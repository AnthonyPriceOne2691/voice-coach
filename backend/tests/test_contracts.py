"""Contract Enforcer unit tests — hard rules from doc 13 (coverage gate: 95%)."""

from pathlib import Path

import pytest

from app.contracts.enforcer import ContractEnforcer, TurnContext
from app.contracts.spec import ContractError, load_contract

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "data" / "contracts"


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
    assert "great answer" in interview.spec.forbidden_patterns
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


def test_coaching_pattern_rejected_case_insensitive(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    violation = turn.feed("Great ANSWER, that was impressive!")
    assert violation is not None and violation.check == "forbid_patterns"
    assert violation.matched == "great answer"


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


def test_violation_event_schema(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    violation = turn.feed("Great answer!")
    assert violation is not None
    event = interview.violation_event(
        violation, turn_index=7, state="CORE_QUEST", recovery="regenerate", recovered=True
    )
    assert event == {
        "turn_index": 7,
        "state": "CORE_QUEST",
        "constraint_id": "I1-H2_no_coaching",
        "severity": "hard",
        "sentence_index": 0,
        "matched": "great answer",
        "recovery": "regenerate",
        "recovered": True,
    }


def test_spoken_text_joins_accepted_sentences(interview: ContractEnforcer) -> None:
    turn = interview.start_turn(TurnContext(state="CORE_QUEST"))
    turn.feed("Got it.")
    turn.feed("Why separate queues?")
    assert turn.spoken_text() == "Got it. Why separate queues?"
