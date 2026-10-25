"""Поправки речи в разговоре — только от кода (D3a.2, C16): правило контракта разговора.

Енфорсер режет поправку и урок грамматики ДО озвучки, поэтому Генри не поправляет сам,
даже если модель согласится (L24). Проверка — с обеих сторон: беседа об английском и
причины подсказок («past tense») идут через тот же контракт и резаться не должны (L25).
"""

from pathlib import Path

import pytest

from app.config import REPO_ROOT
from app.contracts.enforcer import ContractEnforcer, TurnContext
from app.contracts.spec import load_contract

NO_CORRECTIONS = "I3-H4_no_corrections"
NO_GRADES = "I3-H2_no_grades"


@pytest.fixture(scope="module")
def talk() -> ContractEnforcer:
    return ContractEnforcer(load_contract(REPO_ROOT / "data" / "contracts" / "talk.contract.yaml"))


def _rule(talk: ContractEnforcer, sentence: str) -> str | None:
    violation = talk.start_turn(TurnContext(state="CHAT")).feed(sentence)
    return None if violation is None else violation.rule_id


@pytest.mark.parametrize(
    "correction",
    [
        "You could also say “I went to the gym yesterday”.",
        "A more natural way to say it is: the food was delicious.",
        "Quick correction: it's “met”, not “meet”.",
        "“Went” is the past tense of “go”.",
        "Instead of saying “I go”, try saying “I went”.",
        "Here's a little grammar tip for you.",
    ],
)
def test_henry_correcting_english_is_cut_before_speech(
    talk: ContractEnforcer, correction: str
) -> None:
    """C16: поправку и урок грамматики режет енфорсер до озвучки — правило о поправках."""
    assert _rule(talk, correction) == NO_CORRECTIONS


@pytest.mark.parametrize(
    "sentence",
    [
        "Grammar can feel tricky at first — which tense is the hardest for you?",
        "You could say that again!",
        "Instead of going out, we stayed home and watched a film.",
        "Your English sounds really natural today!",
        "past tense",
        "more vivid",
        "word order",
    ],
)
def test_talk_about_english_and_tip_reasons_pass(talk: ContractEnforcer, sentence: str) -> None:
    """C16, зелёная сторона: беседа об английском и причины подсказок — не поправка."""
    assert _rule(talk, sentence) is None


def test_grades_are_still_cut_by_their_own_rule(talk: ContractEnforcer) -> None:
    """C16: у правила о поправках свой список, и оценки по-прежнему режет правило об оценках."""
    assert _rule(talk, "I'd rate your English seven out of ten.") == NO_GRADES


def test_each_forbid_patterns_rule_judges_its_own_list(tmp_path: Path) -> None:
    """C16: второе правило `forbid_patterns` в контракте судит СВОЙ список, а не первого.

    До починки загрузчик читал один `patterns_file` на контракт, и правило о поправках
    проверяло бы фразы оценок.
    """
    (tmp_path / "first.txt").write_text("alpha\n", encoding="utf-8")
    (tmp_path / "second.txt").write_text("# комментарий\nbeta\n", encoding="utf-8")
    (tmp_path / "pair.contract.yaml").write_text(
        "mode: pair\ninvariants:\n  hard:\n"
        "    - id: first\n      check: forbid_patterns\n      patterns_file: first.txt\n"
        "    - id: second\n      check: forbid_patterns\n      patterns_file: second.txt\n",
        encoding="utf-8",
    )
    pair = ContractEnforcer(load_contract(tmp_path / "pair.contract.yaml"))
    hits = {word: pair.start_turn(TurnContext()).feed(f"Say {word}.") for word in ("alpha", "beta")}
    assert {word: (v.rule_id, v.matched) for word, v in hits.items() if v} == {
        "alpha": ("first", "alpha"),
        "beta": ("second", "beta"),
    }
    assert pair.spec.forbidden_patterns == ["alpha", "beta"]
