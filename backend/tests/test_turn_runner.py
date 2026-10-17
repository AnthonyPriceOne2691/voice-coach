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
    # R2: second attempt got the strict regenerate hint — без правил экзаменатора (L24)
    hint = llm.calls[1][-1]["content"]
    assert "broke a rule" in hint
    assert "ask impact" in hint
    for leftover in INTERVIEW_ERA_LEFTOVERS:
        assert leftover not in hint
    assert completed.violations[0]["recovery"] == "regenerate"


#: Остатки интервьюерского текста перегенерации до 2026-10-17. Подсказка одна на
#: оба режима, и каждая из этих строк там чужая: в разборе лимит 5 предложений, а
#: похвала и совет — его работа; в интервью запрет на подсказки снят 2026-08-12.
INTERVIEW_ERA_LEFTOVERS = (
    "interview rules",
    "No coaching",
    "praise, or scoring",  # хвост запрета целиком: само слово «praise» законно в намерении
    "Max 3 sentences",
    "One question OR",
)


async def test_regenerate_hint_carries_no_interview_era_rules() -> None:
    """Перегенерация в разборе не навязывает ему правила интервью-экзаменатора.

    L24: запрет живёт там, где его исполняет машина. Инверсия Генри в тренера
    (2026-08-12) сняла запреты в контракте, но текст перегенерации в коде остался
    прежним — и на любом нарушении требовал «No coaching, praise» и «Max 3
    sentences». В разборе, где похвала и совет и есть работа, это урезало бы ответ.
    """
    review = ContractEnforcer(load_contract(CONTRACTS_DIR / "review.contract.yaml"))
    llm = ScriptedLlm(
        [["Отлично, давай разберём! "], ["That answer was strong. ", "Lead with the metric. "]]
    )
    runner = TurnRunner(llm, FakeTts())
    events = await _run(
        runner,
        enforcer=review,
        ctx=TurnContext(state="REVIEW", question_count=6),
        seed=SEED,
        intent="praise the answer and suggest a sharper opening",
    )
    completed = events[-1]
    assert isinstance(completed, AgentCompleted)
    assert completed.violations[0]["recovery"] == "regenerate"
    hint = llm.calls[1][-1]["content"]
    for leftover in INTERVIEW_ERA_LEFTOVERS:  # R1
        assert leftover not in hint, f"в подсказке перегенерации остался {leftover!r}"
    assert "praise the answer and suggest a sharper opening" in hint  # намерение сохранено
    assert "English only" in hint  # общее правило всех трёх контрактов остаётся


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
