"""STT/TTS/LLM behind Protocols — any impl (Whisper/Piper/Ollama or mocks) is substitutable."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

ChatMessage = dict[str, str]  # {"role": "system|user|assistant", "content": "..."}


class SpeechToText(Protocol):
    async def transcribe(self, wav_path: Path) -> str: ...


class TextToSpeech(Protocol):
    async def synthesize(self, text: str, *, length_scale: float | None = None) -> bytes:
        """Return WAV bytes for the given sentence.

        `length_scale` is the speaking tempo (1.0 = the voice's native rate,
        larger = slower); None means "use whatever this implementation was
        configured with". It lives on the seam because tempo is decided per
        utterance — the user can ask for it mid-session (docs 15/17).
        """
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
