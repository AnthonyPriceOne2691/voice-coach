"""WebSocket voice session handler — message contract per docs/15-api-websocket-spec.md."""

import asyncio
import base64
import binascii
import io
import logging
import tempfile
import time
import uuid
import wave
from pathlib import Path
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app import __version__
from app.container import Container
from app.llm.ollama_client import OllamaError
from app.storage.transcript_log import TranscriptLog
from app.voice.pipeline import (
    AgentCompleted,
    AgentSentence,
    LlmParams,
    SttEmptyError,
    UserTranscribed,
    VoiceTurnPipeline,
)
from app.voice.session import VoiceSession

logger = logging.getLogger(__name__)


def _silent_wav(duration_s: float = 1.0, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * int(duration_s * rate))
    return buffer.getvalue()


async def ws_session(websocket: WebSocket) -> None:
    await websocket.accept()
    container: Container = websocket.app.state.container
    handler = _SessionHandler(websocket, container)
    try:
        while True:
            message = await websocket.receive_json()
            await handler.dispatch(message)
    except WebSocketDisconnect:
        return


class _SessionHandler:
    def __init__(self, websocket: WebSocket, container: Container) -> None:
        self._ws = websocket
        self._c = container
        self._session: VoiceSession | None = None
        self._started_at = 0.0
        self._warmup_task: asyncio.Task[None] | None = None
        self._pipeline = VoiceTurnPipeline(
            container.stt,
            container.llm,
            container.tts,
            min_transcript_words=container.settings.min_transcript_words,
        )

    async def dispatch(self, message: dict[str, Any]) -> None:
        msg_type = message.get("type", "")
        payload = message.get("payload", {}) or {}
        if msg_type == "hello":
            await self._on_hello()
        elif msg_type == "start_interview":
            await self._on_start_interview()
        elif msg_type == "utterance_end":
            await self._on_utterance_end(payload)
        elif msg_type == "end_session":
            await self._on_end_session(reason=str(payload.get("reason", "user")))
        elif msg_type == "ping":
            await self._send("pong", {})
        else:
            await self._error("INTERNAL", f"unknown message type: {msg_type}", recoverable=True)

    async def _on_hello(self) -> None:
        ollama_ok = await self._c.ollama.is_up() if self._c.ollama else True
        await self._send("ready", {"server_version": __version__, "ollama_ok": ollama_ok})

    async def _on_start_interview(self) -> None:
        session_id = str(uuid.uuid4())
        log = TranscriptLog(self._c.settings.sessions_dir, session_id)
        self._session = VoiceSession(session_id, self._c.prompts.interviewer_system(), log)
        self._started_at = time.monotonic()
        await self._send("session_started", {"session_kind": "interview", "session_id": session_id})
        intro = self._c.prompts.template("interview_intro")
        await self._state("speaking")
        await self._send_audio(await self._c.tts.synthesize(intro), final=False)
        # Pre-warm STT + LLM in the background (doc 19 note 1: cold whisper load must
        # not land on the first real turn) while the intro is playing on the client.
        self._warmup_task = asyncio.create_task(self._warmup())
        await self._finish_agent_turn(intro)

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

    async def _on_utterance_end(self, payload: dict[str, Any]) -> None:
        session = self._session
        if session is None:
            await self._error("SESSION_NOT_FOUND", "no active session", recoverable=True)
            return
        try:
            audio = base64.b64decode(payload.get("audio_base64", ""), validate=True)
        except binascii.Error:
            await self._error("INTERNAL", "invalid base64 audio", recoverable=True)
            return
        await self._state("processing")
        try:
            await self._run_turn(session, audio)
        except SttEmptyError:
            await self._error("STT_EMPTY", "no speech detected", recoverable=True)
            await self._state("listening")
        except OllamaError:
            await self._error("PIPELINE_FAILURE", "LLM unavailable", recoverable=False)
            await self._on_end_session(reason="pipeline_failure")
        except Exception:
            logger.exception("voice turn failed")
            await self._error("INTERNAL", "turn failed — please repeat", recoverable=True)
            await self._state("listening")

    async def _run_turn(self, session: VoiceSession, audio: bytes) -> None:
        settings = self._c.settings
        params = LlmParams(
            model=settings.ollama_model_interview,
            temperature=settings.interview_temperature,
            max_tokens=settings.interview_max_tokens,
        )
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "utterance.wav"
            await self._c.decoder.to_wav(audio, wav_path)
            speaking = False
            async for event in self._pipeline.run_turn(wav_path, session.messages, params):
                if isinstance(event, UserTranscribed):
                    session.add_user(event.text)
                    await self._transcript("user", event.text)
                elif isinstance(event, AgentSentence):
                    if not speaking:
                        await self._state("speaking")
                        speaking = True
                    await self._send_audio(event.wav, final=False)
                elif isinstance(event, AgentCompleted):
                    await self._finish_agent_turn(event.text)

    async def _finish_agent_turn(self, text: str) -> None:
        if self._session is not None:
            self._session.add_agent(text)
        await self._transcript("agent", text)
        await self._send_audio(b"", final=True)  # empty sentinel = end of agent audio
        await self._state("listening")

    async def _on_end_session(self, *, reason: str) -> None:
        session = self._session
        if session is None:
            return
        self._session = None
        await self._send(
            "session_ended",
            {
                "session_kind": "interview",
                "session_id": session.session_id,
                "duration_sec": int(time.monotonic() - self._started_at),
                "reason": reason,
                "next_action": "none",  # Phase 2: offer_review
            },
        )
        await self._state("idle")

    async def _send(self, msg_type: str, payload: dict[str, Any]) -> None:
        await self._ws.send_json({"type": msg_type, "payload": payload})

    async def _state(self, value: str) -> None:
        session = self._session
        await self._send(
            "state",
            {
                "value": value,
                "session_kind": "interview" if session else None,
                "session_id": session.session_id if session else None,
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
