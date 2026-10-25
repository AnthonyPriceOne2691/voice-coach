"""Общее для сьюта: сторож утечек соединений и база в памяти с владельцем.

Сторож заменяет канал `filterwarnings = ["error"]` для этого класса дефекта, а не
дополняет его: тот сообщает об утечке, когда соединение найдёт сборщик мусора, то
есть в случайном чужом тесте, а сторож — в конце того теста, который её сделал.
Почему так и чем это шире канонной фикстуры `checkedout() == 0` — в
`tests/db_lifecycle.py`.
"""

from collections.abc import AsyncIterator, Iterator

import pytest

from app.storage.db import Database
from tests.db_lifecycle import ConnectionLedger, owned_database


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
