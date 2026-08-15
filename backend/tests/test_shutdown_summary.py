"""B5: гашение приложения при живой фоновой суммаризации.

Единственный пример из спеки поставки `ws-disconnect-hang`, оставшийся БЕЗ
машинного оракула: «сценарий требует настоящей LLM в полёте». Требует он не
настоящей, а **управляемой** — такой, которую можно остановить ровно в середине
хода и отпустить по команде. Подставной клиент это умеет лучше живого.

Проверяются оба конца поведения:
  - задача, начатая до гашения, ДОЖИДАЕТСЯ и дописывает разбор в базу;
  - задача, которая не укладывается в срок, не подвешивает процесс, а получает
    отмену и строку в лог.
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.common.interfaces import ChatMessage
from app.main import create_app
from app.storage.db import Database
from app.storage.repositories.interviews import InterviewRepository
from app.summary import service as summary_service
from tests.fakes import FakeStt
from tests.helpers import make_container

pytestmark = pytest.mark.asyncio

SUMMARY = {
    "overall_summary": "Solid session.",
    "scores": {
        "clarity": 4,
        "structure": 3,
        "technical_depth": 4,
        "english_fluency": 3,
        "positioning": 3,
    },
    "strengths": [],
    "improvements": [],
    "weak_answers": [],
    "vocabulary": [
        {"term_en": "trade-off", "translation_ru": "компромисс", "example_en": "A trade-off."}
    ],
    "consistency_flags": [],
    "next_session_focus": [],
}


class SlowLlm:
    """Отвечает не сразу: задача заведомо ЖИВА в момент гашения."""

    def __init__(self, payload: str, delay: float) -> None:
        self._payload = payload
        self._delay = delay
        self.started = asyncio.Event()

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        self.started.set()
        await asyncio.sleep(self._delay)
        yield self._payload


class HangingLlm:
    """Не отвечает никогда — так выглядит зависшая модель со стороны процесса."""

    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        self.started.set()
        await asyncio.Event().wait()
        yield ""  # pragma: no cover — сюда не доходит, и в этом весь смысл


async def _seed(container) -> None:  # type: ignore[no-untyped-def]
    await container.db.create_all()
    await container.interviews.create("i1", interview_mode="m", persona="p")
    await container.interviews.checkpoint("i1", [{"role": "user", "text": "I built a CRM."}], {})
    await container.reviews.create("r1", source_interview_id="i1", persona="rf")
    await container.reviews.checkpoint("r1", [{"role": "agent", "text": "Q1 was strong."}], {})


async def test_shutdown_waits_for_a_running_background_summary(tmp_path: Path) -> None:
    """B5: разбор, начатый до гашения, дописывается — а не рвётся на середине.

    Проверяются ДВЕ вещи, потому что каждой поодиночке мало: разбор оказался в
    базе (значит задача дошла до конца) И выход из lifespan занял не меньше, чем
    длится сам разбор (значит гашение его ДОЖДАЛОСЬ, а не разминулось с ним).
    """
    delay = 0.3
    llm = SlowLlm(json.dumps(SUMMARY), delay)
    container = make_container(tmp_path, llm, FakeStt())
    await _seed(container)
    app = create_app(container)

    started_at = time.monotonic()
    async with app.router.lifespan_context(app):
        container.summaries.schedule_full("i1", "r1")
        await llm.started.wait()  # задача точно в полёте, а не в очереди
    elapsed = time.monotonic() - started_at

    fresh = InterviewRepository(Database(container.settings.database_url))
    row = await fresh.get("i1")
    assert row is not None and row.summary_kind == "full"
    assert json.loads(row.debrief_json or "{}")["scores"]["clarity"] == 4
    assert elapsed >= delay * 0.8


async def test_shutdown_gives_up_on_a_hung_summary_and_says_so(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B5, вторая половина: зависшая модель не превращает гашение в вис.

    Срок ожидания подменён на 50 ms: проверяется ПОВЕДЕНИЕ на просрочке, а не
    десять секунд ожидания в сьюте. Само значение (10 s) — предохранитель, и его
    величина ничего не доказывает.
    """
    monkeypatch.setattr(summary_service, "SHUTDOWN_SUMMARY_TIMEOUT_S", 0.05)
    llm = HangingLlm()
    container = make_container(tmp_path, llm, FakeStt())
    await _seed(container)
    app = create_app(container)

    with caplog.at_level(logging.WARNING):
        async with app.router.lifespan_context(app):
            container.summaries.schedule_full("i1", "r1")
            await llm.started.wait()

    assert "summary task(s) cancelled by timeout" in caplog.text
    fresh = InterviewRepository(Database(container.settings.database_url))
    row = await fresh.get("i1")
    # Транскрипт — невосполнимый артефакт: он на месте даже когда разбора нет.
    assert row is not None and row.summary_kind is None
    assert json.loads(row.transcript_json)[0]["text"] == "I built a CRM."
