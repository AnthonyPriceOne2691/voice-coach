"""Async streaming client for the Ollama /api/chat endpoint."""

import json
from collections.abc import AsyncIterator

import httpx

from app.common.interfaces import ChatMessage


class OllamaError(RuntimeError):
    """Ollama is unreachable or returned an error."""


class OllamaClient:
    """Implements LlmClient over a local Ollama daemon."""

    def __init__(
        self,
        base_url: str,
        *,
        num_ctx: int = 8192,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._num_ctx = num_ctx
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0))

    async def is_up(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": num_ctx or self._num_ctx,
            },
        }
        try:
            async with self._client.stream(
                "POST", f"{self._base_url}/api/chat", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    # NDJSON-стрим Ollama: один крошечный объект на ТОКЕН.
                    # Унести в поток нельзя — это и есть sentence-streaming, ради
                    # которого стоит latency-инвариант ~3.0 s на ход.
                    data = json.loads(line)  # cpu-ok: один токен NDJSON
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        return
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

    async def aclose(self) -> None:
        await self._client.aclose()
