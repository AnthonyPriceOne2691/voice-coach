import pytest

from app.voice.transcribe import SttEmptyError, clean_transcript, transcribe_utterance
from tests.fakes import FakeDecoder, FakeStt


def test_clean_transcript_strips_whisper_artifacts() -> None:
    assert clean_transcript("[BLANK_AUDIO]") == ""
    assert clean_transcript("(wind blowing) Hello there [MUSIC]") == "Hello there"
    assert clean_transcript(" . , ") == ""
    assert clean_transcript("Hello.") == "Hello."


async def test_transcribe_happy_path() -> None:
    text = await transcribe_utterance(FakeDecoder(), FakeStt("I built a CRM tool"), b"webm")
    assert text == "I built a CRM tool"


async def test_single_word_is_valid() -> None:
    assert await transcribe_utterance(FakeDecoder(), FakeStt("Hello."), b"x") == "Hello."


async def test_junk_only_raises_stt_empty_with_raw() -> None:
    with pytest.raises(SttEmptyError) as excinfo:
        await transcribe_utterance(FakeDecoder(), FakeStt("[BLANK_AUDIO]"), b"x")
    assert excinfo.value.raw_transcript == "[BLANK_AUDIO]"
