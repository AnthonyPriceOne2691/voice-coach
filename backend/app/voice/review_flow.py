"""Mode 2 session state: review orchestrator + history + transcript (SQLite per turn)."""

from typing import Any

from app.common.interfaces import ChatMessage
from app.orchestrator.review import ReviewOrchestrator, ReviewPlan
from app.storage.repositories.reviews import ReviewRepository
from app.storage.turns import TranscriptBuffer


class ReviewFlow:
    persona = "recruiter_friend"

    def __init__(
        self,
        review_id: str,
        source_interview_id: str,
        orchestrator: ReviewOrchestrator,
        system_prompt: str,
        repo: ReviewRepository,
    ) -> None:
        self.session_id = review_id
        self.source_interview_id = source_interview_id
        self.orchestrator = orchestrator
        self.repo = repo
        self._system = system_prompt
        self._history: list[ChatMessage] = []
        self.buffer = TranscriptBuffer()
        self.current_plan: ReviewPlan = orchestrator.intro_plan()
        self.hard_violations = 0
        self.soft_violations = 0
        self.fallback_count = 0

    async def start(self) -> None:
        await self.repo.create(
            self.session_id, source_interview_id=self.source_interview_id, persona=self.persona
        )

    async def on_user(self, text: str) -> ReviewPlan:
        self.buffer.append(
            "user",
            text,
            state=self.current_plan.state.value,
            question_id=self.current_plan.question_id,
        )
        plan = self.orchestrator.on_user(text)
        self._history.append({"role": "user", "content": self._wrap(plan, text)})
        self.current_plan = plan
        await self._checkpoint()
        return plan

    async def on_agent(
        self, text: str, *, violations: list[dict[str, Any]], fallback_used: bool
    ) -> None:
        self.buffer.append(
            "agent",
            text,
            state=self.current_plan.state.value,
            question_id=self.current_plan.question_id,
        )
        self._history.append({"role": "assistant", "content": text})
        for event in violations:
            if event["severity"] == "hard":
                self.hard_violations += 1
            else:
                self.soft_violations += 1
        if fallback_used:
            self.fallback_count += 1
        await self._checkpoint()

    @property
    def messages(self) -> list[ChatMessage]:
        return [{"role": "system", "content": self._system}, *self._history]

    @property
    def finished(self) -> bool:
        return self.orchestrator.finished

    async def finish(self, *, status: str) -> None:
        await self._checkpoint()
        await self.repo.finish(self.session_id, status=status)

    @staticmethod
    def _wrap(plan: ReviewPlan, text: str) -> str:
        return (
            f"[STATE={plan.state.value}]\n"
            f"[QUESTION={plan.question_number or '-'}]\n"
            f"Instruction: {plan.instruction}\n"
            f"Candidate says:\n{text}"
        )

    async def _checkpoint(self) -> None:
        await self.repo.checkpoint(
            self.session_id,
            self.buffer.to_json_list(),
            {
                "questions_reviewed": self.orchestrator.questions_reviewed,
                "question_count": self.orchestrator.question_count,
                "hard_violations": self.hard_violations,
                "soft_violations": self.soft_violations,
                "fallback_count": self.fallback_count,
            },
        )
