"""Summary service: validation contract, retry, minimal degrade, vocabulary merge."""

import json
from pathlib import Path

import pytest

from app.config import Settings
from app.knowledge.prompts import PromptLibrary
from app.storage.db import Database
from app.storage.repositories.interviews import InterviewRepository
from app.storage.repositories.reviews import ReviewRepository
from app.storage.repositories.vocabulary import VocabularyRepository
from app.summary.service import SummaryService
from app.summary.validate import SummaryInvalid, extract_json, validate_summary
from tests.fakes import ScriptedLlm

VALID = {
    "overall_summary": "Solid session with strong specifics.",
    "scores": {
        "clarity": 4,
        "structure": 3,
        "technical_depth": 4,
        "english_fluency": 3,
        "positioning": 2,
    },
    "strengths": [{"text": "Led with the metric", "reference": "Q2"}],
    "improvements": [],
    "weak_answers": [],
    "vocabulary": [
        {
            "term_en": "trade-off",
            "translation_ru": "компромисс",
            "example_en": "The trade-off was latency versus cost.",
            "category": "architecture",
        }
    ],
    "consistency_flags": [],
    "next_session_focus": ["lead with metrics"],
}


def test_extract_json_from_prose_and_fences() -> None:
    raw = 'Here you go:\n```json\n{"a": 1}\n```\nDone.'
    assert extract_json(raw) == {"a": 1}
    with pytest.raises(SummaryInvalid, match="no JSON"):
        extract_json("no json here")
    with pytest.raises(SummaryInvalid, match="invalid JSON"):
        extract_json("{broken}")


def test_validate_rejects_bad_scores_and_incomplete_vocabulary() -> None:
    bad_scores = json.loads(json.dumps(VALID))
    bad_scores["scores"]["clarity"] = 7
    with pytest.raises(SummaryInvalid, match=r"scores\.clarity"):
        validate_summary(bad_scores, require_vocabulary=True)

    no_translation = json.loads(json.dumps(VALID))
    no_translation["vocabulary"][0]["translation_ru"] = ""  # FR-6.3 hard rule
    with pytest.raises(SummaryInvalid, match="vocabulary"):
        validate_summary(no_translation, require_vocabulary=True)

    ok = validate_summary(json.loads(json.dumps(VALID)), require_vocabulary=True)
    assert ok["vocabulary"][0]["term_en"] == "trade-off"


def test_validate_rejects_cyrillic_body() -> None:
    data = json.loads(json.dumps(VALID))
    data["overall_summary"] = "Отличная сессия"
    with pytest.raises(SummaryInvalid, match="English"):
        validate_summary(data, require_vocabulary=True)


@pytest.fixture
def prompts(tmp_path: Path) -> PromptLibrary:
    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "templates").mkdir(parents=True)
    (prompts_dir / "summary_system.txt").write_text("summary system")
    (prompts_dir / "minimal_summary_system.txt").write_text("minimal system")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    return PromptLibrary(prompts_dir, knowledge)


async def _seed_sessions(db: Database) -> tuple[InterviewRepository, ReviewRepository]:
    interviews = InterviewRepository(db)
    reviews = ReviewRepository(db)
    await interviews.create("i1", interview_mode="m", persona="p")
    await interviews.checkpoint("i1", [{"role": "user", "text": "I built a CRM."}], {})
    await reviews.create("r1", source_interview_id="i1", persona="rf")
    await reviews.checkpoint("r1", [{"role": "agent", "text": "Q1 was strong."}], {})
    return interviews, reviews


def _service(llm: ScriptedLlm, db: Database, prompts: PromptLibrary) -> SummaryService:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    return SummaryService(
        llm,
        prompts,
        InterviewRepository(db),
        ReviewRepository(db),
        VocabularyRepository(db),
        settings,
    )


async def test_full_summary_stores_debrief_and_vocabulary(prompts: PromptLibrary) -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    interviews, _ = await _seed_sessions(db)
    llm = ScriptedLlm([["<think>hm</think>", json.dumps(VALID)]])
    service = _service(llm, db, prompts)

    data = await service.generate_full("i1", "r1")
    assert data is not None and data["vocabulary_added"] == 1
    row = await interviews.get("i1")
    assert row is not None and row.summary_kind == "full"
    stored = json.loads(row.debrief_json or "{}")
    assert stored["scores"]["clarity"] == 4
    entries = await VocabularyRepository(db).list()
    assert entries[0].term_en == "trade-off"
    # R1 with 16K ctx for the offline pass (doc 20)
    assert "INTERVIEW TRANSCRIPT" in llm.calls[0][1]["content"]
    assert "REVIEW TRANSCRIPT" in llm.calls[0][1]["content"]


async def test_invalid_json_retries_with_error_hint(prompts: PromptLibrary) -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    await _seed_sessions(db)
    llm = ScriptedLlm([["not json at all"], [json.dumps(VALID)]])
    service = _service(llm, db, prompts)

    data = await service.generate_full("i1", "r1")
    assert data is not None
    retry_message = llm.calls[1][-1]["content"]
    assert "Your JSON was invalid" in retry_message


async def test_full_degrades_to_minimal_after_two_failures(prompts: PromptLibrary) -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    interviews, _ = await _seed_sessions(db)
    minimal_ok = json.loads(json.dumps(VALID))
    minimal_ok["vocabulary"] = []
    llm = ScriptedLlm([["junk"], ["junk"], [json.dumps(minimal_ok)]])
    service = _service(llm, db, prompts)

    data = await service.generate_full("i1", "r1")
    assert data is not None
    row = await interviews.get("i1")
    assert row is not None and row.summary_kind == "minimal"  # degraded, transcripts intact
    assert "minimal system" in llm.calls[2][0]["content"]  # switched to the minimal prompt


async def test_minimal_gives_up_quietly(prompts: PromptLibrary) -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    interviews, _ = await _seed_sessions(db)
    llm = ScriptedLlm([["junk"], ["junk"]])
    service = _service(llm, db, prompts)

    assert await service.generate_minimal("i1") is None
    row = await interviews.get("i1")
    assert row is not None and row.debrief_json is None  # nothing broken, nothing stored
