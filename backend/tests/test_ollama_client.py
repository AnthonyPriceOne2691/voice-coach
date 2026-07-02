import json

import httpx
import pytest

from app.llm.ollama_client import OllamaClient, OllamaError


def _stream_response(tokens: list[str]) -> httpx.Response:
    lines = [
        json.dumps({"message": {"role": "assistant", "content": t}, "done": False}) for t in tokens
    ]
    lines.append(json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}))
    return httpx.Response(200, content=("\n".join(lines)).encode())


def _client_with(handler: httpx.MockTransport) -> OllamaClient:
    return OllamaClient("http://ollama.test", client=httpx.AsyncClient(transport=handler))


async def test_stream_chat_yields_tokens() -> None:
    transport = httpx.MockTransport(lambda request: _stream_response(["Hel", "lo", "."]))
    client = _client_with(transport)
    tokens = [
        t
        async for t in client.stream_chat(
            [{"role": "user", "content": "hi"}],
            model="test-model",
            temperature=0.5,
            max_tokens=50,
        )
    ]
    assert tokens == ["Hel", "lo", "."]


async def test_stream_chat_sends_options() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return _stream_response(["ok."])

    client = _client_with(httpx.MockTransport(handler))
    async for _ in client.stream_chat(
        [{"role": "user", "content": "hi"}], model="m", temperature=0.7, max_tokens=99
    ):
        pass
    options = seen["options"]
    assert isinstance(options, dict)
    assert options["num_predict"] == 99
    assert options["temperature"] == 0.7
    assert seen["model"] == "m"


async def test_http_error_raises_ollama_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500, content=b"boom"))
    client = _client_with(transport)
    with pytest.raises(OllamaError):
        async for _ in client.stream_chat(
            [{"role": "user", "content": "hi"}], model="m", temperature=0.5, max_tokens=10
        ):
            pass


async def test_is_up_true_and_false() -> None:
    up = _client_with(httpx.MockTransport(lambda r: httpx.Response(200, json={"models": []})))
    assert await up.is_up() is True

    def raise_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    down = _client_with(httpx.MockTransport(raise_error))
    assert await down.is_up() is False
