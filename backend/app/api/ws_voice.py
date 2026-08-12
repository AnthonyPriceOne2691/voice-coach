"""WebSocket voice session handler — message contract per docs/15-api-websocket-spec.md."""

import asyncio
import base64
import binascii
import contextlib
import io
import json
import logging
import random
import tempfile
import time
import uuid
import wave
from pathlib import Path
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app import __version__
from app.container import Container
from app.contracts.enforcer import ContractEnforcer, TurnContext
from app.llm.ollama_client import OllamaError
from app.orchestrator.interview import InterviewOrchestrator
from app.orchestrator.question_bank import pick_session_pool
from app.orchestrator.review import ReviewOrchestrator, build_segments, render_segments
from app.voice.interview_flow import InterviewFlow
from app.voice.review_flow import ReviewFlow
from app.voice.transcribe import SttEmptyError, transcribe_utterance
from app.voice.turn_runner import AgentCompleted, AgentSentence, LlmParams, TurnRunner

logger = logging.getLogger(__name__)

QUESTIONS_PER_SESSION = 6
TERMINAL_STATES = {"DEBRIEF", "END"}

VoiceFlow = InterviewFlow | ReviewFlow


def _silent_wav(duration_s: float = 1.0, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * int(duration_s * rate))
    return buffer.getvalue()


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
        self._runner = TurnRunner(container.llm, container.tts)

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

    async def _on_start_interview(self) -> None:
        user_settings = await self._c.user_settings.get_all()
        duration = int(user_settings.get("interview_duration_min", 15))
        pool = pick_session_pool(
            self._c.question_bank,
            count=QUESTIONS_PER_SESSION,
            # Подавление стоит на строке, а не в ignore конфига: выбор вопросов
            # интервью — не крипто, и это видно на месте. Токены/соли брать
            # `secrets`, и тогда правило обязано краснеть.
            rng=random.Random(),  # noqa: S311 -- выбор вопросов, не крипто
        )
        wrap_seed = self._c.prompts.template("interview_wrap_up")
        orchestrator = InterviewOrchestrator(pool, duration_min=duration, wrap_up_seed=wrap_seed)
        flow = InterviewFlow(
            str(uuid.uuid4()),
            orchestrator,
            self._c.prompts.interviewer_system(),
            self._c.interviews,
            interview_mode="technical_project_walkthrough",
        )
        self._flow, self._kind = flow, "interview"
        self._started_at = time.monotonic()
        await self._send(
            "session_started", {"session_kind": "interview", "session_id": flow.session_id}
        )
        intro = self._c.prompts.template("interview_intro")
        await self._state("speaking")
        await self._send_audio(await self._c.tts.synthesize(intro), final=False)
        await flow.start(intro)
        self._warmup_task = asyncio.create_task(self._warmup())
        await self._transcript("agent", intro)
        await self._send_audio(b"", final=True)
        await self._state("listening")

    async def _on_start_review(self, interview_id: str) -> None:
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
        orchestrator = ReviewOrchestrator(segments)
        flow = ReviewFlow(
            str(uuid.uuid4()),
            interview_id,
            orchestrator,
            self._c.prompts.review_system(render_segments(segments)),
            self._c.reviews,
        )
        self._flow, self._kind = flow, "review"
        self._started_at = time.monotonic()
        await flow.start()
        await self._c.interviews.link_review(interview_id, flow.session_id)
        await self._send(
            "session_started", {"session_kind": "review", "session_id": flow.session_id}
        )
        self._warmup_task = asyncio.create_task(self._warmup())
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
            logger.info("STT_EMPTY, raw transcript: %r", exc.raw_transcript)
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
        logger.info("user said: %r", text)
        plan = await flow.on_user(text)
        await self._transcript("user", text)

        if plan.state.value in TERMINAL_STATES:
            await self._state("speaking")
            await self._send_audio(await self._c.tts.synthesize(plan.seed), final=False)
            await flow.on_agent(plan.seed, violations=[], fallback_used=False)
            await self._transcript("agent", plan.seed)
            await self._send_audio(b"", final=True)
            await self._finish_naturally(flow)
            return

        await self._agent_generation(flow, plan)

    async def _agent_generation(self, flow: VoiceFlow, plan: Any) -> None:
        params, enforcer = self._mode_params()
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

    def _mode_params(self) -> tuple[LlmParams, ContractEnforcer]:
        settings = self._c.settings
        if self._kind == "review":
            return (
                LlmParams(
                    model=settings.ollama_model_interview,  # D-8: Qwen for all voice
                    temperature=settings.review_temperature,
                    max_tokens=settings.review_max_tokens,
                ),
                self._c.review_enforcer,
            )
        return (
            LlmParams(
                model=settings.ollama_model_interview,
                temperature=settings.interview_temperature,
                max_tokens=settings.interview_max_tokens,
            ),
            self._c.interview_enforcer,
        )

    # -- session end ---------------------------------------------------------------

    async def _finish_naturally(self, flow: VoiceFlow) -> None:
        await self._cancel_warmup()
        await flow.finish(status="completed")
        next_action = "offer_review" if self._kind == "interview" else "generate_summary"
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

    async def _warmup(self) -> None:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                wav_path = Path(tmp) / "warmup.wav"
                wav_path.write_bytes(_silent_wav())
                await self._c.stt.transcribe(wav_path)
        except Exception:
            logger.warning("STT warmup failed", exc_info=True)
        try:
            settings = self._c.settings
            async for _ in self._c.llm.stream_chat(
                [{"role": "user", "content": "hi"}],
                model=settings.ollama_model_interview,
                temperature=0.0,
                max_tokens=1,
            ):
                break
        except Exception:
            logger.warning("LLM warmup failed", exc_info=True)

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
            },
        )

    async def _transcript(self, role: str, text: str) -> None:
        await self._send("transcript", {"role": role, "text": text, "final": True})

    async def _send_audio(self, wav: bytes, *, final: bool) -> None:
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
