"""WebSocket voice session handler — message contract per docs/15-api-websocket-spec.md."""

import asyncio
import base64
import binascii
import contextlib
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app import __version__
from app.common.interfaces import ChatMessage
from app.container import Container
from app.contracts.enforcer import TurnContext
from app.llm.ollama_client import OllamaError
from app.orchestrator import meta_request, pace
from app.orchestrator.review import build_segments
from app.orchestrator.talk import TalkPlan
from app.storage.turns import last_agent_text
from app.voice.interview_flow import InterviewFlow
from app.voice.prosody import lead_in
from app.voice.review_flow import ReviewFlow
from app.voice.session_factory import (
    build_interview_flow,
    build_review_flow,
    build_talk_flow,
    mode_params,
)
from app.voice.talk_flow import TalkFlow
from app.voice.transcribe import SttEmptyError, transcribe_utterance
from app.voice.tts_paced import PacedTts
from app.voice.turn_runner import AgentCompleted, AgentSentence, TurnRunner
from app.voice.warmup import warm_up

logger = logging.getLogger(__name__)

QUESTIONS_PER_SESSION = 6

TERMINAL_STATES = {"DEBRIEF", "END"}

#: Настройка, в которой живёт темп речи между сессиями (doc 15).
PACE_SETTING = "speech_length_scale"

#: Какую реплику подтверждения произнести. Ключ — (просьба, уже на границе):
#: на границе Генри обязан сказать, что дальше некуда, иначе «Sure» прозвучит
#: обещанием изменения, которого не будет.
_PACE_TEMPLATES = {
    (pace.PaceRequest.SLOWER, False): "pace_slower",
    (pace.PaceRequest.SLOWER, True): "pace_slowest",
    (pace.PaceRequest.FASTER, False): "pace_faster",
    (pace.PaceRequest.FASTER, True): "pace_fastest",
}

VoiceFlow = InterviewFlow | ReviewFlow | TalkFlow


#: Сколько ждём уборку сессии, если клиент отвалился. Секунды, не минуты: это
#: один UPDATE по первичному ключу в локальном SQLite. Больше — значит что-то
#: уже сломано, и лучше отпустить цикл, чем держать гашение приложения.
DISCONNECT_CLEANUP_TIMEOUT_S = 5.0


async def ws_session(websocket: WebSocket) -> None:
    await websocket.accept()
    container: Container = websocket.app.state.container
    handler = _SessionHandler(websocket, container)
    live: set[asyncio.Task[None]] | None = getattr(websocket.app.state, "live_ws_cleanups", None)
    try:
        while True:
            message = await websocket.receive_json()
            await handler.dispatch(message)
    except WebSocketDisconnect:
        # ⚠ Уборку НЕЛЬЗЯ делать простым await, и это замер, а не осторожность.
        # Отключение клиента и гашение приложения приходят почти одновременно:
        # портал отменяет задачу обработчика ровно посередине записи статуса.
        # Отмена попадает внутрь `async with db.session()`, выход из контекста
        # (rollback/release) не доводится, и соединение остаётся ВНЕ пула. Дальше
        # его подбирает GC, SQLAlchemy заводит `_terminate_graceful_close`, а
        # `asyncio.runners.close()` ждёт эту задачу вечно — прогон виснет целиком
        # (6 из 10 на linux, 0 из 60 на macOS; разбор — delivery diagnosis.md).
        #
        # `shield` доводит уборку до конца, даже когда снаружи пришла отмена;
        # таймаут не даёт ей же и подвесить гашение. Ссылку на задачу держит
        # `app.state.live_ws_cleanups`, чтобы lifespan дождался её до dispose().
        cleanup = asyncio.ensure_future(handler.aclose())
        if live is not None:
            live.add(cleanup)
            cleanup.add_done_callback(live.discard)
        try:
            await asyncio.wait_for(asyncio.shield(cleanup), DISCONNECT_CLEANUP_TIMEOUT_S)
        except TimeoutError:
            logger.warning("session cleanup did not finish in %ss", DISCONNECT_CLEANUP_TIMEOUT_S)


class _SessionHandler:
    def __init__(self, websocket: WebSocket, container: Container) -> None:
        self._ws = websocket
        self._c = container
        self._flow: VoiceFlow | None = None
        self._kind = "interview"
        self._started_at = 0.0
        self._warmup_task: asyncio.Task[None] | None = None
        # Темп — свойство СЕССИИ, поэтому обёртка своя у каждого обработчика;
        # голосовая модель под ней остаётся общей и грузится один раз.
        self._tts = PacedTts(container.tts, scale=container.settings.piper_length_scale)
        #: Сколько чанков уже прозвучало в текущей реплике: первому дыхание не
        #: нужно, оно нужно ПЕРЕД следующими. Сбрасывается на `final=True`.
        self._spoken_chunks = 0
        self._runner = TurnRunner(container.llm, self._tts)

    # -- dispatch --------------------------------------------------------------

    async def dispatch(self, message: dict[str, Any]) -> None:
        msg_type = message.get("type", "")
        payload = message.get("payload", {}) or {}
        if msg_type == "hello":
            await self._on_hello()
        elif msg_type == "start_interview":
            await self._on_start_interview()
        elif msg_type == "start_review":
            await self._on_start_review(str(payload.get("interview_id", "")))
        elif msg_type == "start_talk":
            await self._on_start_talk()
        elif msg_type == "utterance_end":
            await self._on_utterance_end(payload)
        elif msg_type == "end_session":
            await self._on_end_session(reason=str(payload.get("reason", "user")))
        elif msg_type == "ping":
            await self._send("pong", {})
        else:
            await self._error("INTERNAL", f"unknown message type: {msg_type}", recoverable=True)

    async def aclose(self) -> None:
        """Уборка сессии: сначала снять свои задачи, потом дописать статус.

        Порядок принципиален. `_warmup_task` живёт дольше запроса и в момент
        отключения может держать соединение и файловый дескриптор; если её не
        снять ДО записи, она уйдёт в отменяемый цикл вместе с записью — тот же
        класс, из-за которого висел прогон (diagnosis.md, H1).
        """
        await self._cancel_warmup()
        if self._flow is not None:
            await self._flow.finish(status="in_progress")  # checkpoint already on disk
            self._flow = None

    async def _cancel_warmup(self) -> None:
        """Задача-сирота становится задачей с владельцем.

        `asyncio.create_task` без отмены — ровно то, о чём предупреждает
        документация asyncio: сборщик мусора может уничтожить задачу на середине,
        а закрытие цикла — ждать её. Здесь она отменяется и ДОЖИДАЕТСЯ: без
        await отмена только помечена, но не доведена.
        """
        task, self._warmup_task = self._warmup_task, None
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _on_hello(self) -> None:
        ollama_ok = await self._c.ollama.is_up() if self._c.ollama else True
        await self._send("ready", {"server_version": __version__, "ollama_ok": ollama_ok})

    # -- session starts ----------------------------------------------------------

    def _restore_pace(self, user_settings: dict[str, Any]) -> None:
        """Темп, о котором попросили в прошлый раз, — не значение по умолчанию."""
        stored = user_settings.get(PACE_SETTING)
        if isinstance(stored, int | float) and pace.in_range(float(stored)):
            self._tts.set_scale(float(stored))

    async def _on_start_interview(self) -> None:
        user_settings = await self._c.user_settings.get_all()
        self._restore_pace(user_settings)
        duration = int(user_settings.get("interview_duration_min", 15))
        flow = build_interview_flow(self._c, duration_min=duration)
        intro = self._c.prompts.template("interview_intro")
        await self._open(flow, "interview", intro, lambda: flow.start(intro))

    async def _on_start_talk(self) -> None:
        self._restore_pace(await self._c.user_settings.get_all())
        flow = build_talk_flow(self._c)
        await self._open(flow, "talk", " ".join(flow.current_plan.lines), flow.start)

    async def _open(
        self, flow: VoiceFlow, kind: str, line: str, start: Callable[[], Awaitable[Any]]
    ) -> None:
        """Сессия, которую открывает реплика кода: интервью и разговор."""
        self._flow, self._kind = flow, kind
        self._started_at = time.monotonic()
        await self._send("session_started", {"session_kind": kind, "session_id": flow.session_id})
        await self._state("speaking")
        await self._send_audio(await self._tts.synthesize(line), final=False)
        await start()
        self._start_warmup(flow.messages)  # префикс сессии — в кэш, пока звучит приветствие
        await self._transcript("agent", line)
        await self._send_audio(b"", final=True)
        await self._state("listening")

    async def _on_start_review(self, interview_id: str) -> None:
        self._restore_pace(await self._c.user_settings.get_all())
        row = await self._c.interviews.get(interview_id)
        if row is None:
            await self._error("SESSION_NOT_FOUND", "interview not found", recoverable=True)
            return
        segments = build_segments(json.loads(row.transcript_json))
        if not segments:
            await self._error(
                "SESSION_NOT_FOUND", "interview has no answered questions", recoverable=True
            )
            return
        flow = build_review_flow(self._c, interview_id=interview_id, segments=segments)
        self._flow, self._kind = flow, "review"
        self._started_at = time.monotonic()
        await flow.start()
        await self._c.interviews.link_review(interview_id, flow.session_id)
        await self._send(
            "session_started", {"session_kind": "review", "session_id": flow.session_id}
        )
        self._start_warmup()
        await self._state("processing")
        await self._agent_generation(flow, flow.current_plan)

    # -- turns -------------------------------------------------------------------

    async def _on_utterance_end(self, payload: dict[str, Any]) -> None:
        flow = self._flow
        if flow is None:
            await self._error("SESSION_NOT_FOUND", "no active session", recoverable=True)
            return
        try:
            audio = base64.b64decode(payload.get("audio_base64", ""), validate=True)
        except binascii.Error:
            await self._error("INTERNAL", "invalid base64 audio", recoverable=True)
            return
        await self._state("processing")
        try:
            await self._run_turn(flow, audio)
        except SttEmptyError as exc:
            # Речь человека — ему («heard: …»), в лог только размер (CQG §2.7c).
            logger.info("STT_EMPTY: raw transcript of %d char(s)", len(exc.raw_transcript))
            heard = f" (heard: “{exc.raw_transcript}”)" if exc.raw_transcript.strip() else ""
            await self._error(
                "STT_EMPTY",
                f"no speech detected{heard} — session is English-only",
                recoverable=True,
            )
            await self._state("listening")
        except OllamaError:
            await self._error("PIPELINE_FAILURE", "LLM unavailable", recoverable=False)
            await self._on_end_session(reason="pipeline_failure")
        except WebSocketDisconnect:
            # Разрыв — НЕ отказ хода, а штатный конец сессии, и он обязан дойти
            # до `ws_session`: уборка живёт в его `except`. Без этой ветки
            # `WebSocketDisconnect` (он же `Exception`) попадал ниже, ход
            # объявлялся упавшим, и попытка сказать об этом ушедшему клиенту
            # роняла сессию мимо всякой уборки — `ended_at` оставался пустым
            # навсегда (repro: test_disconnect_during_turn_finishes_session).
            raise
        except Exception:
            logger.exception("voice turn failed")
            await self._error("INTERNAL", "turn failed — please repeat", recoverable=True)
            await self._state("listening")

    async def _run_turn(self, flow: VoiceFlow, audio: bytes) -> None:
        text = await transcribe_utterance(
            self._c.decoder, self._c.stt, audio, min_words=self._c.settings.min_transcript_words
        )
        # Реплика живёт в транскрипте, в логе — только размер: страж судит вызов,
        # а не уровень (CQG §2.7c; tests/test_ws_sentinels.py).
        logger.info("user turn: %d word(s)", len(text.split()))

        # Просьба о темпе перехватывается ДО оркестратора. Иначе она уходит в
        # `on_user_answer` как ответ, тратит follow-up или целый вопрос из шести
        # и оседает в транскрипте против чужого question_id.
        request = pace.detect(text, casual=isinstance(flow, TalkFlow))  # разговор: по форме
        if request is not None:
            await self._handle_pace_request(flow, text, request)
            return

        # Просьба к самому Генри — тот же класс, что темп: не ответ, вопрос не
        # тратится. Только в интервью: в разборе «как бы ты это оценил» — законный
        # вопрос, и оценки там ровно на месте.
        asked = meta_request.detect(text) if isinstance(flow, InterviewFlow) else None
        if asked is not None:
            lines = meta_request.reply(
                asked, self._c.prompts.template, last_agent_text(flow.buffer)
            )
            await self._speak_meta_turn(flow, text, lines)
            return

        plan = await flow.on_user(text)
        await self._transcript("user", text)

        if isinstance(flow, TalkFlow) and isinstance(plan, TalkPlan) and plan.lines:
            await self._speak_plan(flow, plan)
            return

        if plan.state.value in TERMINAL_STATES:
            await self._state("speaking")
            await self._send_audio(await self._tts.synthesize(plan.seed), final=False)
            await flow.on_agent(plan.seed, violations=[], fallback_used=False)
            await self._transcript("agent", plan.seed)
            await self._send_audio(b"", final=True)
            await self._finish_naturally(flow)
            return

        await self._agent_generation(flow, plan)

    async def _handle_pace_request(
        self, flow: VoiceFlow, text: str, request: pace.PaceRequest
    ) -> None:
        """Мета-ход: сменить темп, подтвердить УЖЕ им и повторить сказанное дословно.

        LLM здесь не участвует вовсе — ни вызова, ни истории. Решение о темпе
        структурное, а структурой владеет код (I1-H6); повтор дословный, потому
        что просьба «медленнее» почти всегда означает «я не расслышал».
        """
        new_scale, at_limit = pace.apply(self._tts.scale, request)
        self._tts.set_scale(new_scale)  # ДО синтеза: подтверждение звучит новым темпом
        await self._c.user_settings.update({PACE_SETTING: new_scale})

        ack = self._c.prompts.template(_PACE_TEMPLATES[request, at_limit])
        repeat = last_agent_text(flow.buffer)
        await self._speak_meta_turn(flow, text, [ack, repeat])

    async def _speak_meta_turn(self, flow: VoiceFlow, text: str, lines: list[str]) -> None:
        """Произнести мета-ход и записать его вне вопросов интервью (P9)."""
        await self._transcript("user", text)
        spoken = await self._speak(lines)
        await flow.on_meta(text, spoken)
        await self._transcript("agent", spoken)
        await self._send_audio(b"", final=True)
        await self._state("listening")

    async def _speak_plan(self, flow: TalkFlow, plan: TalkPlan) -> None:
        """Ход разговора, который говорит код: тема, отказ, прощание (D3a)."""
        lines = list(plan.lines)
        if plan.repeat_question:
            lines.append(meta_request.last_question(last_agent_text(flow.buffer)))
        spoken = await self._speak(lines)
        await flow.on_spoken(spoken)
        await self._transcript("agent", spoken)
        await self._send_audio(b"", final=True)
        if plan.finished:
            await self._finish_naturally(flow)
        else:
            await self._state("listening")

    async def _speak(self, lines: list[str]) -> str:
        spoken = [line for line in lines if line]
        await self._state("speaking")
        for line in spoken:
            await self._send_audio(await self._tts.synthesize(line), final=False)
        return " ".join(spoken)

    async def _agent_generation(self, flow: VoiceFlow, plan: Any) -> None:
        params, enforcer = mode_params(self._c, self._kind)
        ctx = TurnContext(state=plan.state.value)
        if isinstance(flow, ReviewFlow):
            ctx = TurnContext(
                state=plan.state.value, question_count=flow.orchestrator.question_count
            )
        speaking = False
        async for event in self._runner.run(
            flow.messages,
            params,
            enforcer=enforcer,
            ctx=ctx,
            seed=plan.seed,
            intent=plan.instruction,
            turn_index=len(flow.buffer.turns),
        ):
            if isinstance(event, AgentSentence):
                if not speaking:
                    await self._state("speaking")
                    speaking = True
                await self._send_audio(event.wav, final=False)
            elif isinstance(event, AgentCompleted):
                await flow.on_agent(
                    event.text, violations=event.violations, fallback_used=event.fallback_used
                )
                await self._transcript("agent", event.text)
                await self._send_audio(b"", final=True)
                await self._state("listening")

    # -- session end ---------------------------------------------------------------

    async def _finish_naturally(self, flow: VoiceFlow) -> None:
        await self._cancel_warmup()
        await flow.finish(status="completed")
        next_action = {"interview": "offer_review", "review": "generate_summary"}.get(
            self._kind, "none"
        )
        await self._session_ended(flow, reason="finished", next_action=next_action)
        if isinstance(flow, ReviewFlow):
            self._c.summaries.schedule_full(flow.source_interview_id, flow.session_id)
        self._flow = None

    async def _on_end_session(self, *, reason: str) -> None:
        flow = self._flow
        if flow is None:
            return
        self._flow = None
        await self._cancel_warmup()
        status = "completed" if reason == "user" else "failed"
        await flow.finish(status=status)
        await self._session_ended(flow, reason=reason, next_action="none")
        await self._state("idle")

    async def _session_ended(self, flow: VoiceFlow, *, reason: str, next_action: str) -> None:
        await self._send(
            "session_ended",
            {
                "session_kind": self._kind,
                "session_id": flow.session_id,
                "duration_sec": int(time.monotonic() - self._started_at),
                "reason": reason,
                "next_action": next_action,
            },
        )

    # -- plumbing --------------------------------------------------------------------

    def _start_warmup(self, messages: list[ChatMessage] | None = None) -> None:
        model = self._c.settings.ollama_model_interview
        self._warmup_task = asyncio.create_task(
            warm_up(self._c.stt, self._c.llm, model=model, messages=messages)
        )

    async def _send(self, msg_type: str, payload: dict[str, Any]) -> None:
        # Проверки «а жив ли клиент» здесь СОЗНАТЕЛЬНО нет, и это замер, а не
        # упущение: с ней сьют такой же зелёный, но сервер доигрывает весь ход
        # (LLM + TTS) в пустоту, а без неё первая же отправка роняет
        # `WebSocketDisconnect`, ход обрывается и сессия закрывается. Реплика
        # пользователя сохраняется в обоих случаях — она пишется до отправки.
        await self._ws.send_json({"type": msg_type, "payload": payload})

    async def _state(self, value: str) -> None:
        flow = self._flow
        await self._send(
            "state",
            {
                "value": value,
                "session_kind": self._kind if flow else None,
                "session_id": flow.session_id if flow else None,
                **self._question_progress(flow),
            },
        )

    @staticmethod
    def _question_progress(flow: VoiceFlow | None) -> dict[str, Any]:
        """Где мы в интервью — клиенту, чтобы показать «вопрос N из M».

        Знать, сколько осталось, снимает тревогу, а это и есть задача тренажёра.
        У Mode 2 своего счётчика вопросов нет, поэтому там поля пустые.
        """
        if not isinstance(flow, InterviewFlow):
            return {"question_index": None, "question_total": None, "question_kind": None}
        return {
            "question_index": flow.orchestrator.question_number,
            "question_total": flow.orchestrator.question_count,
            "question_kind": flow.current_plan.question_kind,
        }

    async def _transcript(self, role: str, text: str) -> None:
        await self._send("transcript", {"role": role, "text": text, "final": True})

    async def _send_audio(self, wav: bytes, *, final: bool) -> None:
        """Второму и последующим чанкам реплики предпосылается дыхание.

        Счётчик живёт здесь, а не в `TurnRunner`, потому что одним местом
        закрываются ВСЕ пути, где подряд идут несколько чанков: ход интервью,
        подтверждение темпа с повтором, разбор в Mode 2. Два места вставки
        неизбежно разъехались бы (L11).

        ⚠ Корректность держится на сбросе: `final=True` заканчивает реплику, и
        без сброса пауза уехала бы в НАЧАЛО следующей — то есть в задержку
        перед первым словом Генри.
        """
        if wav and self._spoken_chunks:
            wav = lead_in(wav, self._c.settings.sentence_pause_ms / 1000)
        self._spoken_chunks = 0 if final else self._spoken_chunks + 1
        await self._send(
            "audio",
            {
                "chunk_base64": base64.b64encode(wav).decode("ascii"),
                "mime": "audio/wav",
                "final": final,
            },
        )

    async def _error(self, code: str, message: str, *, recoverable: bool) -> None:
        await self._send("error", {"code": code, "message": message, "recoverable": recoverable})
