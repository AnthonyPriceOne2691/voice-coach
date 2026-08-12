"""Mode 2 session state: review orchestrator + history + transcript (SQLite per turn)."""

from app.orchestrator.review import ReviewOrchestrator, ReviewPlan
from app.storage.repositories.reviews import ReviewRepository
from app.voice.session_flow import SessionFlow


class ReviewFlow(SessionFlow[ReviewRepository]):
    persona = "recruiter_friend"

    def __init__(
        self,
        review_id: str,
        source_interview_id: str,
        orchestrator: ReviewOrchestrator,
        system_prompt: str,
        repo: ReviewRepository,
    ) -> None:
        super().__init__(review_id, system_prompt, repo)
        self.source_interview_id = source_interview_id
        self.orchestrator = orchestrator
        self.current_plan: ReviewPlan = orchestrator.intro_plan()

    async def start(self) -> None:
        await self.repo.create(
            self.session_id, source_interview_id=self.source_interview_id, persona=self.persona
        )

    async def on_user(self, text: str) -> ReviewPlan:
        self._record_user(text)
        plan: ReviewPlan = self.orchestrator.on_user(text)
        self._remember_user_message(self._wrap(plan, text))
        self.current_plan = plan
        await self._checkpoint()
        return plan

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
