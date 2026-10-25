"""Talk session state (D3a): transcript on every turn, a windowed history for the model."""

from typing import Any

from app.common.interfaces import ChatMessage
from app.orchestrator.talk import TalkOrchestrator, TalkPlan
from app.storage.repositories.talks import TalkRepository
from app.storage.turns import TIP_STATE
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

#: Счётчики проверки речи в метаданных разговора: `checks_run`, `checks_noted`, …
CHECK_COUNTERS = ("run", "noted", "cancelled", "failed")


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
        #: Заметки к речи (D3a.2) — контракт с экраном talk-notes, doc 12.
        self.language_notes: list[dict[str, Any]] = []
        self.check_counts = dict.fromkeys(CHECK_COUNTERS, 0)
        #: Реплика, на которую отвечает МОДЕЛЬ, и её индекс в транскрипте: только её
        #: проверяет речь. Просьбу («change the topic», «bye») код отвечает сам —
        #: проверять там нечего и незачем.
        self.last_user_text = ""
        self.last_user_turn_index: int | None = None

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
        answered_by_model = not plan.lines
        self.last_user_text = text if answered_by_model else ""
        self.last_user_turn_index = len(self.buffer.turns) - 1 if answered_by_model else None
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

    async def on_tip(self, line: str, note: dict[str, Any]) -> None:
        """Подсказка прозвучала (D3a.2): она в транскрипте и в списке, но не в истории модели.

        Модель подсказку не видит (инвариант 4): иначе училась бы поправлять сама, а
        поправки — работа кода (I3-H4). Префикс следующего хода от этого не меняется.
        """
        self.buffer.append("agent", line, state=TIP_STATE)
        note["spoken"] = True
        await self._checkpoint()

    def add_note(self, note: dict[str, Any]) -> None:
        """Заметка — только в память потока; в базу её несёт следующий чекпойнт.

        ⚠ Без записи в базу НАМЕРЕННО: зовёт фоновая проверка, а её отменяет
        следующая реплика. Отмена посередине `async with db.session()` — ровно класс
        виса 2026-08 (соединение вне пула, L5–L7).
        """
        self.language_notes.append(note)
        self.check_counts["noted"] += 1

    async def _checkpoint(self) -> None:
        metadata: dict[str, Any] = {
            **self.orchestrator.snapshot(),
            **self._counters(),
            "language_notes": self.language_notes,
            **{f"checks_{name}": count for name, count in self.check_counts.items()},
        }
        await self.repo.checkpoint(self.session_id, self.buffer.to_json_list(), metadata)
