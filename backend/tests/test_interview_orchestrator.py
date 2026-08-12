"""Interview orchestrator: state x event -> next state (doc 04; coverage gate 90%)."""

import random
from pathlib import Path

import pytest

from app.orchestrator.interview import InterviewOrchestrator, Phase
from app.orchestrator.question_bank import (
    Question,
    QuestionKind,
    load_bank,
    pick_session_pool,
)

QUESTIONS_DIR = Path(__file__).resolve().parents[2] / "data" / "questions"
TECHNICAL_BANK = QUESTIONS_DIR / "technical_project_walkthrough.yaml"
BEHAVIORAL_BANK = QUESTIONS_DIR / "behavioral.yaml"

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


# Загрузка банков и сборка пула переехали в test_question_bank.py вместе с
# чередованием классов (2026-08-13): здесь остаётся только машина состояний.


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


# -- политика follow-up зависит от КЛАССА вопроса (spec S3-S6) ------------------

GENERIC_ANSWER = (
    "I always try to communicate clearly and keep everyone in the loop, because "
    "in my experience most problems in a team come from people not knowing what "
    "the others are doing, so I make sure to write things down and share context "
    "with everybody involved as early as possible in the process"
)

STORY_ANSWER = (
    "Our PM wanted to ship without the review queue. I showed him two false "
    "positives from the week before, and we agreed to keep it behind a flag. "
    "In the end we shipped a week later with the queue on."
)


def behavioral_pool(n: int = 3) -> list[Question]:
    return [
        Question(
            id=f"b{i}",
            theme=f"Theme {i}",
            seed=f"Tell me about a time {i}?",
            kind=QuestionKind.BEHAVIORAL,
        )
        for i in range(n)
    ]


def test_generic_behavioral_answer_gets_a_second_follow_up() -> None:
    """S3: длинный, но без эпизода и исхода — это ещё не история."""
    assert len(GENERIC_ANSWER.split()) >= 40, "иначе сработало бы правило длины, а не класса"
    orch = InterviewOrchestrator(behavioral_pool(), clock=FakeClock())
    orch.on_user_answer(SHORT)

    plan = orch.on_user_answer(GENERIC_ANSWER)

    assert plan.state == Phase.FOLLOW_UP
    assert plan.follow_up_count == 2


def test_behavioral_story_with_an_ending_moves_on() -> None:
    """S4: конкретный эпизод и исход — допрашивать больше не о чем."""
    assert len(STORY_ANSWER.split()) >= 40
    orch = InterviewOrchestrator(behavioral_pool(), clock=FakeClock())
    orch.on_user_answer(SHORT)

    plan = orch.on_user_answer(STORY_ANSWER)

    assert plan.state == Phase.CORE_QUEST
    assert plan.question_id == "b1"


def test_technical_rule_did_not_move() -> None:
    """S5: тот же текст на ТЕХНИЧЕСКОМ вопросе — цифр в нём нет, значит допрос."""
    assert not any(ch.isdigit() for ch in STORY_ANSWER)
    orch = InterviewOrchestrator(make_pool(), clock=FakeClock())
    orch.on_user_answer(SHORT)

    plan = orch.on_user_answer(STORY_ANSWER)

    assert plan.state == Phase.FOLLOW_UP


def test_behavioral_follow_up_asks_about_actions_not_trade_offs() -> None:
    """S6: инструкция для рассказа о людях — своя."""
    orch = InterviewOrchestrator(behavioral_pool(), clock=FakeClock())

    plan = orch.on_user_answer(SHORT)

    assert plan.state == Phase.FOLLOW_UP
    lowered = plan.instruction.lower()
    assert "personally did" in lowered
    assert "turned out" in lowered
    assert "trade-off" not in lowered
    assert "measurable impact" not in lowered
    assert plan.seed == "What did you do next, and how did it turn out?"


def test_question_kind_travels_in_the_plan() -> None:
    """S7 (половина в оркестраторе): класс доезжает до плана, а из него в транскрипт."""
    orch = InterviewOrchestrator(behavioral_pool(), clock=FakeClock())
    assert orch.intro_plan().question_kind == "behavioral"
    assert InterviewOrchestrator(make_pool(), clock=FakeClock()).intro_plan().question_kind == (
        "technical"
    )


STRONG_BOTH_WAYS = (
    "Our PM wanted to ship without the review queue. I showed him two false "
    "positives from the week before, and we agreed to keep it behind a flag. "
    "In the end we shipped a week later and cut manual checks by 40 percent."
)


def test_a_real_session_actually_asks_behavioral_questions() -> None:
    """L22: «банк загружен» и «вопрос задан» — разные утверждения.

    Ответ здесь силён по ОБОИМ критериям (есть цифра, есть эпизод с исходом),
    поэтому допросов не будет и оркестратор пройдёт весь пул.
    """
    pool = pick_session_pool(
        load_bank(TECHNICAL_BANK), load_bank(BEHAVIORAL_BANK), count=6, rng=random.Random(42)
    )
    orch = InterviewOrchestrator(pool, clock=FakeClock())

    asked = [orch.intro_plan().question_kind]
    for _ in range(4):
        orch.on_user_answer(STRONG_BOTH_WAYS)  # первый follow-up — всегда
        asked.append(orch.on_user_answer(STRONG_BOTH_WAYS).question_kind)

    assert "behavioral" in asked, asked
    assert "technical" in asked, asked
