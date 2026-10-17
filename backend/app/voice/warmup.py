"""Прогрев голосового цикла на старте сессии: STT и модель грузятся до первой реплики.

Вынесено из `ws_voice` (2026-10-17), когда тот упёрся в потолок 500 строк, а
третьему режиму понадобилось место. Оба прогрева — best-effort: отказ пишется в
лог и сессию не роняет.

⚠ Прогреть модель — мало: нужно прогреть ПРЕФИКС. Ollama переиспользует KV-кэш
по неизменному началу промпта (doc 20), а системный промпт с профилем — ~1,700
токенов. Прогрев «hi» грузил веса и не кэшировал ничего, и первый ход сессии
платил полный prefill после реплики человека: замер 2026-10-17 — 8,763 ms до
первого звука при гейте 3,000 (тёплые ходы — 1,621–1,778 ms). Поэтому сессия,
открытая репликой кода, прогревает СВОИ сообщения, пока звучит приветствие.
"""

import io
import logging
import tempfile
import wave
from pathlib import Path

from app.common.interfaces import ChatMessage, LlmClient, SpeechToText

logger = logging.getLogger(__name__)


def _silent_wav(duration_s: float = 1.0, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * int(duration_s * rate))
    return buffer.getvalue()


async def warm_up(
    stt: SpeechToText,
    llm: LlmClient,
    *,
    model: str,
    messages: list[ChatMessage] | None = None,
) -> None:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "warmup.wav"
            wav_path.write_bytes(_silent_wav())
            await stt.transcribe(wav_path)
    except Exception:
        logger.warning("STT warmup failed", exc_info=True)
    try:
        prefix = messages or [{"role": "user", "content": "hi"}]
        async for _ in llm.stream_chat(prefix, model=model, temperature=0.0, max_tokens=1):
            break
    except Exception:
        logger.warning("LLM warmup failed", exc_info=True)
