"""Review Together orchestrator (doc 11): walk interview Q&A, grounded, question by question.

Deterministic advance rule: a user turn containing "?" keeps the pointer (answer their
question first — USER_Q); otherwise move to the next interview question. G2-H3 (cover
every question before wrap-up) is guaranteed by the pointer itself.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

ANSWER_EXCERPT_CHARS = 700  # doc 20: segmented Q&A is a compression, not a raw transcript


class ReviewPhase(StrEnum):
    INTRO = "INTRO"
    WALK_QUESTIONS = "WALK_QUESTIONS"
    WRAP_UP = "WRAP_UP"
    END = "END"


@dataclass(frozen=True)
class QASegment:
    question_id: str
    question_text: str
    answer_text: str


@dataclass(frozen=True)
class ReviewPlan:
    state: ReviewPhase
    question_id: str | None
    question_number: int  # 1-based; 0 when not applicable
    instruction: str
    seed: str
    #: Разбор идёт по сегментам интервью, своего класса у хода Mode 2 нет —
    #: поле есть ради общего кода записи транскрипта (`SessionFlow`).
    question_kind: str | None = None


def build_segments(turns: list[dict[str, Any]]) -> list[QASegment]:
    """Group interview turns into per-question segments using question_id (doc 12)."""
    order: list[str] = []
    questions: dict[str, str] = {}
    answers: dict[str, list[str]] = {}
    for turn in turns:
        question_id = turn.get("question_id")
        if not question_id:
            continue
        if question_id not in order:
            order.append(question_id)
            answers[question_id] = []
        if turn["role"] == "agent" and question_id not in questions:
            questions[question_id] = turn["text"]
        elif turn["role"] == "user":
            answers[question_id].append(turn["text"])
    segments = []
    for question_id in order:
        answer = " / ".join(answers.get(question_id, []))[:ANSWER_EXCERPT_CHARS]
        if not answer:
            continue  # never reviewed a question the candidate did not answer
        segments.append(
            QASegment(
                question_id=question_id,
                question_text=questions.get(question_id, question_id),
                answer_text=answer,
            )
        )
    return segments


def render_segments(segments: list[QASegment]) -> str:
    return "\n".join(
        f"Q{i + 1}: {s.question_text}\nA{i + 1}: {s.answer_text}" for i, s in enumerate(segments)
    )


class ReviewOrchestrator:
    def __init__(self, segments: list[QASegment]) -> None:
        if not segments:
            raise ValueError("no answered questions to review")
        self._segments = segments
        self._pointer = 0
        self.phase = ReviewPhase.INTRO

    @property
    def question_count(self) -> int:
        return len(self._segments)

    @property
    def questions_reviewed(self) -> int:
        return min(self._pointer, len(self._segments))

    @property
    def finished(self) -> bool:
        return self.phase == ReviewPhase.END

    def intro_plan(self) -> ReviewPlan:
        segment = self._segments[0]
        return ReviewPlan(
            state=ReviewPhase.INTRO,
            question_id=segment.question_id,
            question_number=1,
            instruction=(
                "Greet briefly as their recruiter friend: good session, let's go through it "
                "together. Then start reviewing Q1: say what was strong (be specific), what "
                "could be sharper, and offer one spoken rephrase."
            ),
            seed="Good session. Let's go through it together, starting with question one.",
        )

    def on_user(self, text: str) -> ReviewPlan:
        if self.phase == ReviewPhase.WRAP_UP:
            self.phase = ReviewPhase.END
            return ReviewPlan(
                state=ReviewPhase.END,
                question_id=None,
                question_number=0,
                instruction="Review over.",
                seed="Great work today — see you at the next session.",
            )
        if self.phase == ReviewPhase.INTRO:
            self.phase = ReviewPhase.WALK_QUESTIONS

        if "?" in text:  # USER_Q: answer first, stay on the current question
            segment = self._segments[min(self._pointer, len(self._segments) - 1)]
            number = min(self._pointer, len(self._segments) - 1) + 1
            return ReviewPlan(
                state=ReviewPhase.WALK_QUESTIONS,
                question_id=segment.question_id,
                question_number=number,
                instruction=(
                    "Answer the candidate's question, grounded strictly in the interview "
                    f"transcript, in the context of Q{number}. Then continue the review."
                ),
                seed=f"Let's stay on question {number} for a moment.",
            )

        self._pointer += 1
        if self._pointer >= len(self._segments):
            self.phase = ReviewPhase.WRAP_UP
            return ReviewPlan(
                state=ReviewPhase.WRAP_UP,
                question_id=None,
                question_number=0,
                instruction=(
                    "Wrap up the review: give the 2-3 main takeaways and what to focus on "
                    "next session. Ask if they have any final questions."
                ),
                seed=(
                    "Main takeaways: keep answers tight and lead with the metric. "
                    "Any final questions?"
                ),
            )
        number = self._pointer + 1
        segment = self._segments[self._pointer]
        return ReviewPlan(
            state=ReviewPhase.WALK_QUESTIONS,
            question_id=segment.question_id,
            question_number=number,
            instruction=(
                f"Review Q{number} of {len(self._segments)}: say what was strong (specific), "
                "what could be sharper, and offer one spoken rephrase if needed."
            ),
            seed=f"Let's look at question {number}.",
        )
