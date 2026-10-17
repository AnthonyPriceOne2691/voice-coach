"""Talk session state (D3a): transcript on every turn, a windowed history for the model."""

from typing import Any

from app.common.interfaces import ChatMessage
from app.orchestrator.talk import TalkOrchestrator, TalkPlan
from app.storage.repositories.talks import TalkRepository
from app.voice.session_flow import SessionFlow

#: Окно истории: модель видит системный промпт и не больше WINDOW_MAX последних
#: сообщений. Разговор длиннее интервью, и без окна история однажды вытеснила бы
#: системный промпт из num_ctx 8192 — молча (doc 20, L21).
#:
#: ⚠ Окно сдвигается СТУПЕНЬКОЙ по WINDOW_STEP, а не на каждом ходе. Ollama
#: переиспользует KV-кэш по неизменному префиксу (doc 20: тёплый TTFT 0.17 s), и
#: окно, скользящее по одному сообщению, меняло бы префикс каждый ход — полный
#: prefill всей истории на каждом ответе. Ступенька платит его раз в WINDOW_STEP.
WINDOW_MAX = 40
WINDOW_STEP = 20


def window_start(size: int) -> int:
    """С какого сообщения истории начинается окно: 0, пока всё влезает."""
    if size <= WINDOW_MAX:
        return 0
    return ((size - WINDOW_MAX - 1) // WINDOW_STEP + 1) * WINDOW_STEP


class TalkFlow(SessionFlow[TalkRepository]):
    persona = "friend_mentor"

    def __init__(
        self,
        session_id: str,
        orchestrator: TalkOrchestrator,
        system_prompt: str,
        repo: TalkRepository,
    ) -> None:
        super().__init__(session_id, system_prompt, repo)
        self.orchestrator = orchestrator
        self.current_plan: TalkPlan = orchestrator.intro_plan()

    async def start(self) -> str:
        """Записать начало разговора; вернуть реплику, которую говорит код."""
        await self.repo.create(self.session_id, persona=self.persona)
        opening = " ".join(self.current_plan.lines)
        await self.on_spoken(opening)
        return opening

    async def on_user(self, text: str) -> TalkPlan:
        """Решение о ходе — до записи: реплика помечается тем, чем она оказалась."""
        plan: TalkPlan = self.orchestrator.on_user(text)
        self.current_plan = plan
        self.buffer.append("user", text, state=plan.state.value)
        if plan.remember:
            self._remember_user_message(text)
        await self._checkpoint()
        return plan

    async def on_spoken(self, text: str) -> None:
        """Реплика, которую выбрал код: приветствие, тема, отказ, прощание."""
        self.buffer.append("agent", text, state=self.current_plan.state.value)
        if self.current_plan.remember:
            self._remember_agent_message(text)
        await self._checkpoint()

    @property
    def messages(self) -> list[ChatMessage]:
        window = self._history[window_start(len(self._history)) :]
        return [{"role": "system", "content": self._system}, *window]

    async def _checkpoint(self) -> None:
        metadata: dict[str, Any] = {**self.orchestrator.snapshot(), **self._counters()}
        await self.repo.checkpoint(self.session_id, self.buffer.to_json_list(), metadata)
