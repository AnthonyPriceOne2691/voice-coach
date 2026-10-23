"""STT/TTS/LLM behind Protocols — any impl (Whisper/Piper/Ollama or mocks) is substitutable."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, NotRequired, Protocol, TypedDict, Unpack

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


class ChatOptions(TypedDict):
    """Параметры одного вызова модели — объявлены ОДИН раз для шва и реализации.

    `json_schema` ограничивает ответ этой JSON-формой (Ollama `format`): побочный
    структурный запрос вроде проверки речи (D3a.2), а не произносимая реплика.
    """

    model: str
    temperature: float
    max_tokens: int
    num_ctx: NotRequired[int | None]
    json_schema: NotRequired[dict[str, Any] | None]


class LlmClient(Protocol):
    def stream_chat(
        self, messages: list[ChatMessage], **options: Unpack[ChatOptions]
    ) -> AsyncIterator[str]:
        """Yield response tokens as they arrive."""
        ...


class AudioDecoder(Protocol):
    async def to_wav(self, data: bytes, out_path: Path) -> None:
        """Decode client audio (webm/opus) to 16 kHz mono WAV."""
        ...
