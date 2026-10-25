"""Фоновая проверка речи в разговоре (D3a.2) — задача с владельцем.

Порядок держит инвариант 2 спеки «проверка ничего не задерживает»:

* стартует, когда ответ Генри уже сгенерирован (первый звук хода не сдвигается);
* следующая реплика Антона отменяет незаконченную проверку И ДОЖИДАЕТСЯ отмены:
  без await отмена только помечена, а слот Ollama занят — ответ встал бы в очередь
  за проверкой, которая уже никому не нужна;
* конец и уборка сессии отменяют её так же — тот же класс, что `_warmup_task`
  (задача-сирота держит соединение, и закрытие цикла ждёт её вечно, L5–L7).

Задача ничего не пишет в базу: заметка уходит в память потока (`TalkFlow.add_note`),
а на диск — со следующим чекпойнтом хода или с `finish`.
"""

import asyncio
import contextlib
import logging

from app.common.interfaces import ChatMessage, LlmClient
from app.contracts.enforcer import ContractEnforcer
from app.knowledge.prompts import PromptLibrary
from app.llm.ollama_client import OllamaError
from app.orchestrator.tips import Rejection, contract_gate, decide, parse_candidate
from app.voice.language_check import ask_candidate, check_messages
from app.voice.talk_flow import TalkFlow

logger = logging.getLogger(__name__)


class TalkChecks:
    def __init__(
        self,
        llm: LlmClient,
        prompts: PromptLibrary,
        enforcer: ContractEnforcer,
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self._llm = llm
        self._prompts = prompts
        self._passes = contract_gate(enforcer)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._task: asyncio.Task[None] | None = None
        self._flow: TalkFlow | None = None

    def start(self, flow: TalkFlow) -> None:
        """Проверить реплику, на которую только что ответила модель."""
        utterance, turn_index = flow.last_user_text, flow.last_user_turn_index
        if not utterance or turn_index is None:
            return
        messages = check_messages(flow.messages, self._prompts.language_check(utterance))
        self._flow = flow
        self._task = asyncio.create_task(self._run(flow, messages, utterance, turn_index))

    async def finished(self) -> None:
        """Дождаться текущей проверки, не отменяя её (подсказка вслух ждёт её с дедлайном)."""
        task = self._task
        if task is not None:
            await asyncio.wait({task})

    async def cancel(self) -> None:
        """Снять незаконченную проверку и дождаться снятия."""
        task, self._task = self._task, None
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        if self._flow is not None:
            self._flow.check_counts["cancelled"] += 1

    async def _run(
        self, flow: TalkFlow, messages: list[ChatMessage], utterance: str, turn_index: int
    ) -> None:
        """Сбой проверки — не сбой разговора: записан и посчитан, но наружу не идёт.

        Отмена (`CancelledError`) — не `Exception` и проходит насквозь, как и должна.
        """
        flow.check_counts["run"] += 1
        try:
            await self._check(flow, messages, utterance, turn_index)
        except OllamaError:
            flow.check_counts["failed"] += 1
            logger.warning("talk check failed", extra={"turn_index": turn_index}, exc_info=True)
        except Exception:
            flow.check_counts["failed"] += 1
            logger.exception("talk check crashed", extra={"turn_index": turn_index})

    async def _check(
        self, flow: TalkFlow, messages: list[ChatMessage], utterance: str, turn_index: int
    ) -> None:
        raw = await ask_candidate(
            self._llm,
            messages,
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        candidate = parse_candidate(raw)
        verdict = (
            candidate
            if isinstance(candidate, Rejection)
            else decide(
                candidate, utterance, seen=flow.language_notes, passes_contract=self._passes
            )
        )
        if isinstance(verdict, Rejection):
            logger.info(
                "talk check: no note", extra={"turn_index": turn_index, "reason": verdict.value}
            )
            return
        flow.add_note({"turn_index": turn_index, **verdict})
        logger.info("talk check: note", extra={"turn_index": turn_index, "kind": verdict["kind"]})
