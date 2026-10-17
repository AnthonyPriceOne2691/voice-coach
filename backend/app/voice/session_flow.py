"""Общая часть голосовой сессии — то, что у Mode 1 и Mode 2 совпадало дословно.

Обе сессии ведут одно и то же: историю для модели, транскрипт с чекпойнтом на
каждом ходе и счётчики нарушений. Различаются они оркестратором, обёрткой
пользовательской реплики и составом метаданных — это и остаётся в наследниках.

Выделено не «для красоты»: 36 строк жили копией в двух файлах, и правка мета-хода
(2026-08-12) должна была лечь третьей копией. Rule-of-three сработало буквально.
"""

from typing import Any, Protocol

from app.common.interfaces import ChatMessage
from app.storage.turns import TranscriptBuffer, append_meta


class SessionRepository(Protocol):
    """То, что обеим сессиям нужно от своего репозитория."""

    async def checkpoint(
        self, session_id: str, turns: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> None: ...

    async def finish(self, session_id: str, *, status: str) -> None: ...


class SessionFlow[RepoT: SessionRepository]:
    """Транскрипт, история и счётчики; чем чекпойнтить — решает наследник.

    Параметр типа — репозиторий: у режимов он свой, и наследнику нужен целиком
    (у каждого свой `create` со своими полями). База знает общий минимум, а
    наследник — свой полный тип, не сужая атрибут базы.
    """

    #: Заполняются наследником в его `__init__` — у каждого свой тип.
    orchestrator: Any
    current_plan: Any

    def __init__(self, session_id: str, system_prompt: str, repo: RepoT) -> None:
        self.session_id = session_id
        self.repo = repo
        self._system = system_prompt
        self._history: list[ChatMessage] = []
        self.buffer = TranscriptBuffer()
        self.hard_violations = 0
        self.soft_violations = 0
        self.fallback_count = 0

    # -- ходы ------------------------------------------------------------------

    async def on_agent(
        self, text: str, *, violations: list[dict[str, Any]], fallback_used: bool
    ) -> None:
        plan = self.current_plan
        self.buffer.append(
            "agent",
            text,
            state=plan.state.value,
            question_id=plan.question_id,
            question_kind=plan.question_kind,
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

    async def on_meta(self, user_text: str, agent_text: str) -> None:
        """Мета-ход (просьба о темпе): в транскрипт, но мимо оркестратора и истории.

        История LLM не пополняется СОЗНАТЕЛЬНО: модель не должна увидеть ни
        просьбы, ни повтора своей же реплики — иначе в контексте появится дубль
        вопроса, а бюджет токенов (doc 20) платит за него каждый следующий ход.
        """
        append_meta(self.buffer, user_text, agent_text)
        await self._checkpoint()

    def _record_user(self, text: str) -> None:
        plan = self.current_plan
        self.buffer.append(
            "user",
            text,
            state=plan.state.value,
            question_id=plan.question_id,
            question_kind=plan.question_kind,
        )

    def _remember_user_message(self, content: str) -> None:
        self._history.append({"role": "user", "content": content})

    def _remember_agent_message(self, content: str) -> None:
        self._history.append({"role": "assistant", "content": content})

    # -- состояние -------------------------------------------------------------

    @property
    def messages(self) -> list[ChatMessage]:
        return [{"role": "system", "content": self._system}, *self._history]

    @property
    def finished(self) -> bool:
        finished: bool = self.orchestrator.finished
        return finished

    async def finish(self, *, status: str) -> None:
        await self._checkpoint()
        await self.repo.finish(self.session_id, status=status)

    def _counters(self) -> dict[str, int]:
        """Счётчики нарушений для метаданных чекпойнта."""
        return {
            "hard_violations": self.hard_violations,
            "soft_violations": self.soft_violations,
            "fallback_count": self.fallback_count,
        }

    # -- чем наполняет наследник ------------------------------------------------

    async def _checkpoint(self) -> None:
        """Метаданные у режимов разные — снимок собирает наследник."""
        raise NotImplementedError
