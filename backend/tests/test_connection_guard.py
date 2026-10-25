"""Сторожа сьюта сами под проверкой (`db_lifecycle.py`, `conftest.py`).

Сторож, который не может покраснеть, неотличим от отсутствующего, а краснеющий
всегда будет снят через неделю. Поэтому здесь обе стороны: каждая форма утечки
называется, чистая работа — тишина. Каждый тест убирает свою утечку сам, ДО конца:
autouse-сторож из `conftest.py` смотрит и на этот файл. Срок на кадр WebSocket — так же.
"""

import asyncio
import contextlib
import threading
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocket, WebSocketDisconnect

from tests import conftest
from tests.db_lifecycle import ConnectionLedger, owned_database

NOT_DISPOSED = "движок без `dispose()`"
NOT_RETURNED = "выдано пулом и не возвращено"


async def _touch(engine: AsyncEngine) -> None:
    """Взять соединение и ВЕРНУТЬ его в пул: пул остаётся открытым."""
    async with engine.connect() as conn:
        await conn.execute(text("select 1"))


async def test_engine_without_dispose_is_named(tmp_path: Path) -> None:
    """W3: соединение возвращено в пул, а пул не закрыт — так текли все 18 тестов.

    Канонная фикстура `checkedout() == 0` этот случай пропускает: выданных нет.
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'leak.db'}")
    with ConnectionLedger() as ledger:
        await _touch(engine)
        found = ledger.leaks()
        lent_by_pool = engine.pool.checkedout()  # type: ignore[attr-defined]
        await engine.dispose()  # своя уборка: autouse-сторож смотрит и сюда
        after = ledger.leaks()

    assert lent_by_pool == 0  # W3: канонной фикстуре здесь нечего увидеть
    assert len(found) == 1  # W3
    assert found[0].startswith("1 соединени(й) открыто и не закрыто")  # W3
    assert NOT_DISPOSED in found[0]  # W3: причина названа, а не только число
    assert after == []  # W3: dispose() закрывает соединение, учёт это видит


async def test_connection_taken_and_not_returned_is_named(tmp_path: Path) -> None:
    """W4: соединение выдано и не возвращено — сессия мимо `async with`."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'lent.db'}")
    with ConnectionLedger() as ledger:
        conn = await engine.connect()
        await conn.execute(text("select 1"))
        found = ledger.leaks()
        await conn.close()
        await engine.dispose()
        after = ledger.leaks()

    assert any(NOT_RETURNED in problem for problem in found)  # W4
    assert found[0].startswith("1 соединени(й) выдано пулом")  # W4
    assert after == []  # W4


async def test_in_memory_engine_without_dispose_is_named() -> None:
    """W5: база `:memory:` — `StaticPool`, у которого `checkedout()` нет вовсе.

    На нём жили 16 утечек из 18 (фикстура `test_storage.py` и тесты разбора).
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    with ConnectionLedger() as ledger:
        await _touch(engine)
        found = ledger.leaks()
        pool_can_tell = hasattr(engine.pool, "checkedout")
        await engine.dispose()

    assert not pool_can_tell  # W5: канонной фикстуре нечего спросить у этого пула
    assert len(found) == 1 and NOT_DISPOSED in found[0]  # W5


async def test_owned_database_leaves_nothing_and_ledger_detaches(tmp_path: Path) -> None:
    """W6: у движка есть владелец — сторож молчит; вышли из учёта — он не слушает.

    Вторая половина не косметика: учёт, который не снимается, копил бы по шесть
    слушателей на каждый тест сьюта.
    """
    with ConnectionLedger() as ledger:
        async with owned_database(f"sqlite+aiosqlite:///{tmp_path / 'clean.db'}") as db:
            await db.create_all()
            async with db.session() as session:
                await session.execute(text("select 1"))
    quiet = ledger.leaks()

    late = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'late.db'}")
    await _touch(late)  # течёт ПОСЛЕ выхода из учёта — учёт не должен этого видеть
    after_exit = ledger.leaks()
    await late.dispose()

    assert quiet == []  # W6
    assert after_exit == []  # W6


def test_connection_opened_in_another_thread_is_seen(tmp_path: Path) -> None:
    """W7: TestClient держит приложение в своём потоке и своём цикле — учёт видит и его."""
    engines: list[AsyncEngine] = []

    async def open_in_worker() -> None:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'thread.db'}")
        await _touch(engine)
        engines.append(engine)

    with ConnectionLedger() as ledger:
        worker = threading.Thread(target=asyncio.run, args=(open_in_worker(),))
        worker.start()
        worker.join()
        found = ledger.leaks()
        asyncio.run(engines[0].dispose())
        after = ledger.leaks()

    assert len(found) == 1 and NOT_DISPOSED in found[0]  # W7
    assert after == []  # W7


def test_a_frame_that_never_comes_fails_the_test(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сервер молчит — тест падает за срок, а не висит (под mutmut — таймаут мутанта)."""
    monkeypatch.setattr(conftest, "WS_FRAME_DEADLINE_S", 0.05)

    async def silent(websocket: WebSocket) -> None:
        await websocket.accept()
        with contextlib.suppress(WebSocketDisconnect):
            await websocket.receive_text()

    app = Starlette(routes=[WebSocketRoute("/ws", silent)])
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        with pytest.raises(AssertionError, match="не прислал кадр"):
            ws.receive_json()
