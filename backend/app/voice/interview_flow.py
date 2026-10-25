"""Mode 1 session state: orchestrator + history + transcript, checkpointed per turn."""

from typing import Any

from app.orchestrator.interview import InterviewOrchestrator, TurnPlan
from app.storage.repositories.interviews import InterviewRepository
from app.voice.session_flow import SessionFlow


class InterviewFlow(SessionFlow[InterviewRepository]):
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
        super().__init__(session_id, system_prompt, repo)
        self.orchestrator = orchestrator
        self.interview_mode = interview_mode
        self.current_plan: TurnPlan = orchestrator.intro_plan()

    async def start(self, intro_text: str) -> None:
        await self.repo.create(
            self.session_id, interview_mode=self.interview_mode, persona=self.persona
        )
        self.buffer.append(
            "agent",
            intro_text,
            state=self.current_plan.state.value,
            question_id=self.current_plan.question_id,
            question_kind=self.current_plan.question_kind,
        )
        self._remember_agent_message(intro_text)
        await self._checkpoint()

    async def on_user(self, text: str) -> TurnPlan:
        """Record the answer against the question it answers, then plan the next move."""
        self._record_user(text)
        plan: TurnPlan = self.orchestrator.on_user_answer(text)
        self._remember_user_message(self.orchestrator.build_user_message(plan, text))
        self.current_plan = plan
        await self._checkpoint()
        return plan

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


def question_progress(flow: object) -> dict[str, Any]:
    """Где мы в интервью — клиенту, чтобы показать «вопрос N из M» (doc 15).

    Знать, сколько осталось, снимает тревогу, а это и есть задача тренажёра.
    У разбора и разговора своего счётчика вопросов нет, поэтому там поля пустые.
    Жило в `ws_voice.py`; переехало к интервью, когда обработчик подошёл к 500 строкам.
    """
    if not isinstance(flow, InterviewFlow):
        return {"question_index": None, "question_total": None, "question_kind": None}
    return {
        "question_index": flow.orchestrator.question_number,
        "question_total": flow.orchestrator.question_count,
        "question_kind": flow.current_plan.question_kind,
    }
