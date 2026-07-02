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

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        self.last_messages = messages
        for token in self.tokens:
            yield token


class FakeDecoder:
    async def to_wav(self, data: bytes, out_path: Path) -> None:
        out_path.write_bytes(b"RIFF-fake-wav")
