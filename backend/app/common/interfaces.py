"""STT/TTS/LLM behind Protocols — any impl (Whisper/Piper/Ollama or mocks) is substitutable."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

ChatMessage = dict[str, str]  # {"role": "system|user|assistant", "content": "..."}


class SpeechToText(Protocol):
    async def transcribe(self, wav_path: Path) -> str: ...


class TextToSpeech(Protocol):
    async def synthesize(self, text: str) -> bytes:
        """Return WAV bytes for the given sentence."""
        ...


class LlmClient(Protocol):
    def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield response tokens as they arrive."""
        ...


class AudioDecoder(Protocol):
    async def to_wav(self, data: bytes, out_path: Path) -> None:
        """Decode client audio (webm/opus) to 16 kHz mono WAV."""
        ...
