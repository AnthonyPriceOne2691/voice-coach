"""Interview orchestrator: state x event -> next state (doc 04; coverage gate 90%)."""

import random
from pathlib import Path

import pytest

from app.orchestrator.interview import InterviewOrchestrator, Phase
from app.orchestrator.question_bank import Question, load_bank, pick_session_pool

BANK_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "questions"
    / "technical_project_walkthrough.yaml"
)

LONG_WITH_METRIC = " ".join(["word"] * 50) + " reduced from 5 to 1"
LONG_NO_METRIC = " ".join(["word"] * 50)
SHORT = "we used queues"


def make_pool(n: int = 3) -> list[Question]:
    return [Question(id=f"q{i}", theme=f"Theme {i}", seed=f"Seed question {i}?") for i in range(n)]


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_bank_loads_and_pool_starts_with_first() -> None:
    bank = load_bank(BANK_PATH)
    assert len(bank) == 8
    pool = pick_session_pool(bank, count=6, rng=random.Random(42))
    assert pool[0].id == "project_overview"  # marked first: true
    assert len(pool) == 6
    assert len({q.id for q in pool}) == 6


def test_empty_bank_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty.yaml"
    empty.write_text("mode: x\nquestions: []\n")
    with pytest.raises(ValueError, match="empty question bank"):
        load_bank(empty)


def test_intro_plan_uses_first_question() -> None:
    orch = InterviewOrchestrator(make_pool(), clock=FakeClock())
    plan = orch.intro_plan()
    assert plan.state == Phase.INTRO
    assert plan.question_id == "q0"


def test_first_follow_up_always_happens() -> None:
    orch = InterviewOrchestrator(make_pool(), clock=FakeClock())
    plan = orch.on_user_answer(LONG_WITH_METRIC)  # great answer — still 1 follow-up
    assert plan.state == Phase.FOLLOW_UP
    assert plan.question_id == "q0"
    assert plan.follow_up_count == 1


def test_second_follow_up_only_for_weak_answers() -> None:
    # strong second answer -> move on
    orch = InterviewOrchestrator(make_pool(), clock=FakeClock())
    orch.on_user_answer(SHORT)
    plan = orch.on_user_answer(LONG_WITH_METRIC)
    assert plan.state == Phase.CORE_QUEST
    assert plan.question_id == "q1"

    # short second answer -> second follow-up
    orch = InterviewOrchestrator(make_pool(), clock=FakeClock())
    orch.on_user_answer(SHORT)
    plan = orch.on_user_answer(SHORT)
    assert plan.state == Phase.FOLLOW_UP
    assert plan.follow_up_count == 2

    # long but metric-less -> second follow-up (probe for impact)
    orch = InterviewOrchestrator(make_pool(), clock=FakeClock())
    orch.on_user_answer(SHORT)
    plan = orch.on_user_answer(LONG_NO_METRIC)
    assert plan.state == Phase.FOLLOW_UP


def test_max_two_follow_ups_then_next_question() -> None:
    orch = InterviewOrchestrator(make_pool(), clock=FakeClock())
    orch.on_user_answer(SHORT)
    orch.on_user_answer(SHORT)
    plan = orch.on_user_answer(SHORT)  # third weak answer — but max 2 reached
    assert plan.state == Phase.CORE_QUEST
    assert plan.question_id == "q1"
    assert plan.follow_up_count == 0  # reset for the new question


def test_follow_ups_disabled_late_in_session() -> None:
    clock = FakeClock()
    orch = InterviewOrchestrator(make_pool(), duration_min=15, clock=clock)
    clock.now = 13 * 60  # 87% elapsed
    plan = orch.on_user_answer(SHORT)
    assert plan.state == Phase.CORE_QUEST  # no follow-up despite weak answer


def test_hard_stop_forces_wrap_up() -> None:
    clock = FakeClock()
    orch = InterviewOrchestrator(make_pool(10), duration_min=15, clock=clock)
    clock.now = 16 * 60 + 1
    plan = orch.on_user_answer(LONG_WITH_METRIC)
    assert plan.state == Phase.WRAP_UP
    assert "questions for us" in plan.seed


def test_pool_exhaustion_leads_to_wrap_up_and_debrief() -> None:
    clock = FakeClock()
    orch = InterviewOrchestrator(make_pool(2), duration_min=15, clock=clock)
    clock.now = 13 * 60  # follow-ups off to speed through
    assert orch.on_user_answer(LONG_WITH_METRIC).question_id == "q1"
    plan = orch.on_user_answer(LONG_WITH_METRIC)  # last question answered
    assert plan.state == Phase.WRAP_UP
    assert not orch.finished
    plan = orch.on_user_answer("no questions, thanks")
    assert plan.state == Phase.DEBRIEF
    assert orch.finished


def test_time_remaining_and_snapshot() -> None:
    clock = FakeClock()
    orch = InterviewOrchestrator(make_pool(), duration_min=15, clock=clock)
    clock.now = 5 * 60
    plan = orch.on_user_answer(SHORT)
    assert plan.time_remaining_min == 10
    snap = orch.snapshot()
    assert snap["duration_sec"] == 300
    assert snap["follow_ups"] == 1


def test_user_message_wrapper_format() -> None:
    orch = InterviewOrchestrator(make_pool(), clock=FakeClock())
    plan = orch.on_user_answer(SHORT)
    message = orch.build_user_message(plan, "my answer")
    assert "[STATE=FOLLOW_UP]" in message
    assert "[QUESTION_ID=q0]" in message
    assert "[FOLLOW_UP_COUNT=1]" in message
    assert message.endswith("Candidate answer:\nmy answer")


def test_instructions_mention_seed_for_core_quest() -> None:
    clock = FakeClock()
    orch = InterviewOrchestrator(make_pool(), clock=clock)
    clock.now = 13 * 60
    plan = orch.on_user_answer(SHORT)
    assert plan.state == Phase.CORE_QUEST
    assert "Seed question 1?" in plan.instruction
    assert plan.seed == "Seed question 1?"


def test_empty_pool_rejected() -> None:
    with pytest.raises(ValueError):
        InterviewOrchestrator([], clock=FakeClock())
