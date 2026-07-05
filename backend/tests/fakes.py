"""Shared fakes for STT/TTS/LLM/decoder — real AI is always mocked (doc 18)."""

from collections.abc import AsyncIterator
from pathlib import Path

from app.common.interfaces import ChatMessage


class FakeStt:
    def __init__(self, text: str = "I built an inbound pipeline for our team") -> None:
        self.text = text
        self.calls: list[Path] = []

    async def transcribe(self, wav_path: Path) -> str:
        self.calls.append(wav_path)
        return self.text


class FakeTts:
    def __init__(self) -> None:
        self.synthesized: list[str] = []

    async def synthesize(self, text: str) -> bytes:
        self.synthesized.append(text)
        return b"WAV:" + text.encode()


class FakeLlm:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.last_messages: list[ChatMessage] | None = None
        self.last_model: str | None = None
        self.last_num_ctx: int | None = None

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        self.last_messages = messages
        self.last_model = model
        self.last_num_ctx = num_ctx
        for token in self.tokens:
            yield token


class ScriptedLlm:
    """Returns a different token script per call (attempt 1, attempt 2, ...)."""

    def __init__(self, scripts: list[list[str]]) -> None:
        self._scripts = scripts
        self.calls: list[list[ChatMessage]] = []

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        script = self._scripts[min(len(self.calls) - 1, len(self._scripts) - 1)]
        for token in script:
            yield token


class FakeDecoder:
    async def to_wav(self, data: bytes, out_path: Path) -> None:
        out_path.write_bytes(b"RIFF-fake-wav")
