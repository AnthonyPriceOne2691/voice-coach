"""Piper TTS via the piper-tts package; voice loaded once (doc 19 note 4)."""

import asyncio
import io
import wave
from pathlib import Path
from typing import Any


class PiperTts:
    """Implements TextToSpeech; ONNX inference runs in a worker thread."""

    def __init__(
        self,
        voice_path: Path,
        *,
        length_scale: float = 1.0,
        noise_scale: float | None = None,
        noise_w: float | None = None,
    ) -> None:
        self._voice_path = voice_path
        self._length_scale = length_scale  # > 1.0 = slower speech
        # Просодия — характер голоса, один на процесс: в отличие от темпа её
        # никто не меняет на лету, поэтому она живёт в конструкторе, а не на шве.
        # None означало бы «взять паспорт голоса», а паспорт hfc_male ровный.
        self._noise_scale = noise_scale
        self._noise_w = noise_w
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

    async def synthesize(self, text: str, *, length_scale: float | None = None) -> bytes:
        voice = await self._ensure_loaded()
        scale = self._length_scale if length_scale is None else length_scale
        return await asyncio.to_thread(self._synthesize_blocking, voice, text, scale)

    def _synthesize_blocking(self, voice: Any, text: str, length_scale: float) -> bytes:
        from piper import SynthesisConfig

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            voice.synthesize_wav(
                text,
                wav_file,
                syn_config=SynthesisConfig(
                    length_scale=length_scale,
                    noise_scale=self._noise_scale,
                    noise_w_scale=self._noise_w,
                ),
            )
        return buffer.getvalue()
