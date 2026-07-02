"""Piper TTS via the piper-tts package; voice loaded once (doc 19 note 4)."""

import asyncio
import io
import wave
from pathlib import Path
from typing import Any


class PiperTts:
    """Implements TextToSpeech; ONNX inference runs in a worker thread."""

    def __init__(self, voice_path: Path) -> None:
        self._voice_path = voice_path
        self._voice: Any = None
        self._lock = asyncio.Lock()

    async def _ensure_loaded(self) -> Any:
        async with self._lock:
            if self._voice is None:
                self._voice = await asyncio.to_thread(self._load_voice)
        return self._voice

    def _load_voice(self) -> Any:
        from piper import PiperVoice

        return PiperVoice.load(
            str(self._voice_path),
            config_path=str(self._voice_path.with_suffix(".onnx.json")),
        )

    async def synthesize(self, text: str) -> bytes:
        voice = await self._ensure_loaded()
        return await asyncio.to_thread(self._synthesize_blocking, voice, text)

    @staticmethod
    def _synthesize_blocking(voice: Any, text: str) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        return buffer.getvalue()
