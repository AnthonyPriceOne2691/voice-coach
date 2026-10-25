"""Фоновая проверка речи (D3a.2): сбой проверки — не сбой разговора."""

import random
from collections.abc import AsyncIterator
from typing import Any

from app.config import REPO_ROOT
from app.contracts.enforcer import ContractEnforcer
from app.contracts.spec import load_contract
from app.knowledge.prompts import PromptLibrary
from app.llm.ollama_client import OllamaError
from app.orchestrator.talk import TalkOrchestrator, load_script
from app.voice.talk_checks import TalkChecks
from app.voice.talk_flow import TalkFlow


class NullRepo:
    async def checkpoint(self, *_: Any) -> None: ...

    async def finish(self, *_: Any, **__: Any) -> None: ...

    async def create(self, *_: Any, **__: Any) -> None: ...


class BrokenLlm:
    """Проверка падает: модель недоступна (`OllamaError`) или ломается иначе."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    async def stream_chat(self, *_: Any, **__: Any) -> AsyncIterator[str]:
        raise self.error
        yield ""  # pragma: no cover — генератор, а не корутина


def _checks(llm: Any) -> TalkChecks:
    return TalkChecks(
        llm,
        PromptLibrary(REPO_ROOT / "data" / "prompts", REPO_ROOT / "data" / "knowledge"),
        ContractEnforcer(load_contract(REPO_ROOT / "data" / "contracts" / "talk.contract.yaml")),
        model="m",
        temperature=0.0,
        max_tokens=120,
    )


async def _flow_after(said: str) -> TalkFlow:
    script = load_script(REPO_ROOT / "data" / "talk" / "talk.yaml")
    flow = TalkFlow(
        "t-1", TalkOrchestrator(script, rng=random.Random(1)), "talk system", NullRepo()
    )  # type: ignore[arg-type]
    await flow.start()
    await flow.on_user(said)
    return flow


async def test_unreachable_model_is_counted_and_the_talk_goes_on() -> None:
    """C8: модель не ответила — проверка посчитана упавшей, заметки нет, исключения наружу нет."""
    flow = await _flow_after("Yesterday I go to the office.")
    checks = _checks(BrokenLlm(OllamaError("down")))
    checks.start(flow)
    await checks.finished()
    await checks.cancel()  # задача уже кончилась сама — отмена ничего не считает
    assert flow.check_counts == {"run": 1, "noted": 0, "cancelled": 0, "failed": 1}
    assert flow.language_notes == []


async def test_unexpected_crash_is_logged_not_raised(caplog: Any) -> None:
    """Неожиданное исключение в проверке не доходит до разговора и не теряется молча."""
    flow = await _flow_after("Yesterday I go to the office.")
    checks = _checks(BrokenLlm(ValueError("boom")))
    checks.start(flow)
    await checks.finished()
    assert flow.check_counts["failed"] == 1
    assert "talk check crashed" in caplog.text


async def test_request_answered_by_code_starts_no_check() -> None:
    """Просьбу («change the topic») отвечает код — проверять нечего, задачи нет."""
    flow = await _flow_after("Can we talk about something else?")
    checks = _checks(BrokenLlm(OllamaError("must not be called")))
    checks.start(flow)
    await checks.finished()
    assert flow.check_counts["run"] == 0
