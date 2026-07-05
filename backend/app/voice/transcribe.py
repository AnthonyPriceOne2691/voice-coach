"""User utterance -> clean transcript (decode + STT + junk filter)."""

import re
import tempfile
from pathlib import Path

from app.common.interfaces import AudioDecoder, SpeechToText

# whisper hallucination artifacts on silence/noise: [BLANK_AUDIO], (wind blowing), *music* ...
_JUNK_SEGMENTS = re.compile(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*")
_HAS_WORD = re.compile(r"[A-Za-z0-9]")  # digits are speech too ("5 to 1" is a metric)


class SttEmptyError(RuntimeError):
    """User utterance produced no usable transcript (doc 15: STT_EMPTY)."""

    def __init__(self, raw_transcript: str) -> None:
        super().__init__(f"no usable speech (heard: {raw_transcript!r})")
        self.raw_transcript = raw_transcript


def clean_transcript(raw: str) -> str:
    """Strip non-speech artifacts; empty result means nothing usable was said."""
    text = _JUNK_SEGMENTS.sub(" ", raw)
    words = [w for w in text.split() if _HAS_WORD.search(w)]
    return " ".join(words)


async def transcribe_utterance(
    decoder: AudioDecoder,
    stt: SpeechToText,
    audio: bytes,
    *,
    min_words: int = 1,
) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "utterance.wav"
        await decoder.to_wav(audio, wav_path)
        raw = await stt.transcribe(wav_path)
    text = clean_transcript(raw)
    if len(text.split()) < min_words:
        raise SttEmptyError(raw)
    return text
