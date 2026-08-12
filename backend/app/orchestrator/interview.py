"""Interview state machine (doc 04): deterministic structure, zero extra LLM calls.

Follow-up policy (doc 04 v2026-07-02):
  1. first follow-up — always (while time allows)
  2. second — only if the answer is short (<40 words) or has no digits/metrics
  3. max 2 per core question
  4. <20% session time left -> follow-ups off
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from app.orchestrator.question_bank import Question

SHORT_ANSWER_WORDS = 40
FOLLOW_UPS_OFF_AT = 0.8  # fraction of session elapsed
MAX_FOLLOW_UPS = 2
HARD_STOP_FACTOR = 16 / 15  # doc 04: hard stop at 16 min for a 15-min session

_DIGIT = re.compile(r"\d")


class Phase(StrEnum):
    INTRO = "INTRO"
    CORE_QUEST = "CORE_QUEST"
    FOLLOW_UP = "FOLLOW_UP"
    WRAP_UP = "WRAP_UP"
    DEBRIEF = "DEBRIEF"


@dataclass(frozen=True)
class TurnPlan:
    """What the LLM must do this turn — structure decided here, wording by the LLM."""

    state: Phase
    question_id: str | None
    instruction: str
    seed: str  # speakable fallback line for contract recovery
    follow_up_count: int
    time_remaining_min: int


class InterviewOrchestrator:
    def __init__(
        self,
        pool: list[Question],
        *,
        duration_min: int = 15,
        wrap_up_seed: str = "That's all from my side. Do you have any questions for us?",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not pool:
            raise ValueError("question pool is empty")
        self._pool = pool
        self._index = 0
        self._follow_ups = 0
        self._total_follow_ups = 0
        self._duration_s = duration_min * 60
        self._wrap_up_seed = wrap_up_seed
        self._clock = clock
        self._started = clock()
        self.phase = Phase.INTRO

    # -- public API -----------------------------------------------------------

    def intro_plan(self) -> TurnPlan:
        """The intro template already asks the first question (D-4)."""
        return self._plan(Phase.INTRO, self._current_question())

    def on_user_answer(self, answer: str) -> TurnPlan:
        """Decide the next move after a user answer. Pure policy — unit-testable."""
        if self.phase == Phase.WRAP_UP:
            self.phase = Phase.DEBRIEF
            return self._plan(Phase.DEBRIEF, None)
        if self.phase == Phase.INTRO:
            self.phase = Phase.CORE_QUEST

        if self._elapsed_fraction() >= HARD_STOP_FACTOR or (
            self._is_last_question() and not self._may_follow_up(answer)
        ):
            return self._wrap_up()

        if self._may_follow_up(answer):
            self._follow_ups += 1
            self._total_follow_ups += 1
            self.phase = Phase.FOLLOW_UP
            return self._plan(Phase.FOLLOW_UP, self._current_question())

        if self._is_last_question():
            return self._wrap_up()
        self._index += 1
        self._follow_ups = 0
        self.phase = Phase.CORE_QUEST
        return self._plan(Phase.CORE_QUEST, self._current_question())

    @property
    def finished(self) -> bool:
        return self.phase == Phase.DEBRIEF

    def snapshot(self) -> dict[str, int | str]:
        return {
            "phase": self.phase.value,
            "questions_asked": self._index + 1,
            "follow_ups": self._total_follow_ups,
            "duration_sec": int(self._clock() - self._started),
        }

    def build_user_message(self, plan: TurnPlan, user_answer: str) -> str:
        """Doc 16 wrapper: orchestrator context travels in the user turn, not the system."""
        return (
            f"[STATE={plan.state.value}]\n"
            f"[QUESTION_ID={plan.question_id or '-'}]\n"
            f"[FOLLOW_UP_COUNT={plan.follow_up_count}]\n"
            f"[TIME_REMAINING_MIN={plan.time_remaining_min}]\n"
            f"Instruction: {plan.instruction}\n"
            f"Candidate answer:\n{user_answer}"
        )

    # -- policy internals -----------------------------------------------------

    def _may_follow_up(self, answer: str) -> bool:
        if self._follow_ups >= MAX_FOLLOW_UPS:
            return False
        if self._elapsed_fraction() >= FOLLOW_UPS_OFF_AT:
            return False
        if self._follow_ups == 0:
            return True  # first follow-up is always worth it — that's the practice
        words = len(answer.split())
        return words < SHORT_ANSWER_WORDS or not _DIGIT.search(answer)

    def _wrap_up(self) -> TurnPlan:
        self.phase = Phase.WRAP_UP
        return self._plan(Phase.WRAP_UP, None)

    def _current_question(self) -> Question:
        return self._pool[self._index]

    def _is_last_question(self) -> bool:
        return self._index >= len(self._pool) - 1

    def _elapsed_fraction(self) -> float:
        return (self._clock() - self._started) / self._duration_s

    def _time_remaining_min(self) -> int:
        return max(0, int((self._duration_s - (self._clock() - self._started)) / 60))

    def _plan(self, phase: Phase, question: Question | None) -> TurnPlan:
        if phase == Phase.FOLLOW_UP and question is not None:
            instruction = (
                f"Ask ONE follow-up on their answer about '{question.theme}'. "
                "If a technology was named without a trade-off, ask why X over Y. "
                "If the claim was vague, ask for the measurable impact. "
                "If it contradicts the profile, probe the inconsistency. "
                "Otherwise ask them to elaborate."
            )
            seed = "Help me understand the trade-off you considered there."
        elif phase == Phase.CORE_QUEST and question is not None:
            instruction = (
                "Briefly acknowledge, then ask the next question (adapt the wording, "
                f"keep the intent): {question.seed}"
            )
            seed = question.seed
        elif phase == Phase.WRAP_UP:
            instruction = (
                "Time is up. Thank them briefly and ask if they have any questions for us."
            )
            seed = self._wrap_up_seed
        elif phase == Phase.DEBRIEF:
            instruction = "Session over."
            seed = "Thanks — that's the end of our mock interview."
        else:  # INTRO — spoken from the template, LLM not involved
            instruction = "Intro is template-driven."
            seed = question.seed if question else ""
        return TurnPlan(
            state=phase,
            question_id=question.id if question else None,
            instruction=instruction,
            seed=seed,
            follow_up_count=self._follow_ups,
            time_remaining_min=self._time_remaining_min(),
        )
