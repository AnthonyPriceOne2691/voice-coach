"""Repository integration tests on in-memory SQLite (doc 18: real DB, mocked AI).

База — фикстура `db` из `conftest.py`, с `dispose()` в teardown. Прежняя локальная
фикстура делала `return` вместо `yield`, то есть teardown у неё не было вовсе.
"""

import json

from app.storage.db import Database
from app.storage.repositories.interviews import InterviewRepository
from app.storage.repositories.reviews import ReviewRepository
from app.storage.repositories.settings_repo import SettingsRepository
from app.storage.repositories.vocabulary import VocabularyRepository
from app.storage.turns import TranscriptBuffer


async def test_interview_lifecycle(db: Database) -> None:
    repo = InterviewRepository(db)
    await repo.create(
        "i1", interview_mode="technical_project_walkthrough", persona="senior_colleague"
    )

    buffer = TranscriptBuffer()
    buffer.append("agent", "Hello.", state="INTRO")
    buffer.append("user", "Hi.", state="INTRO", question_id="project_overview")
    await repo.checkpoint("i1", buffer.to_json_list(), {"question_count": 1})

    row = await repo.get("i1")
    assert row is not None and row.status == "in_progress"
    turns = json.loads(row.transcript_json)
    assert turns[1]["question_id"] == "project_overview"
    assert turns[1]["turn_index"] == 1

    await repo.finish("i1", status="completed")
    row = await repo.get("i1")
    assert row is not None and row.status == "completed" and row.ended_at is not None

    await repo.set_debrief("i1", {"scores": {"clarity": 4}}, "minimal")
    row = await repo.get("i1")
    assert row is not None and row.summary_kind == "minimal"
    assert json.loads(row.debrief_json or "{}")["scores"]["clarity"] == 4


async def test_interview_list_and_cascade_delete(db: Database) -> None:
    interviews = InterviewRepository(db)
    reviews = ReviewRepository(db)
    await interviews.create("i1", interview_mode="m", persona="p")
    await interviews.create("i2", interview_mode="m", persona="p")
    await reviews.create("r1", source_interview_id="i1", persona="recruiter_friend")
    await interviews.link_review("i1", "r1")

    listed = await interviews.list_recent()
    assert {r.id for r in listed} == {"i1", "i2"}

    assert await interviews.delete_cascade("i1") is True
    assert await interviews.get("i1") is None
    assert await reviews.get("r1") is None
    assert await interviews.delete_cascade("missing") is False


async def test_review_lifecycle(db: Database) -> None:
    interviews = InterviewRepository(db)
    reviews = ReviewRepository(db)
    await interviews.create("i1", interview_mode="m", persona="p")
    await reviews.create("r1", source_interview_id="i1", persona="recruiter_friend")
    await reviews.checkpoint("r1", [{"role": "agent", "text": "Q1 was strong."}], {})
    await reviews.finish("r1", status="completed")

    row = await reviews.get("r1")
    assert row is not None and row.status == "completed"
    assert (await reviews.for_interview("i1"))[0].id == "r1"


async def test_vocabulary_translation_can_be_rewritten(db: Database) -> None:
    """Починка банка (S-H6): перевод переписывается, пропавшая запись — не молча."""
    repo = VocabularyRepository(db)
    await repo.merge(
        [{"term_en": "impact statement", "translation_ru": "陳述", "example_en": "x"}],
        session_id="s1",
    )
    entry = (await repo.list())[0]

    assert await repo.set_translation(entry.id, "заявление о вкладе") is True
    assert (await repo.list())[0].translation_ru == "заявление о вкладе"
    # Скрипт чистки обязан уметь сказать «не нашёл», а не отчитаться об успехе.
    assert await repo.set_translation("no-such-id", "что угодно") is False


async def test_vocabulary_merge_dedup_and_soft_delete(db: Database) -> None:
    repo = VocabularyRepository(db)
    items = [
        {
            "term_en": "trade-off",
            "translation_ru": "компромисс",
            "example_en": "The trade-off was X.",
        },
        {
            "term_en": "throughput",
            "translation_ru": "пропускная способность",
            "example_en": "We doubled throughput.",
        },
        {"term_en": "no-translation", "translation_ru": "", "example_en": "x"},  # dropped (S-H4)
    ]
    assert await repo.merge(items, session_id="s1") == 2
    # exact duplicate -> times_seen bump, not a new row
    assert await repo.merge([items[0]], session_id="s2") == 0
    entries = await repo.list()
    assert len(entries) == 2
    tradeoff = next(e for e in entries if e.term_en == "trade-off")
    assert tradeoff.times_seen == 2

    # soft delete -> hidden from list, never re-added
    assert await repo.soft_delete(tradeoff.id) is True
    assert all(e.term_en != "trade-off" for e in await repo.list())
    assert await repo.merge([items[0]], session_id="s3") == 0
    assert all(e.term_en != "trade-off" for e in await repo.list())

    # search and sort
    assert (await repo.list(query="through"))[0].term_en == "throughput"


async def test_settings_defaults_and_patch(db: Database) -> None:
    repo = SettingsRepository(db)
    values = await repo.get_all()
    assert values["interview_duration_min"] == 15

    updated = await repo.update({"interview_duration_min": 30, "unknown_key": 1})
    assert updated["interview_duration_min"] == 30
    assert "unknown_key" not in updated
    assert (await repo.get_all())["interview_duration_min"] == 30
