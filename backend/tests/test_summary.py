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
from app.storage.turns import META_STATE
from app.summary.service import SummaryService
from app.summary.validate import (
    SummaryInvalidError,
    extract_json,
    translation_is_russian,
    validate_summary,
)
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
    with pytest.raises(SummaryInvalidError, match="no JSON"):
        extract_json("no json here")
    with pytest.raises(SummaryInvalidError, match="invalid JSON"):
        extract_json("{broken}")


def test_validate_rejects_bad_scores_and_incomplete_vocabulary() -> None:
    bad_scores = json.loads(json.dumps(VALID))
    bad_scores["scores"]["clarity"] = 7
    with pytest.raises(SummaryInvalidError, match=r"scores\.clarity"):
        validate_summary(bad_scores, require_vocabulary=True)

    no_translation = json.loads(json.dumps(VALID))
    no_translation["vocabulary"][0]["translation_ru"] = ""  # FR-6.3 hard rule
    with pytest.raises(SummaryInvalidError, match="vocabulary"):
        validate_summary(no_translation, require_vocabulary=True)

    ok = validate_summary(json.loads(json.dumps(VALID)), require_vocabulary=True)
    assert ok["vocabulary"][0]["term_en"] == "trade-off"


def test_validate_rejects_cyrillic_body() -> None:
    data = json.loads(json.dumps(VALID))
    data["overall_summary"] = "Отличная сессия"
    with pytest.raises(SummaryInvalidError, match="English"):
        validate_summary(data, require_vocabulary=True)


def test_cjk_leak_in_translation_is_caught() -> None:
    """S-H6 (V1–V3): поле, выпавшее из проверок, снова проверяется.

    Запись взята из живого банка слов: `deepseek-r1:14b` срывается на китайский,
    и `S-H2_en_body` это поле ЯВНО исключает — то есть до этой поставки его не
    проверяло ничто.
    """
    assert not translation_is_russian("выразительный陳述")  # V1: та самая запись
    assert not translation_is_russian("陳述")
    assert not translation_is_russian("Redis/RabbitMQ")  # V3: кириллицы нет вовсе
    assert not translation_is_russian("")

    # V2: латиница внутри русского перевода законна — `Redis`, `outreach` и
    # `Kubernetes` по-русски так и остаются. Запрет дал бы ложные срабатывания
    # на каждой второй записи, а это дороже пропуска (Delivery §4.3b).
    assert translation_is_russian("автоматизация outreach")
    assert translation_is_russian("компромисс")
    assert translation_is_russian("очередь задач (Redis/RQ)")


@pytest.fixture
def prompts(tmp_path: Path) -> PromptLibrary:
    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "templates").mkdir(parents=True)
    (prompts_dir / "summary_system.txt").write_text("summary system")
    (prompts_dir / "minimal_summary_system.txt").write_text("minimal system")
    (prompts_dir / "translate_term_system.txt").write_text("translate to russian")
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


def _with_translation(translation: str) -> dict:
    data = json.loads(json.dumps(VALID))
    data["vocabulary"][0]["translation_ru"] = translation
    return data


async def test_broken_translation_is_repaired_on_the_voice_model(prompts: PromptLibrary) -> None:
    """V4: запись чинится, а не теряется — и чинит её qwen, а не тот, кто сломал.

    D-8: R1 живёт только в офлайн-разборе, и именно он срывается на китайский.
    Просить починку у него значит просить у источника дефекта.
    """
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    await _seed_sessions(db)
    llm = ScriptedLlm([[json.dumps(_with_translation("выразительный陳述"))], ["компромисс"]])
    service = _service(llm, db, prompts)

    data = await service.generate_full("i1", "r1")

    assert data is not None
    assert data["vocabulary"][0]["translation_ru"] == "компромисс"
    entries = await VocabularyRepository(db).list()
    assert entries[0].translation_ru == "компромисс"  # в банк попал ПОЧИНЕННЫЙ перевод
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert llm.models == [settings.ollama_model_review, settings.ollama_model_interview]
    repair_prompt = llm.calls[1][1]["content"]
    assert repair_prompt.startswith("trade-off")  # чинили именно термин
    # Пример употребления идёт вместе с термином: без него перевод делается
    # вслепую, и живой прогон дал «заявление об impactе» (verify-report).
    assert "The trade-off was latency versus cost." in repair_prompt


async def test_unrepairable_translation_is_dropped_out_loud(
    prompts: PromptLibrary, caplog: pytest.LogCaptureFixture
) -> None:
    """V5: потеря записи обязана звучать — иначе она неотличима от «слова не было»."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    await _seed_sessions(db)
    llm = ScriptedLlm([[json.dumps(_with_translation("выразительный陳述"))], ["陳述"]])
    service = _service(llm, db, prompts)

    with caplog.at_level("WARNING"):
        data = await service.generate_full("i1", "r1")

    assert data is not None and data["vocabulary"] == []
    assert await VocabularyRepository(db).list() == []
    assert "trade-off" in caplog.text and "иероглифы" in caplog.text


async def test_all_vocabulary_broken_does_not_kill_the_summary(prompts: PromptLibrary) -> None:
    """V6: словарь — часть разбора, а не его условие. Оценки и текст остаются."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    interviews, _ = await _seed_sessions(db)
    llm = ScriptedLlm([[json.dumps(_with_translation("陳述"))], ["陳述"]])
    service = _service(llm, db, prompts)

    data = await service.generate_full("i1", "r1")

    assert data is not None and data["scores"]["clarity"] == 4
    row = await interviews.get("i1")
    assert row is not None and row.summary_kind == "full"


async def test_clean_summary_costs_no_extra_call(prompts: PromptLibrary) -> None:
    """V7: исправный перевод не платит ничем — починка вызывается только по нужде."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    await _seed_sessions(db)
    llm = ScriptedLlm([[json.dumps(VALID)]])
    service = _service(llm, db, prompts)

    await service.generate_full("i1", "r1")

    assert len(llm.calls) == 1


async def test_meta_turns_never_reach_the_summary_prompt(prompts: PromptLibrary) -> None:
    """P9: просьба о темпе была, но она не реплика кандидата и не улика в разборе."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    interviews = InterviewRepository(db)
    reviews = ReviewRepository(db)
    await interviews.create("i1", interview_mode="m", persona="p")
    await interviews.checkpoint(
        "i1",
        [
            {"role": "user", "text": "I built a CRM.", "state": "CORE_QUEST"},
            {"role": "user", "text": "Slower, please.", "state": META_STATE},
            {"role": "agent", "text": "Sure, slowing down.", "state": META_STATE},
        ],
        {},
    )
    await reviews.create("r1", source_interview_id="i1", persona="rf")
    await reviews.checkpoint("r1", [{"role": "agent", "text": "Q1 was strong."}], {})
    llm = ScriptedLlm([[json.dumps(VALID)]])

    await _service(llm, db, prompts).generate_full("i1", "r1")

    sent = llm.calls[0][1]["content"]
    assert "I built a CRM." in sent  # содержательное на месте
    assert "Slower, please." not in sent
    assert "Sure, slowing down." not in sent


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
