"""Жизнь соединений с базой в тестах: владелец движка и учёт соединений пула.

Отдельным модулем, а не в `conftest.py` и не в `helpers.py`, по двум причинам. У
учёта два потребителя: autouse-сторож сьюта и тесты самого сторожа
(`test_connection_guard.py`). И `conftest.py` не должен тянуть `starlette.testclient`
через `helpers.py`: предупреждение на импорте того модуля без строки ignore в
`pyproject.toml` роняло бы загрузку conftest, то есть весь прогон разом, а не сбор
семи модулей (замер 2026-10-23).

Учёт синхронен с тестом. Незакрытое соединение aiosqlite сообщает о себе само, из
`Connection.__del__`, но только тогда, когда до него дойдёт СБОРЩИК МУСОРА. Движок
живёт в циклических ссылках и собирается не в конце своего теста, а там, где
сработает порог поколения. Замер 2026-10-23: соединения оставляли открытыми 18
тестов, а падали 5 других, среди них `test_tts_piper.py`, который базы не касается,
и набор упавших менялся от одного включения coverage. События пула приходят в момент
открытия, выдачи, возврата и закрытия соединения, поэтому утечку здесь называет тот
тест, который её сделал.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.pool import Pool

from app.storage.db import Database


@asynccontextmanager
async def owned_database(database_url: str) -> AsyncIterator[Database]:
    """Движок, у которого есть владелец: `dispose()` на ЛЮБОМ выходе, с исключением тоже.

    Без него соединение остаётся в пуле открытым, пока движок не найдёт сборщик
    мусора, — а он находит его в чужом тесте.
    """
    db = Database(database_url)
    try:
        yield db
    finally:
        await db.dispose()


class ConnectionLedger:
    """Соединения пула за время учёта: какие не закрыты и какие не возвращены.

    Слушает КЛАСС `Pool`, а не конкретный движок, поэтому видит все движки сразу:
    приложение под TestClient (оно работает в своём потоке), фикстуру, помощника,
    сам тест. Регистрировать движки руками не нужно, забыть зарегистрировать нельзя.

    Чем это шире фикстуры `pool.checkedout() == 0` из канона (CQG §2.7). Та видит
    одну форму утечки из двух и здесь не нашла бы ни одной из 18: у тех тестов
    каждое соединение было ВОЗВРАЩЕНО в пул, но пул никто не закрыл, потому что
    `dispose()` не вызывали. Кроме того, у `StaticPool` (база `:memory:`) метода
    `checkedout()` нет вовсе, а 16 из 18 утечек были как раз на нём.
    """

    def __init__(self) -> None:
        self._open: set[int] = set()
        self._lent: set[int] = set()
        # Один объект на событие: тот же самый уходит и в listen, и в remove.
        self._listeners: dict[str, Callable[..., None]] = {
            "connect": self._on_connect,
            "close": self._on_close,
            "close_detached": self._on_close_detached,
            "detach": self._on_detach,
            "checkout": self._on_checkout,
            "checkin": self._on_checkin,
        }

    def __enter__(self) -> "ConnectionLedger":
        for name, listener in self._listeners.items():
            event.listen(Pool, name, listener)
        return self

    def __exit__(self, *exc_info: object) -> None:
        # Снимать обязательно: иначе каждый тест добавлял бы шесть слушателей
        # к классу, и к концу сьюта их были бы тысячи на каждом событии пула.
        for name, listener in self._listeners.items():
            event.remove(Pool, name, listener)

    def leaks(self) -> list[str]:
        """Что осталось на руках: пусто — значит всё взятое возвращено и закрыто."""
        problems = []
        if self._lent:
            problems.append(
                f"{len(self._lent)} соединени(й) выдано пулом и не возвращено: сессия "
                "взята мимо `async with db.session()`, или её уборку оборвала отмена"
            )
        if self._open:
            problems.append(
                f"{len(self._open)} соединени(й) открыто и не закрыто: движок без "
                "`dispose()`. У каждой `Database` должен быть владелец, который её "
                "гасит: фикстура с yield, `owned_database`, lifespan приложения"
            )
        return problems

    # Ключ — id объекта, а не сам объект: сильная ссылка из учёта продлила бы
    # жизнь соединению и сдвинула бы момент, о котором учёт и должен сообщить.
    def _on_connect(self, dbapi_connection: Any, _record: Any) -> None:
        self._open.add(id(dbapi_connection))

    def _on_close(self, dbapi_connection: Any, _record: Any) -> None:
        self._open.discard(id(dbapi_connection))

    def _on_close_detached(self, dbapi_connection: Any) -> None:
        self._open.discard(id(dbapi_connection))

    def _on_detach(self, _dbapi_connection: Any, record: Any) -> None:
        # Отсоединённое соединение пулу больше ничего не должно; его закрытие
        # придёт отдельным событием `close_detached`.
        self._lent.discard(id(record))

    def _on_checkout(self, _dbapi_connection: Any, record: Any, _proxy: Any) -> None:
        self._lent.add(id(record))

    def _on_checkin(self, _dbapi_connection: Any, record: Any) -> None:
        self._lent.discard(id(record))
