from pathlib import Path

import pytest

from app.voice.pipeline import (
    AgentCompleted,
    AgentSentence,
    LlmParams,
    SttEmptyError,
    UserTranscribed,
    VoiceTurnPipeline,
)
from tests.fakes import FakeLlm, FakeStt, FakeTts

PARAMS = LlmParams(model="m", temperature=0.7, max_tokens=100)


async def _run(pipeline: VoiceTurnPipeline) -> list[object]:
    return [
        e
        async for e in pipeline.run_turn(
            Path("/tmp/fake.wav"), [{"role": "system", "content": "sys"}], PARAMS
        )
    ]


async def test_happy_path_event_order_and_sentence_gating() -> None:
    llm = FakeLlm(["Got it. ", "Why did you ", "choose queues? "])
    tts = FakeTts()
    pipeline = VoiceTurnPipeline(FakeStt(), llm, tts)

    events = await _run(pipeline)

    assert isinstance(events[0], UserTranscribed)
    sentences = [e for e in events if isinstance(e, AgentSentence)]
    assert [s.text for s in sentences] == ["Got it.", "Why did you choose queues?"]
    assert [s.index for s in sentences] == [0, 1]
    # TTS was called per sentence, not once for the whole turn
    assert tts.synthesized == ["Got it.", "Why did you choose queues?"]
    completed = events[-1]
    assert isinstance(completed, AgentCompleted)
    assert completed.text == "Got it. Why did you choose queues?"


async def test_user_message_appended_to_history() -> None:
    llm = FakeLlm(["Okay. "])
    pipeline = VoiceTurnPipeline(FakeStt("my answer text"), llm, FakeTts())
    await _run(pipeline)
    assert llm.last_messages is not None
    assert llm.last_messages[-1] == {"role": "user", "content": "my answer text"}
    assert llm.last_messages[0]["role"] == "system"


async def test_short_transcript_raises_stt_empty() -> None:
    pipeline = VoiceTurnPipeline(FakeStt("uh"), FakeLlm(["x"]), FakeTts())
    with pytest.raises(SttEmptyError):
        await _run(pipeline)


async def test_trailing_partial_sentence_is_flushed() -> None:
    llm = FakeLlm(["One. ", "and a tail without period"])
    pipeline = VoiceTurnPipeline(FakeStt(), llm, FakeTts())
    events = await _run(pipeline)
    sentences = [e.text for e in events if isinstance(e, AgentSentence)]
    assert sentences == ["One.", "and a tail without period"]
