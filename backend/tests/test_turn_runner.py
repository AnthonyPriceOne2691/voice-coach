"""TurnRunner: sentence-gated generation with the doc 13 recovery ladder."""

from pathlib import Path

import pytest

from app.contracts.enforcer import ContractEnforcer, TurnContext
from app.contracts.spec import load_contract
from app.voice.turn_runner import AgentCompleted, AgentSentence, LlmParams, TurnRunner
from tests.fakes import FakeLlm, FakeTts, ScriptedLlm

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "data" / "contracts"
PARAMS = LlmParams(model="m", temperature=0.7, max_tokens=100)
SEED = "Help me understand the trade-off you considered there."


@pytest.fixture(scope="module")
def enforcer() -> ContractEnforcer:
    return ContractEnforcer(load_contract(CONTRACTS_DIR / "interview.contract.yaml"))


async def _run(runner: TurnRunner, llm_messages=None, **kwargs):  # type: ignore[no-untyped-def]
    return [e async for e in runner.run(llm_messages or [], PARAMS, **kwargs)]


async def test_sentence_streaming_without_enforcer() -> None:
    tts = FakeTts()
    runner = TurnRunner(FakeLlm(["One. ", "Two and ", "a tail"]), tts)
    events = await _run(runner)
    sentences = [e for e in events if isinstance(e, AgentSentence)]
    assert [s.text for s in sentences] == ["One.", "Two and a tail"]
    assert tts.synthesized == ["One.", "Two and a tail"]  # per-sentence TTS
    completed = events[-1]
    assert isinstance(completed, AgentCompleted)
    assert completed.text == "One. Two and a tail"
    assert completed.fallback_used is False


async def test_clean_turn_passes_enforcer(enforcer: ContractEnforcer) -> None:
    runner = TurnRunner(FakeLlm(["Got it. ", "Why separate queues? "]), FakeTts())
    events = await _run(
        runner, enforcer=enforcer, ctx=TurnContext(state="FOLLOW_UP"), seed=SEED, intent="x"
    )
    completed = events[-1]
    assert isinstance(completed, AgentCompleted)
    assert completed.text == "Got it. Why separate queues?"
    assert completed.violations == []


async def test_violation_mid_turn_truncates_but_keeps_prefix(enforcer: ContractEnforcer) -> None:
    llm = FakeLlm(["Why queues? ", "I'd score that a four. ", "More text. "])
    tts = FakeTts()
    runner = TurnRunner(llm, tts)
    events = await _run(
        runner, enforcer=enforcer, ctx=TurnContext(state="FOLLOW_UP"), seed=SEED, intent="x"
    )
    completed = events[-1]
    assert isinstance(completed, AgentCompleted)
    assert completed.text == "Why queues?"  # G3 — фраза с баллом обрезана, префикс сохранён
    assert "score" not in " ".join(tts.synthesized)  # G3
    assert completed.violations[0]["constraint_id"] == "I1-H3_no_scoring"  # G3
    assert completed.violations[0]["recovery"] == "truncate"


async def test_violation_on_first_sentence_regenerates(enforcer: ContractEnforcer) -> None:
    llm = ScriptedLlm([["Отлично! Расскажите ещё? "], ["Understood. ", "What was the impact? "]])
    runner = TurnRunner(llm, FakeTts())
    events = await _run(
        runner,
        enforcer=enforcer,
        ctx=TurnContext(state="CORE_QUEST"),
        seed=SEED,
        intent="ask impact",
    )
    completed = events[-1]
    assert isinstance(completed, AgentCompleted)
    assert completed.text == "Understood. What was the impact?"
    assert completed.fallback_used is False
    # second attempt got the strict regenerate hint
    assert "violated interview rules" in llm.calls[1][-1]["content"]
    assert "ask impact" in llm.calls[1][-1]["content"]
    assert completed.violations[0]["recovery"] == "regenerate"


async def test_double_failure_falls_back_to_seed(enforcer: ContractEnforcer) -> None:
    llm = ScriptedLlm([["I'd score that a four. "], ["Overall your performance was fine. "]])
    tts = FakeTts()
    runner = TurnRunner(llm, tts)
    events = await _run(
        runner, enforcer=enforcer, ctx=TurnContext(state="FOLLOW_UP"), seed=SEED, intent="x"
    )
    completed = events[-1]
    assert isinstance(completed, AgentCompleted)
    assert completed.fallback_used is True
    assert completed.text == SEED
    assert tts.synthesized == [SEED]  # nothing non-compliant was ever spoken
    assert len(completed.violations) == 2


async def test_empty_stream_falls_back(enforcer: ContractEnforcer) -> None:
    runner = TurnRunner(ScriptedLlm([[], []]), FakeTts())
    events = await _run(
        runner, enforcer=enforcer, ctx=TurnContext(state="CORE_QUEST"), seed=SEED, intent="x"
    )
    completed = events[-1]
    assert isinstance(completed, AgentCompleted)
    assert completed.fallback_used is True
    assert completed.violations[0]["constraint_id"] == "EMPTY_STREAM"


async def test_missing_question_appends_seed(enforcer: ContractEnforcer) -> None:
    llm = FakeLlm(["That architecture sounds like a reasonable choice for the workload. "])
    tts = FakeTts()
    runner = TurnRunner(llm, tts)
    events = await _run(
        runner, enforcer=enforcer, ctx=TurnContext(state="CORE_QUEST"), seed=SEED, intent="x"
    )
    completed = events[-1]
    assert isinstance(completed, AgentCompleted)
    assert completed.text.endswith(SEED)  # additive fix — nothing retracted
    assert tts.synthesized[-1] == SEED
    assert completed.violations[0]["constraint_id"] == "G1-H4_question_or_ack"
    assert completed.violations[0]["recovery"] == "append_seed_question"
