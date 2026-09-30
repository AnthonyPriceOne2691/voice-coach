"""Просьба к самому Генри против ответа: где проходит граница (класс «мета-ход», как темп)."""

import pytest

from app.orchestrator.meta_request import MetaRequest, detect, last_question


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("How would you rate that answer, out of 10?", MetaRequest.SCORE),
        ("Could you score my answer?", MetaRequest.SCORE),
        ("What's my score so far?", MetaRequest.SCORE),
        ("How did I do?", MetaRequest.SCORE),
        ("Out of ten?", MetaRequest.SCORE),
        ("Can we switch to Russian for a minute?", MetaRequest.LANGUAGE),
        ("Let's speak in Russian.", MetaRequest.LANGUAGE),
        ("Could I answer in my language?", MetaRequest.LANGUAGE),
        (
            "Where should I start: the business problem or the architecture?",
            MetaRequest.WHERE_TO_START,
        ),
        ("How should I structure this?", MetaRequest.WHERE_TO_START),
    ],
)
def test_requests_to_henry_are_caught(text: str, expected: MetaRequest) -> None:
    assert detect(text) is expected


@pytest.mark.parametrize(
    "text",
    [
        # Короткие ОТВЕТЫ с теми же словами — ради них у каждого шаблона форма просьбы.
        "Our reply rate was fifteen percent, and that was good.",
        "I talk to Russian clients daily.",
        "We had 7 out of 10 campaigns succeed last quarter.",
        "How did I do the migration? We split it into two steps.",
        "We started with the architecture.",
        # Темп — не эта политика: его ловит pace, и раньше.
        "Could you speak slower?",
    ],
)
def test_answers_stay_answers(text: str) -> None:
    assert detect(text) is None


def test_a_long_answer_is_never_a_request() -> None:
    """Порог длины: содержательный ответ не превращается в мета-ход целиком."""
    long_answer = (
        "Before I answer how you would rate it, let me say the outreach platform "
        "cut a team of five to one operator in production."
    )
    assert detect(long_answer) is None


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "That sounds impressive. Can you tell me about a specific trade-off?",
            "Can you tell me about a specific trade-off?",
        ),
        (
            "Hi, I'm Henry. Walk me through an internal tool you built end-to-end.",
            "Walk me through an internal tool you built end-to-end.",
        ),
        ("", ""),
    ],
)
def test_last_question_skips_the_acknowledgement(line: str, expected: str) -> None:
    assert last_question(line) == expected
