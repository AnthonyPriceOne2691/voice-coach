"""Pace policy — deterministic recognition and clamping (spec P1–P4)."""

import pytest

from app.orchestrator.pace import (
    PACE_FASTEST,
    PACE_SLOWEST,
    PaceRequest,
    apply,
    detect,
    in_range,
)


@pytest.mark.parametrize(
    ("utterance", "expected"),
    [
        # P1 — просьба замедлить
        ("Could you speak a bit slower, please?", PaceRequest.SLOWER),
        ("Slower, please.", PaceRequest.SLOWER),
        ("You're going too fast.", PaceRequest.SLOWER),
        ("Slow down a little.", PaceRequest.SLOWER),
        ("Can you speak more slowly?", PaceRequest.SLOWER),
        # P2 — просьба ускорить
        ("That's too slow, speak faster.", PaceRequest.FASTER),
        ("Speak faster please.", PaceRequest.FASTER),
        ("You can speed up.", PaceRequest.FASTER),
    ],
)
def test_short_pace_requests_are_recognised(utterance: str, expected: PaceRequest) -> None:
    assert detect(utterance) is expected


def test_too_slow_asks_to_speed_up_not_to_slow_down() -> None:
    """Порядок шаблонов — часть правила: «too slow» содержит «slow»."""
    assert detect("That's too slow.") is PaceRequest.FASTER


@pytest.mark.parametrize(
    "utterance",
    [
        # P4 — содержательный ответ, в котором упомянута скорость
        "We had to speed up the ingest pipeline, the old version was too slow for "
        "our SLA, so I rewrote the batching layer.",
        "The slower path was the database, not the API, and that took a while to find.",
        # обычный ответ без единого слова о темпе
        "I built an inbound pipeline for our team.",
        "",
    ],
)
def test_normal_answers_are_not_pace_requests(utterance: str) -> None:
    assert detect(utterance) is None


def test_long_utterance_is_never_a_request_even_if_it_says_slower() -> None:
    """Длина — единственный разделитель P1 и P4, и он проверяется отдельно."""
    words = " ".join(["word"] * 12)
    assert detect(f"speak slower {words}") is None


def test_the_interview_detector_would_take_a_story_for_a_request() -> None:
    """Почему разговору нужна своя таблица: в интервью короткий рассказ — редкость."""
    assert detect("It was a slow day.") is PaceRequest.SLOWER


@pytest.mark.parametrize(
    ("utterance", "expected"),
    [
        # T4 — слово о скорости в рассказе: в разговоре короткая фраза — норма (L33)
        ("It was a slow day.", None),
        ("Trains are faster than buses here.", None),
        ("The internet was so slow yesterday.", None),
        ("I had to slow down at work this week.", None),
        # T5 — просьба узнаётся по форме: обращение, глагол речи, реплика целиком
        ("Could you speak a bit slower?", PaceRequest.SLOWER),
        ("Slower, please.", PaceRequest.SLOWER),
        ("Slow down a little.", PaceRequest.SLOWER),
        ("You're speaking too fast.", PaceRequest.SLOWER),
        ("Can you speak more slowly?", PaceRequest.SLOWER),
        ("You can talk faster.", PaceRequest.FASTER),
        ("Could you speed up a bit?", PaceRequest.FASTER),
        ("You're a bit too slow.", PaceRequest.FASTER),
    ],
)
def test_in_talk_only_the_shape_of_a_request_changes_the_pace(
    utterance: str, expected: PaceRequest | None
) -> None:
    assert detect(utterance, casual=True) is expected


def test_one_request_moves_exactly_one_step() -> None:
    new_scale, at_limit = apply(1.15, PaceRequest.SLOWER)
    assert (new_scale, at_limit) == (1.30, False)  # P1
    new_scale, at_limit = apply(1.15, PaceRequest.FASTER)
    assert (new_scale, at_limit) == (1.00, False)  # P2


def test_clamped_at_both_limits_and_the_limit_is_reported() -> None:
    """P3: на границе значение не меняется, и вызывающий обязан это УЗНАТЬ."""
    assert apply(PACE_SLOWEST, PaceRequest.SLOWER) == (PACE_SLOWEST, True)
    assert apply(PACE_FASTEST, PaceRequest.FASTER) == (PACE_FASTEST, True)
    # один шаг не доходит до границы — это ещё не предел
    assert apply(PACE_SLOWEST - 0.15, PaceRequest.SLOWER) == (PACE_SLOWEST, False)


def test_repeated_requests_never_leave_the_corridor() -> None:
    scale = 1.15
    for _ in range(10):
        scale, _ = apply(scale, PaceRequest.SLOWER)
    assert scale == PACE_SLOWEST
    for _ in range(10):
        scale, _ = apply(scale, PaceRequest.FASTER)
    assert scale == PACE_FASTEST


def test_in_range_guards_the_corridor() -> None:
    assert in_range(1.15) and in_range(PACE_FASTEST) and in_range(PACE_SLOWEST)
    assert not in_range(2.5)
    assert not in_range(0.5)
