"""Contract Enforcer unit tests — hard rules from doc 13 (coverage gate: 95%)."""

from pathlib import Path

import pytest

from app.contracts.enforcer import ContractEnforcer, TurnContext
from app.contracts.spec import ContractError, load_contract
from app.orchestrator.question_bank import load_bank

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "data" / "contracts"
QUESTIONS_DIR = Path(__file__).resolve().parents[2] / "data" / "questions"


@pytest.fixture(scope="module")
def interview() -> ContractEnforcer:
    return ContractEnforcer(load_contract(CONTRACTS_DIR / "interview.contract.yaml"))


@pytest.fixture(scope="module")
def review() -> ContractEnforcer:
    return ContractEnforcer(load_contract(CONTRACTS_DIR / "review.contract.yaml"))


def test_real_contract_files_load(interview: ContractEnforcer, review: ContractEnforcer) -> None:
    assert interview.spec.mode == "interview"
    assert interview.spec.enforcement == "per_sentence"
    assert interview.spec.max_retries == 1
    assert "i'd score" in interview.spec.forbidden_patterns  # оценки остались
    assert "great answer" not in interview.spec.forbidden_patterns  # похвала разрешена 2026-08-12
    assert "got it" in interview.spec.ack_whitelist
    assert review.spec.mode == "review"


def test_unknown_check_rejected_at_load(tmp_path: Path) -> None:
    bad = tmp_path / "bad.contract.yaml"
    bad.write_text("mode: x\ninvariants:\n  hard:\n    - id: r1\n      check: run_shell\n")
    with pytest.raises(ContractError, match="unknown check"):
        load_contract(bad)


def test_missing_check_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.contract.yaml"
    bad.write_text("mode: x\ninvariants:\n  hard:\n    - id: r1\n")
    with pytest.raises(ContractError, match="no check"):
        load_contract(bad)


# --- Mode 1 hard rules ---


def test_cyrillic_rejected(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    violation = turn.feed("Отлично, расскажите про проект?")
    assert violation is not None and violation.check == "no_cyrillic"
    assert violation.severity == "hard"
    assert turn.sentences == []  # rejected sentence is never spoken


def test_scoring_pattern_rejected_case_insensitive(interview: ContractEnforcer) -> None:
    """Регистр не спасает оценку. Похвала при этом проходит — граница 2026-08-12."""
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    violation = turn.feed("I'D SCORE that at four.")
    assert violation is not None and violation.check == "forbid_patterns"
    assert violation.matched == "i'd score"  # G3
    assert (
        interview.start_turn(TurnContext(state="CORE_QUEST")).feed(
            "Great ANSWER, that was impressive!"
        )
        is None
    )


def test_max_three_sentences(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    assert turn.feed("One?") is None
    assert turn.feed("Two.") is None
    assert turn.feed("Three.") is None
    violation = turn.feed("Four.")
    assert violation is not None and violation.check == "max_sentences"
    assert violation.sentence_index == 3


def test_max_chars_cumulative(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    assert turn.feed("x" * 149 + "?") is None  # cumulative 151 (incl. separator)
    assert turn.feed("y" * 199 + ".") is None  # cumulative 352
    violation = turn.feed("z" * 60 + ".")  # 352 + 61 > 400
    assert violation is not None and violation.check == "max_chars_cumulative"
    assert violation.severity == "hard"


def test_question_or_ack_passes_with_question(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="FOLLOW_UP"))
    turn.feed("Help me understand the trade-off there?")
    assert turn.finish() is None


def test_question_or_ack_passes_with_short_ack(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    turn.feed("Got it, that makes sense.")
    assert turn.finish() is None


def test_statement_without_question_fails(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    turn.feed("Your architecture uses queues and that is an interesting approach to the problem.")
    violation = turn.finish()
    assert violation is not None and violation.check == "question_or_ack"
    assert violation.sentence_index == -1


def test_question_or_ack_skipped_outside_states(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="WRAP_UP"))
    turn.feed("That's all from my side, thanks for your time today.")
    assert turn.finish() is None


def test_long_nonwhitelisted_ack_fails(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    turn.feed("Interesting point about the queues indeed.")
    violation = turn.finish()
    assert violation is not None and violation.check == "question_or_ack"


# --- Mode 2 hard rules ---


def test_review_question_ref_out_of_range(review: ContractEnforcer) -> None:
    turn = review.start_turn(TurnContext(state="WALK_QUESTIONS", question_count=5))
    assert turn.feed("Q3 was strong because you led with the metric.") is None
    violation = turn.feed("Now Q9 was weaker.")
    assert violation is not None and violation.check == "quoted_question_in_transcript"
    assert violation.matched == "Q9"


def test_review_allows_five_sentences(review: ContractEnforcer) -> None:
    turn = review.start_turn(TurnContext(state="WALK_QUESTIONS", question_count=3))
    for i in range(5):
        assert turn.feed(f"Sentence number {i} about Q1.") is None
    assert turn.feed("Sixth sentence.") is not None


# --- events ---


# --- Talk (D3a): без оценок, по-английски, коротко ---


@pytest.fixture(scope="module")
def talk() -> ContractEnforcer:
    return ContractEnforcer(load_contract(CONTRACTS_DIR / "talk.contract.yaml"))


@pytest.mark.parametrize(
    "graded",
    [
        "I'd rate your English seven out of ten.",
        "Honestly, your English is a solid B1 level.",
        "I'd score this conversation a four.",
    ],
)
def test_talk_never_speaks_a_grade(talk: ContractEnforcer, graded: str) -> None:
    """T6: оценку держит енфорсер, а не согласие модели (L24)."""
    violation = talk.start_turn(TurnContext(state="CHAT")).feed(graded)
    assert violation is not None and violation.rule_id == "I3-H2_no_grades"


def test_talk_lets_praise_and_plain_talk_through(talk: ContractEnforcer) -> None:
    """T6, красная сторона: похвала — не оценка, а «score» в рассказе о матче — не балл."""
    turn = talk.start_turn(TurnContext(state="CHAT"))
    for sentence in (
        "Your English sounds really natural today!",
        "What was the final score of the match?",
        "I love that place too.",
        "What did you have for lunch?",
    ):
        assert turn.feed(sentence) is None
    violation = turn.feed("One more thought.")
    assert violation is not None and violation.check == "max_sentences"  # не длиннее 4
    assert talk.start_turn(TurnContext(state="CHAT")).feed("Привет!") is not None


def test_violation_event_schema(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    violation = turn.feed("I'd score that a four.")
    assert violation is not None
    event = interview.violation_event(
        violation, turn_index=7, state="CORE_QUEST", recovery="regenerate", recovered=True
    )
    assert event == {
        "turn_index": 7,
        "state": "CORE_QUEST",
        "constraint_id": "I1-H3_no_scoring",
        "severity": "hard",
        "sentence_index": 0,
        "matched": "i'd score",
        "recovery": "regenerate",
        "recovered": True,
    }


def test_spoken_text_joins_accepted_sentences(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    turn.feed("Got it.")
    turn.feed("Why separate queues?")
    assert turn.spoken_text() == "Got it. Why separate queues?"


def test_behavioral_seeds_are_speakable(interview: ContractEnforcer) -> None:
    """Вопрос, который енфорсер режет, пользователь НЕ УСЛЫШИТ (L24).

    Seed'ы банка используются дословно как запасная реплика при нарушении
    контракта, поэтому обязаны проходить его сами.
    """
    bank = load_bank(QUESTIONS_DIR / "behavioral.yaml")
    assert len(bank) == 8

    for question in bank:
        turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
        assert turn.feed(question.seed) is None, f"{question.id} режется контрактом"

    # запасная реплика behavioral follow-up — оттуда же
    turn = interview.start_turn(TurnContext(state="FOLLOW_UP"))
    assert turn.feed("What did you do next, and how did it turn out?") is None

    # красная сторона (L25): будь в вопросе оценка, сторож обязан покраснеть
    red = interview.start_turn(TurnContext(state="CORE_QUEST"))
    assert red.feed("Tell me about a time you failed. I'd rate that answer 3 out of 5.") is not None


# --- Сторожа summary-контракта (V8) --------------------------------------
#
# `summary.contract.yaml` не исполняется енфорсером (он про голос) — его правила
# живут кодом в `app/summary/`. Значит связь «объявлено ↔ реализовано» держится
# на честном слове, и именно в этой щели поселился `выразительный陳述`.

SUMMARY_CONTRACT = CONTRACTS_DIR / "summary.contract.yaml"
SUMMARY_CODE = Path(__file__).resolve().parents[1] / "app" / "summary"


def _summary_hard_invariants() -> list[dict[str, object]]:
    import yaml

    data = yaml.safe_load(SUMMARY_CONTRACT.read_text(encoding="utf-8"))
    invariants = data["invariants"]["hard"]
    assert isinstance(invariants, list) and invariants
    return [dict(item) for item in invariants]


def test_every_summary_invariant_leaves_a_mark_in_code() -> None:
    """Объявленный инвариант обязан быть реализован — иначе контракт врёт о полноте."""
    source = "\n".join(p.read_text(encoding="utf-8") for p in sorted(SUMMARY_CODE.glob("*.py")))
    for invariant in _summary_hard_invariants():
        marker = str(invariant["id"]).split("_", 1)[0]  # S-H6 из S-H6_translation_is_russian
        assert marker in source, (
            f"инвариант {invariant['id']} объявлен в summary.contract.yaml, но маркера "
            f"{marker} нет ни в одном файле app/summary/ — правило существует только на бумаге"
        )


def test_excluded_field_is_covered_by_another_invariant() -> None:
    """Исключение из правила обязано быть ЗАМЕНЕНО правилом, а не оставлять поле голым.

    Это сторож ровно на найденный дефект: `vocabulary.translation_ru` исключили из
    `S-H2_en_body` («только английский») и не покрыли ничем — поле оказалось между
    двумя правилами, и туда попали иероглифы `deepseek-r1`. Проверка не на текст
    правила, а на СВЯЗЬ: у каждого исключённого поля есть другой инвариант, который
    его называет.
    """
    invariants = _summary_hard_invariants()
    for invariant in invariants:
        excluded = invariant.get("exclude_fields") or []
        assert isinstance(excluded, list)  # V8
        for field in excluded:
            covering = [
                other["id"]
                for other in invariants
                if other["id"] != invariant["id"] and other.get("field") == field
            ]
            assert covering, (  # V8: исключение обязано быть заменено правилом
                f"поле {field} исключено из {invariant['id']} и не покрыто ничем: "
                "исключение из одного правила молча означает «может быть чем угодно». "
                "Заведи инвариант с `field: <это поле>` — так в банк слов попало "
                "`выразительный陳述`"
            )
