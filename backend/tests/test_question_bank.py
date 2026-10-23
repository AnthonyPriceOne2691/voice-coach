"""Банки вопросов и сборка пула сессии (spec S1, S2)."""

import random
from itertools import pairwise
from pathlib import Path

import pytest

from app.config import REPO_ROOT
from app.orchestrator.question_bank import (
    QuestionKind,
    load_bank,
    pick_session_pool,
)

QUESTIONS_DIR = REPO_ROOT / "data" / "questions"
TECHNICAL_PATH = QUESTIONS_DIR / "technical_project_walkthrough.yaml"
BEHAVIORAL_PATH = QUESTIONS_DIR / "behavioral.yaml"


def test_kind_comes_from_the_bank_file() -> None:
    technical = load_bank(TECHNICAL_PATH)
    behavioral = load_bank(BEHAVIORAL_PATH)

    assert len(technical) == 8
    assert len(behavioral) == 8
    # у технического банка ключа `kind:` нет вовсе — умолчание, а не забытое поле
    assert {q.kind for q in technical} == {QuestionKind.TECHNICAL}
    assert {q.kind for q in behavioral} == {QuestionKind.BEHAVIORAL}


def test_empty_bank_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty.yaml"
    empty.write_text("mode: x\nquestions: []\n")
    with pytest.raises(ValueError, match="empty question bank"):
        load_bank(empty)


def test_unknown_kind_is_a_loud_failure(tmp_path: Path) -> None:
    """Опечатка в классе не должна молча стать `technical`."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("mode: x\nkind: soft\nquestions:\n  - id: a\n    seed: 'S?'\n")
    with pytest.raises(ValueError):
        load_bank(bad)


@pytest.mark.parametrize("seed", [1, 42, 7, 2026])
def test_session_pool_is_half_behavioral_and_alternates(seed: int) -> None:
    """S1 + S2: три и три, строго через один, открывает технический вопрос."""
    technical = load_bank(TECHNICAL_PATH)
    behavioral = load_bank(BEHAVIORAL_PATH)

    pool = pick_session_pool(technical, behavioral, count=6, rng=random.Random(seed))

    assert len(pool) == 6
    assert len({q.id for q in pool}) == 6  # без повторов
    assert pool[0].id == "project_overview"  # marked first: true
    kinds = [q.kind for q in pool]
    assert kinds.count(QuestionKind.TECHNICAL) == 3  # S1
    assert kinds.count(QuestionKind.BEHAVIORAL) == 3  # S1
    assert all(a is not b for a, b in pairwise(kinds)), kinds  # S2


def test_pool_survives_a_short_behavioral_bank() -> None:
    """Банк меньше нужного не роняет сессию — просто даёт меньше своих слотов."""
    technical = load_bank(TECHNICAL_PATH)
    behavioral = load_bank(BEHAVIORAL_PATH)[:1]

    pool = pick_session_pool(technical, behavioral, count=6, rng=random.Random(1))

    assert [q.kind for q in pool][:3] == [
        QuestionKind.TECHNICAL,
        QuestionKind.BEHAVIORAL,
        QuestionKind.TECHNICAL,
    ]
    assert len(pool) == 4  # один behavioral исчерпан, чередование обрывается честно
