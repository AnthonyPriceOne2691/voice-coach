"""Гашение приложения: «отменить» и «дождаться отмены» — два шага (L90).

Обе двери гашения ждут свою задачу со сроком: фоновую суммаризацию —
`SummaryService.aclose()`, уборку отключившейся ws-сессии — `_drain` в `main.py`.
По сроку задачу надо ОТМЕНИТЬ и ДОЖДАТЬСЯ, пока отмена размотается: выход из
`async with db.session()` сам требует `await` (rollback и возврат соединения).
Пропущен второй шаг — `dispose()` движка проходит раньше, чем отменённая задача
вернёт соединение в пул, и соединение остаётся вне пула. Добивает его потом сборщик
мусора — тот же механизм, что в августе вешал прогон целиком (L5, D4 поставки
`ws-disconnect-hang`).

Задача застревает не в модели, а ВНУТРИ записи: соединение выдано пулом, запрос не
кончается. Так со стороны процесса выглядит запись, которую держит чужая
блокировка базы. Настоящая база для этого не нужна — нужна управляемая остановка
(L60), её даёт репозиторий-наследник ниже.

Судит учёт соединений пула (`ConnectionLedger`, поставка test-leaks) сразу после
выхода из lifespan: движок к этому моменту погашен, и всё взятое обязано быть
возвращено и закрыто. Учёт открыт ДО первого соединения теста, поэтому видит и
открытие, и выдачу.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from app import main as app_main
from app.api import ws_voice
from app.api.ws_voice import ws_session
from app.container import Container
from app.main import create_app
from app.storage.db import Database
from app.storage.repositories.interviews import InterviewRepository
from app.summary import service as summary_service
from app.summary.service import SummaryService
from tests.db_lifecycle import ConnectionLedger
from tests.fakes import FakeLlm, FakeStt, GoneClientWebSocket
from tests.helpers import MINIMAL_SUMMARY, make_container

pytestmark = pytest.mark.asyncio

#: Полный разбор, который проходит проверку: у полного разбора словарь обязателен.
SUMMARY = {
    **MINIMAL_SUMMARY,
    "vocabulary": [
        {"term_en": "trade-off", "translation_ru": "компромисс", "example_en": "A trade-off."}
    ],
}

#: Сроки гашения в тестах. Проверяется поведение НА просрочке, а не сами 5 и 10 s:
#: их величина — предохранитель и ничего не доказывает (как в test_shutdown_summary).
SHORT_DEADLINE_S = 0.05

#: Сколько разматывается отмена записи. Rollback и возврат соединения идут через
#: поток aiosqlite и под нагрузкой занимают десятки миллисекунд: в замере test-leaks
#: ожидание отмены со сроком 50 ms оставляло утечку в 2 случаях из ~45. Здесь размотка
#: заведомо дольше короткого срока — и ожидание отмены СО сроком краснеет на каждом
#: прогоне, а не только на занятой машине.
SLOW_UNWIND_S = 4 * SHORT_DEADLINE_S


class StuckOnFinalWrite(InterviewRepository):
    """Итоговая запись сессии берёт соединение и не отпускает его, пока не отменят.

    Итоговых записей две — ровно по одной на каждую дверь гашения: `finish` пишет
    уборка ws-сессии, `set_debrief` — фоновая суммаризация. Остальные методы
    настоящие: сессия создаётся и чекпойнтится как обычно.
    """

    def __init__(self, db: Database) -> None:
        super().__init__(db)
        #: Выставляется, когда соединение уже выдано пулом и запись встала.
        self.holding = asyncio.Event()

    async def _hold_connection(self) -> None:
        async with self._db.session() as session:
            await session.execute(text("select 1"))  # соединение выдано пулом
            self.holding.set()
            try:
                await asyncio.Event().wait()  # разрешить некому: выход только через отмену
            finally:
                await asyncio.sleep(SLOW_UNWIND_S)  # и размотка отмены не мгновенна

    async def finish(self, session_id: str, *, status: str) -> None:
        await self._hold_connection()

    async def set_debrief(self, session_id: str, debrief: dict[str, Any], kind: str) -> None:
        await self._hold_connection()


async def _seed_interview_and_review(container: Container) -> None:
    await container.db.create_all()
    await container.interviews.create("i1", interview_mode="m", persona="p")
    await container.reviews.create("r1", source_interview_id="i1", persona="rf")


async def test_shutdown_waits_until_a_cancelled_summary_returns_its_connection(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E1: `SummaryService.aclose()` по сроку отменяет задачу и ДОЖИДАЕТСЯ отмены.

    До правки 5 из 5 красных (поставка test-leaks, H5): отмена только помечалась,
    `dispose()` проходил раньше, и соединение оставалось выданным и не закрытым.
    """
    monkeypatch.setattr(summary_service, "SHUTDOWN_SUMMARY_TIMEOUT_S", SHORT_DEADLINE_S)
    with ConnectionLedger() as ledger:
        llm = FakeLlm([json.dumps(SUMMARY)])
        container = make_container(tmp_path, llm, FakeStt())
        stuck = StuckOnFinalWrite(container.db)
        container.summaries = SummaryService(
            llm,
            container.prompts,
            stuck,
            container.reviews,
            container.vocabulary,
            container.settings,
        )
        await _seed_interview_and_review(container)
        app = create_app(container)
        with caplog.at_level(logging.WARNING):
            async with app.router.lifespan_context(app):
                container.summaries.schedule_full("i1", "r1")
                await stuck.holding.wait()  # разбор готов и встал на записи в базу
        leaks = ledger.leaks()

    assert leaks == []  # E1: к концу гашения соединение возвращено и закрыто
    assert "summary task(s) cancelled by timeout" in caplog.text  # E1: отмена названа


async def test_shutdown_cancels_a_stuck_ws_cleanup_and_waits_for_it(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2: `_drain` по сроку ОТМЕНЯЕТ застрявшую уборку ws-сессии и дожидается отмены.

    До правки 5 из 5 красных (H5): по сроку `_drain` только писал в лог, и движок
    гасился при живой уборке, которая держала соединение.

    Транспорт поддельный по той же причине, что в `test_ws_voice.py`: тест-клиент на
    закрытии сам отменяет задачу приложения, а uvicorn — нет.
    """
    monkeypatch.setattr(ws_voice, "DISCONNECT_CLEANUP_TIMEOUT_S", SHORT_DEADLINE_S)
    monkeypatch.setattr(app_main, "SHUTDOWN_DRAIN_TIMEOUT_S", SHORT_DEADLINE_S)
    with ConnectionLedger() as ledger:
        container = make_container(tmp_path, FakeLlm(["Ok? "]), FakeStt())
        stuck = StuckOnFinalWrite(container.db)
        container.interviews = stuck
        app = create_app(container)
        ws = GoneClientWebSocket(app, [{"type": "start_interview", "payload": {}}])
        with caplog.at_level(logging.WARNING):
            async with app.router.lifespan_context(app):
                await ws_session(ws)  # клиент ушёл после приветствия, не послав end_session
                await stuck.holding.wait()  # уборка дошла до итоговой записи и встала
        leaks = ledger.leaks()

    assert ws.sent[0]["type"] == "session_started"  # E2: сессия была, уборке было что писать
    assert leaks == []  # E2: к концу гашения соединение возвращено и закрыто
    assert "ws cleanup(s) did not finish in time" in caplog.text  # E2: срок назван в логе
