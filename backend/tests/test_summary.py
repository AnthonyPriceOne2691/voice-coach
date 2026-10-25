"""Summary service: validation contract, retry, minimal degrade, vocabulary merge."""

import json
import re
from pathlib import Path

import pytest

from app.config import REPO_ROOT, Settings
from app.knowledge.prompts import PROFILE_PLACEHOLDER, PromptLibrary
from app.storage.db import Database
from app.storage.repositories.interviews import InterviewRepository
from app.storage.repositories.reviews import ReviewRepository
from app.storage.repositories.vocabulary import VocabularyRepository
from app.storage.turns import META_STATE
from app.summary.service import SCHEMA_HINT, SummaryService
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


# --- Поля-списки: форма схемы, а не «что прислала модель» -------------------------
#
# Живая запись от 2026-07-05 хранит `next_session_focus` ОДНОЙ строкой: подсказка
# говорила `next_session_focus [string]`, R1 прочёл «строка», валидатор тип не
# проверял, фронт позвал `.join` у строки — и History → Open давал пустую страницу.

#: Поля-списки так, как их объявляет подсказка модели: `имя [` после `: ` или `, `.
LIST_FIELDS_IN_HINT = re.findall(r"(?:: |, )(\w+) \[", SCHEMA_HINT)


def _with(field: str, value: object) -> dict:
    data = json.loads(json.dumps(VALID))
    data[field] = value
    return data


def test_string_list_fields_take_any_shape_and_store_a_list() -> None:
    cases = [
        ("Lead with the metric.", ["Lead with the metric."]),  # форма живой записи
        (["metrics first", "STAR"], ["metrics first", "STAR"]),  # список не трогается
        (None, []),
        ("   ", []),
        (42, []),
        ({"topic": "HITL"}, []),
        (["  kept  ", "", None, 3, {"x": 1}], ["kept"]),  # мусор внутри списка
    ]
    for field in ("next_session_focus", "consistency_flags"):
        for sent, stored in cases:
            shaped = validate_summary(_with(field, sent), require_vocabulary=True)[field]
            assert shaped == stored, f"{field}={sent!r}: ждали {stored!r}, получили {shaped!r}"


def test_object_list_fields_keep_objects_and_the_models_text() -> None:
    """Строка на месте объекта не пропадает: это текст модели, он становится главным полем."""
    cases = [
        ("strengths", "Led with the metric.", [{"text": "Led with the metric."}]),
        ("strengths", {"text": "Calm", "reference": "Q1"}, [{"text": "Calm", "reference": "Q1"}]),
        (
            "strengths",
            [{"text": "Calm"}, "Clear", None, 5, " "],
            [{"text": "Calm"}, {"text": "Clear"}],
        ),
        ("improvements", "Open with the impact.", [{"problem": "Open with the impact."}]),
        ("weak_answers", ["Q2 had no number."], [{"question": "Q2 had no number."}]),
        ("weak_answers", None, []),
    ]
    for field, sent, stored in cases:
        shaped = validate_summary(_with(field, sent), require_vocabulary=True)[field]
        assert shaped == stored, f"{field}={sent!r}: ждали {stored!r}, получили {shaped!r}"


def test_missing_list_fields_and_null_vocabulary_become_empty_lists() -> None:
    data = json.loads(json.dumps(VALID))
    for field in ("strengths", "improvements", "weak_answers", "consistency_flags"):
        del data[field]
    data["next_session_focus"] = None
    data["vocabulary"] = None  # minimal-разбору словарь не обязателен — не повод для повтора

    shaped = validate_summary(data, require_vocabulary=False)

    for field in LIST_FIELDS_IN_HINT:
        assert shaped[field] == [], f"{field}: {shaped[field]!r}"
    with pytest.raises(SummaryInvalidError, match="vocabulary"):  # полному — обязателен (S-H4)
        validate_summary(_with("vocabulary", "queues"), require_vocabulary=True)


def test_every_list_field_declared_in_the_hint_is_shaped() -> None:
    """Сторож КЛАССА, а не случая.

    Поле, которое подсказка модели объявляет списком (`имя [...]`), обязано
    доезжать до базы списком, что бы ни прислала модель. Новое поле-список в
    SCHEMA_HINT без строки в таблицах `validate.py` — красный тест здесь, а не
    пустая страница на демо.
    """
    # регулярка видит подсказку — иначе цикл ниже прошёл бы по пустому списку
    assert {"strengths", "vocabulary", "next_session_focus"} <= set(LIST_FIELDS_IN_HINT)
    for field in LIST_FIELDS_IN_HINT:
        for sent in ("one plain string", None, 7):
            shaped = validate_summary(_with(field, sent), require_vocabulary=False)[field]
            assert isinstance(shaped, list), (
                f"{field}={sent!r} дошёл бы до базы как {type(shaped).__name__}: SCHEMA_HINT "
                f"объявляет поле списком, а validate.py его не приводит — фронт на нём упадёт"
            )


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


async def test_full_summary_stores_debrief_and_vocabulary(
    prompts: PromptLibrary, db: Database
) -> None:
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


async def test_string_focus_from_the_model_is_stored_as_a_list(
    prompts: PromptLibrary, db: Database
) -> None:
    """Форма живой записи 2026-07-05 доезжает до БД уже списком — фронту нечего чинить."""
    interviews, _ = await _seed_sessions(db)
    llm = ScriptedLlm([[json.dumps(_with("next_session_focus", "Lead with the metric."))]])

    await _service(llm, db, prompts).generate_full("i1", "r1")

    row = await interviews.get("i1")
    assert row is not None
    assert json.loads(row.debrief_json or "{}")["next_session_focus"] == ["Lead with the metric."]


def _with_translation(translation: str) -> dict:
    data = json.loads(json.dumps(VALID))
    data["vocabulary"][0]["translation_ru"] = translation
    return data


async def test_broken_translation_is_repaired_on_the_voice_model(
    prompts: PromptLibrary, db: Database
) -> None:
    """V4: запись чинится, а не теряется — и чинит её qwen, а не тот, кто сломал.

    D-8: R1 живёт только в офлайн-разборе, и именно он срывается на китайский.
    Просить починку у него значит просить у источника дефекта.
    """
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
    prompts: PromptLibrary,
    caplog: pytest.LogCaptureFixture,
    db: Database,
) -> None:
    """V5: потеря записи обязана звучать — иначе она неотличима от «слова не было»."""
    await _seed_sessions(db)
    llm = ScriptedLlm([[json.dumps(_with_translation("выразительный陳述"))], ["陳述"]])
    service = _service(llm, db, prompts)

    with caplog.at_level("WARNING"):
        data = await service.generate_full("i1", "r1")

    assert data is not None and data["vocabulary"] == []
    assert await VocabularyRepository(db).list() == []
    assert "trade-off" in caplog.text and "иероглифы" in caplog.text


async def test_all_vocabulary_broken_does_not_kill_the_summary(
    prompts: PromptLibrary, db: Database
) -> None:
    """V6: словарь — часть разбора, а не его условие. Оценки и текст остаются."""
    interviews, _ = await _seed_sessions(db)
    llm = ScriptedLlm([[json.dumps(_with_translation("陳述"))], ["陳述"]])
    service = _service(llm, db, prompts)

    data = await service.generate_full("i1", "r1")

    assert data is not None and data["scores"]["clarity"] == 4
    row = await interviews.get("i1")
    assert row is not None and row.summary_kind == "full"


async def test_clean_summary_costs_no_extra_call(prompts: PromptLibrary, db: Database) -> None:
    """V7: исправный перевод не платит ничем — починка вызывается только по нужде."""
    await _seed_sessions(db)
    llm = ScriptedLlm([[json.dumps(VALID)]])
    service = _service(llm, db, prompts)

    await service.generate_full("i1", "r1")

    assert len(llm.calls) == 1


async def test_meta_turns_never_reach_the_summary_prompt(
    prompts: PromptLibrary, db: Database
) -> None:
    """P9: просьба о темпе была, но она не реплика кандидата и не улика в разборе."""
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


async def test_invalid_json_retries_with_error_hint(prompts: PromptLibrary, db: Database) -> None:
    await _seed_sessions(db)
    llm = ScriptedLlm([["not json at all"], [json.dumps(VALID)]])
    service = _service(llm, db, prompts)

    data = await service.generate_full("i1", "r1")
    assert data is not None
    retry_message = llm.calls[1][-1]["content"]
    assert "Your JSON was invalid" in retry_message


async def test_full_degrades_to_minimal_after_two_failures(
    prompts: PromptLibrary, db: Database
) -> None:
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


async def test_minimal_gives_up_quietly(prompts: PromptLibrary, db: Database) -> None:
    interviews, _ = await _seed_sessions(db)
    llm = ScriptedLlm([["junk"], ["junk"]])
    service = _service(llm, db, prompts)

    assert await service.generate_minimal("i1") is None
    row = await interviews.get("i1")
    assert row is not None and row.debrief_json is None  # nothing broken, nothing stored


# --- Сводка видит профиль кандидата (поставка summary-profile) ---------------
#
# Оба промпта сводки объявляли профиль своим входом и ставили балл `positioning`,
# а профиль не доходил: `PromptLibrary.system()` отдавал файл как есть, и не
# подставлял его никто. Тесты берут НАСТОЯЩИЕ промпты сводки — дефект жил в них и
# в загрузчике, а не в сервисе, — и синтетический профиль: личное в фикстуры не
# попадает. Проверяется собранное сообщение вызова, а не наличие файлов (L20).

REPO_PROMPTS = REPO_ROOT / "data" / "prompts"
SYNTHETIC_PROFILE = (
    "# Candidate Profile\n\nSam Example - builds AI pipelines for agencies.\n\n"
    "## Positioning rules\n\nBuilder of systems, never an SEO lead.\n"
)
NO_PROFILE = "(no candidate profile available)"  # заглушка PromptLibrary._profile


def _knowledge(tmp_path: Path, profile: str | None) -> Path:
    knowledge = tmp_path / "repo-knowledge"
    knowledge.mkdir()
    if profile is not None:
        (knowledge / "profile_condensed.md").write_text(profile, encoding="utf-8")
    return knowledge


async def _summary_call(pass_name: str, knowledge: Path, db: Database) -> list[dict[str, str]]:
    """Сообщения ПЕРВОГО вызова модели в полной или минимальной сводке."""
    await _seed_sessions(db)
    llm = ScriptedLlm([[json.dumps(VALID)]])
    service = _service(llm, db, PromptLibrary(REPO_PROMPTS, knowledge))
    if pass_name == "full":
        assert await service.generate_full("i1", "r1") is not None
    else:
        assert await service.generate_minimal("i1") is not None
    return [dict(message) for message in llm.calls[0]]


async def test_full_summary_sends_the_candidate_profile(tmp_path: Path, db: Database) -> None:
    """Репро: полная сводка на R1 ставила `positioning`, не видя профиля."""
    messages = await _summary_call("full", _knowledge(tmp_path, SYNTHETIC_PROFILE), db)

    assert messages[0]["role"] == "system"  # U1
    assert SYNTHETIC_PROFILE in messages[0]["content"], "профиль не дошёл до сводки"  # U1
    assert all(PROFILE_PLACEHOLDER not in m["content"] for m in messages)  # U1


async def test_minimal_summary_sends_the_candidate_profile(tmp_path: Path, db: Database) -> None:
    """Минимальная сводка на qwen: «INPUT: … + candidate profile only» — теперь правда."""
    messages = await _summary_call("minimal", _knowledge(tmp_path, SYNTHETIC_PROFILE), db)

    assert messages[0]["role"] == "system"  # U2
    assert SYNTHETIC_PROFILE in messages[0]["content"], "профиль не дошёл до сводки"  # U2
    assert all(PROFILE_PLACEHOLDER not in m["content"] for m in messages)  # U2


@pytest.mark.parametrize("pass_name", ["full", "minimal"])
async def test_summary_without_profile_file_says_so(
    pass_name: str, tmp_path: Path, db: Database
) -> None:
    """Нет файла профиля — заглушка, как у промптов интервью, а не голый плейсхолдер."""
    messages = await _summary_call(pass_name, _knowledge(tmp_path, None), db)

    assert NO_PROFILE in messages[0]["content"]  # U3
    assert all(PROFILE_PLACEHOLDER not in m["content"] for m in messages)  # U3


SUMMARY_PROMPTS = ("summary_system", "minimal_summary_system")


def test_positioning_is_judged_against_the_profile_section() -> None:
    """Позиционирование судится по разделу профиля, а не по роли в тексте промпта.

    До 2026-10-25 правило звучало «SEO lead vs AI automation engineer» — роль,
    зашитая в промпт, разошлась с профилем 2026-10-17. Теперь оба промпта ссылаются
    на раздел `Positioning rules`, и сторож держит связь: переименуй раздел в
    профиле — промпт сводки сослался бы на пустоту. Проверка описания: ловит
    разрыв ссылки, а не то, как модель профилем пользуется (это — живой прогон).
    """
    profile = (REPO_ROOT / "data" / "knowledge" / "profile_condensed.md").read_text(
        encoding="utf-8"
    )
    assert "## Positioning rules" in profile  # U4
    for name in SUMMARY_PROMPTS:
        text = (REPO_PROMPTS / f"{name}.txt").read_text(encoding="utf-8")
        assert PROFILE_PLACEHOLDER in text, f"{name}: профиль не объявлен входом"  # U4
        assert "Positioning rules" in text, f"{name}: позиционирование не по профилю"  # U4
        assert "AI automation engineer" not in text, f"{name}: зашитая роль вернулась"  # U4


#: doc 20: оценка «4 символа на токен» — та же, что у бюджета профиля
#: (`test_knowledge_profile.py`); по словам (0.75 слова на токен) выходит меньше,
#: а занижение здесь опаснее завышения.
CHARS_PER_TOKEN = 4
#: doc 20, Summary pass: полные транскрипты 15-минутной сессии.
INTERVIEW_TRANSCRIPT_TOKENS = 2500
REVIEW_TRANSCRIPT_TOKENS = 3000


def test_summary_prompts_with_profile_fit_the_context_budget() -> None:
    """Профиль, промпт, транскрипты и генерация укладываются в `num_ctx` (doc 20, L21).

    Превышение `num_ctx` не падает — Ollama молча обрезает промпт. Считается на
    настоящих профиле и промптах; транскрипты — по оценке doc 20 для 15-минутной
    сессии. Длинные сессии (30 и 45 минут) этим тестом не судятся: их расчёт и
    открытый вопрос — в doc 20.
    """
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    library = PromptLibrary(REPO_PROMPTS, REPO_ROOT / "data" / "knowledge")

    def prompt_tokens(name: str) -> float:
        return (len(library.system(name)) + len(SCHEMA_HINT)) / CHARS_PER_TOKEN

    full = prompt_tokens("summary_system") + INTERVIEW_TRANSCRIPT_TOKENS + REVIEW_TRANSCRIPT_TOKENS
    assert full + settings.summary_max_tokens <= settings.summary_num_ctx  # U5
    minimal = prompt_tokens("minimal_summary_system") + INTERVIEW_TRANSCRIPT_TOKENS
    assert minimal + settings.minimal_summary_max_tokens <= settings.ollama_num_ctx  # U5
