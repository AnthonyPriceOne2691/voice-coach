from pathlib import Path

import pytest

from app.voice.pipeline import (
    AgentCompleted,
    AgentSentence,
    LlmParams,
    SttEmptyError,
    UserTranscribed,
    VoiceTurnPipeline,
    clean_transcript,
)
from tests.fakes import FakeLlm, FakeStt, FakeTts

PARAMS = LlmParams(model="m", temperature=0.7, max_tokens=100)


def test_clean_transcript_strips_whisper_artifacts() -> None:
    assert clean_transcript("[BLANK_AUDIO]") == ""
    assert clean_transcript("(wind blowing) Hello there [MUSIC]") == "Hello there"
    assert clean_transcript(" . , ") == ""
    assert clean_transcript("Hello.") == "Hello."


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


async def test_junk_only_transcript_raises_stt_empty() -> None:
    pipeline = VoiceTurnPipeline(FakeStt("[BLANK_AUDIO]"), FakeLlm(["x"]), FakeTts())
    with pytest.raises(SttEmptyError) as excinfo:
        await _run(pipeline)
    assert excinfo.value.raw_transcript == "[BLANK_AUDIO]"


async def test_single_word_is_a_valid_turn() -> None:
    # "Hello" must not be rejected — live-session lesson
    llm = FakeLlm(["Hi. "])
    pipeline = VoiceTurnPipeline(FakeStt("Hello."), llm, FakeTts())
    events = await _run(pipeline)
    assert isinstance(events[0], UserTranscribed)
    assert events[0].text == "Hello."


async def test_trailing_partial_sentence_is_flushed() -> None:
    llm = FakeLlm(["One. ", "and a tail without period"])
    pipeline = VoiceTurnPipeline(FakeStt(), llm, FakeTts())
    events = await _run(pipeline)
    sentences = [e.text for e in events if isinstance(e, AgentSentence)]
    assert sentences == ["One.", "and a tail without period"]
