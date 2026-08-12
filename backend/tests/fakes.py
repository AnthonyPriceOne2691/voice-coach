"""Shared fakes for STT/TTS/LLM/decoder — real AI is always mocked (doc 18)."""

from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocketState

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


class GoneClientWebSocket:
    """Транспорт, повторяющий starlette ПОСЛЕ ухода клиента посреди хода.

    Почему поддельный, а не `TestClient`: тест-клиент на закрытии **отменяет**
    задачу приложения (замер: внутрь STT прилетает `CancelledError`), а uvicorn
    задачу не трогает и сообщает об уходе только на отправке. Тест на
    `TestClient` проверял бы поведение тест-клиента, а не сервера.

    Воспроизводятся ОБЕ ступени `starlette/websockets.py::send`, снятые с
    настоящего прогона: первая отправка после ухода даёт
    `WebSocketDisconnect(1006)` и переводит `application_state` в DISCONNECTED,
    каждая следующая — `RuntimeError('Cannot call "send" once a close message
    has been sent.')`. Вторая ступень и уносила уборку мимо
    `except WebSocketDisconnect`.

    `client_state` остаётся CONNECTED: он переключается только на приёме
    `websocket.disconnect`, которого посреди хода никто не читает.
    """

    def __init__(self, app: object, script: list[dict[str, object]]) -> None:
        self.app = app
        self.client_state = WebSocketState.CONNECTED
        self.application_state = WebSocketState.CONNECTED
        self.sent: list[dict[str, object]] = []
        self.client_gone = False
        self._script = list(script)

    async def accept(self) -> None:
        return None

    async def receive_json(self) -> dict[str, object]:
        if self.client_gone or not self._script:
            self.client_state = WebSocketState.DISCONNECTED
            raise WebSocketDisconnect(code=1006)
        return self._script.pop(0)

    async def send_json(self, message: dict[str, object]) -> None:
        if not self.client_gone:
            self.sent.append(message)
            return
        if self.application_state is WebSocketState.CONNECTED:
            self.application_state = WebSocketState.DISCONNECTED
            raise WebSocketDisconnect(code=1006)
        raise RuntimeError('Cannot call "send" once a close message has been sent.')


class TabClosingStt:
    """STT, во время которого пользователь закрывает вкладку.

    Момент выбран не случайно: следующая за STT операция — отправка распознанной
    реплики, то есть первый контакт с уже мёртвым сокетом. Ровно там дефект и
    жил в браузере.
    """

    def __init__(
        self, ws: GoneClientWebSocket, text: str = "I built an inbound pipeline for our team"
    ) -> None:
        self.ws = ws
        self.text = text

    async def transcribe(self, wav_path: Path) -> str:
        self.ws.client_gone = True
        return self.text


class FakeDecoder:
    async def to_wav(self, data: bytes, out_path: Path) -> None:
        out_path.write_bytes(b"RIFF-fake-wav")
