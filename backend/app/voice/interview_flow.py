"""Mode 1 session state: orchestrator + history + transcript, checkpointed per turn."""

from typing import Any

from app.common.interfaces import ChatMessage
from app.orchestrator.interview import InterviewOrchestrator, TurnPlan
from app.storage.repositories.interviews import InterviewRepository
from app.storage.turns import TranscriptBuffer


class InterviewFlow:
    persona = "senior_colleague"

    def __init__(
        self,
        session_id: str,
        orchestrator: InterviewOrchestrator,
        system_prompt: str,
        repo: InterviewRepository,
        *,
        interview_mode: str,
    ) -> None:
        self.session_id = session_id
        self.orchestrator = orchestrator
        self.repo = repo
        self.interview_mode = interview_mode
        self._system = system_prompt
        self._history: list[ChatMessage] = []
        self.buffer = TranscriptBuffer()
        self.current_plan: TurnPlan = orchestrator.intro_plan()
        self.hard_violations = 0
        self.soft_violations = 0
        self.fallback_count = 0

    async def start(self, intro_text: str) -> None:
        await self.repo.create(
            self.session_id, interview_mode=self.interview_mode, persona=self.persona
        )
        self.buffer.append(
            "agent",
            intro_text,
            state=self.current_plan.state.value,
            question_id=self.current_plan.question_id,
        )
        self._history.append({"role": "assistant", "content": intro_text})
        await self._checkpoint()

    async def on_user(self, text: str) -> TurnPlan:
        """Record the answer against the question it answers, then plan the next move."""
        self.buffer.append(
            "user",
            text,
            state=self.current_plan.state.value,
            question_id=self.current_plan.question_id,
        )
        plan = self.orchestrator.on_user_answer(text)
        self._history.append(
            {"role": "user", "content": self.orchestrator.build_user_message(plan, text)}
        )
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

    async def _checkpoint(self) -> None:
        metadata: dict[str, Any] = dict(self.orchestrator.snapshot())
        metadata.update(
            {
                "hard_violations": self.hard_violations,
                "soft_violations": self.soft_violations,
                "fallback_count": self.fallback_count,
            }
        )
        await self.repo.checkpoint(self.session_id, self.buffer.to_json_list(), metadata)
