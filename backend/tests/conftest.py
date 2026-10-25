"""Общее для сьюта: сторож утечек соединений, срок на кадр WebSocket, база в памяти.

Сторож заменяет канал `filterwarnings = ["error"]` для этого класса дефекта, а не
дополняет его: тот сообщает об утечке, когда соединение найдёт сборщик мусора, то
есть в случайном чужом тесте, а сторож — в конце того теста, который её сделал.
Почему так и чем это шире канонной фикстуры `checkedout() == 0` — в
`tests/db_lifecycle.py`.
"""

import sys
from collections.abc import AsyncIterator, Iterator
from typing import Any

import anyio
import pytest

from app.storage.db import Database
from tests.db_lifecycle import ConnectionLedger, owned_database

#: Кадр WebSocket, которого сервер не прислал за столько секунд, — красный тест.
WS_FRAME_DEADLINE_S = 3.0


def _receive_or_fail(session: Any) -> Any:
    """`WebSocketTestSession.receive` со сроком: тест-клиент ждёт кадр вечно."""

    async def next_frame() -> Any:
        with anyio.fail_after(WS_FRAME_DEADLINE_S):
            return await session._send_rx.receive()

    try:
        return session.portal.call(next_frame)
    except TimeoutError:
        raise AssertionError(f"сервер не прислал кадр за {WS_FRAME_DEADLINE_S} s") from None


@pytest.fixture(autouse=True)
def _ws_frames_arrive_or_the_test_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Тест, не дождавшийся кадра, падает за секунды, а не висит.

    Без срока он висел до pytest-timeout (60 s), а под мутационным гейтом — до потолка
    mutmut, (оценка тестов + 1) × 3: замер 2026-10-25 — 51 такой мутант в
    `ws_voice.py` и `talk_checks.py`, по этой формуле около трети цены прогона. Модуль
    тест-клиента здесь не импортируется (предупреждение на его импорте роняло бы
    загрузку conftest): подменяется то, что загрузили сами тесты.
    """
    testclient = sys.modules.get("starlette.testclient")
    if testclient is not None:
        monkeypatch.setattr(testclient.WebSocketTestSession, "receive", _receive_or_fail)


@pytest.fixture(autouse=True)
def _no_leaked_connections() -> Iterator[None]:
    """W3, W4, W5, W7: каждый тест возвращает в пул и закрывает всё, что открыл.

    Фикстура autouse поднимается раньше остальных фикстур теста и потому
    сворачивается последней: к проверке уже отработали teardown'ы `db`, TestClient
    и lifespan приложения, то есть всё, что обязано погасить движок.
    """
    with ConnectionLedger() as ledger:
        yield
    problems = ledger.leaks()
    assert not problems, "; ".join(problems)  # W3, W4, W5, W7


@pytest.fixture
async def db() -> AsyncIterator[Database]:
    """База в памяти со схемой — и с владельцем: `dispose()` в teardown."""
    async with owned_database("sqlite+aiosqlite:///:memory:") as database:
        await database.create_all()
        yield database
