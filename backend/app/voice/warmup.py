"""Прогрев голосового цикла на старте сессии: STT и модель грузятся до первой реплики.

Вынесено из `ws_voice` (2026-10-17), когда тот упёрся в потолок 500 строк, а
третьему режиму понадобилось место. Поведение то же: оба прогрева — best-effort,
отказ пишется в лог и сессию не роняет.
"""

import io
import logging
import tempfile
import wave
from pathlib import Path

from app.common.interfaces import LlmClient, SpeechToText

logger = logging.getLogger(__name__)


def _silent_wav(duration_s: float = 1.0, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * int(duration_s * rate))
    return buffer.getvalue()


async def warm_up(stt: SpeechToText, llm: LlmClient, *, model: str) -> None:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "warmup.wav"
            wav_path.write_bytes(_silent_wav())
            await stt.transcribe(wav_path)
    except Exception:
        logger.warning("STT warmup failed", exc_info=True)
    try:
        async for _ in llm.stream_chat(
            [{"role": "user", "content": "hi"}], model=model, temperature=0.0, max_tokens=1
        ):
            break
    except Exception:
        logger.warning("LLM warmup failed", exc_info=True)
