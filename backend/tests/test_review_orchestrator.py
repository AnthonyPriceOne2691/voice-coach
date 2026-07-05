"""Review orchestrator (doc 11): grounded walk, USER_Q handling, coverage of all questions."""

import pytest

from app.orchestrator.review import (
    ReviewOrchestrator,
    ReviewPhase,
    build_segments,
    render_segments,
)

TURNS = [
    {"role": "agent", "text": "Walk me through a tool.", "question_id": "q1", "state": "INTRO"},
    {"role": "user", "text": "I built a CRM.", "question_id": "q1", "state": "INTRO"},
    {"role": "agent", "text": "Why queues?", "question_id": "q1", "state": "FOLLOW_UP"},
    {"role": "user", "text": "For isolation.", "question_id": "q1", "state": "FOLLOW_UP"},
    {"role": "agent", "text": "What was the impact?", "question_id": "q2", "state": "CORE_QUEST"},
    {"role": "user", "text": "5 to 1 team.", "question_id": "q2", "state": "CORE_QUEST"},
    {"role": "agent", "text": "Any questions?", "question_id": None, "state": "WRAP_UP"},
    {"role": "user", "text": "No thanks.", "question_id": None, "state": "WRAP_UP"},
]


def test_build_segments_groups_by_question() -> None:
    segments = build_segments(TURNS)
    assert [s.question_id for s in segments] == ["q1", "q2"]
    assert segments[0].question_text == "Walk me through a tool."
    assert segments[0].answer_text == "I built a CRM. / For isolation."  # follow-up answers merged
    rendered = render_segments(segments)
    assert "Q1: Walk me through a tool." in rendered
    assert "A2: 5 to 1 team." in rendered


def test_unanswered_questions_are_skipped() -> None:
    turns = [
        {"role": "agent", "text": "Q?", "question_id": "q1", "state": "CORE_QUEST"},
        {"role": "user", "text": "answer", "question_id": "q1", "state": "CORE_QUEST"},
        {"role": "agent", "text": "Another?", "question_id": "q2", "state": "CORE_QUEST"},
    ]
    assert [s.question_id for s in build_segments(turns)] == ["q1"]


def test_empty_segments_rejected() -> None:
    with pytest.raises(ValueError, match="no answered questions"):
        ReviewOrchestrator([])


def test_walk_advances_on_statement_and_holds_on_question() -> None:
    orch = ReviewOrchestrator(build_segments(TURNS))
    intro = orch.intro_plan()
    assert intro.state == ReviewPhase.INTRO and intro.question_number == 1

    plan = orch.on_user("What about my queue answer?")  # USER_Q -> stay on Q1
    assert plan.state == ReviewPhase.WALK_QUESTIONS
    assert plan.question_number == 1
    assert "grounded strictly" in plan.instruction

    plan = orch.on_user("okay makes sense")  # ack -> advance to Q2
    assert plan.question_number == 2
    assert orch.questions_reviewed == 1

    plan = orch.on_user("got it")  # last question covered -> WRAP_UP
    assert plan.state == ReviewPhase.WRAP_UP
    assert orch.questions_reviewed == 2  # G2-H3: all questions covered before wrap-up

    plan = orch.on_user("no, thanks")
    assert plan.state == ReviewPhase.END
    assert orch.finished
