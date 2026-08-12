"""PacedTts — the seam that carries a session's tempo to the voice (spec P1)."""

import pytest

from app.voice.tts_paced import PacedTts

from .fakes import FakeTts


@pytest.mark.asyncio
async def test_session_tempo_reaches_the_voice() -> None:
    inner = FakeTts()
    tts = PacedTts(inner, scale=1.15)

    await tts.synthesize("Hello.")

    assert inner.scales == [1.15]


@pytest.mark.asyncio
async def test_new_tempo_applies_from_the_very_next_synthesis() -> None:
    """Ровно то, на чём держится P1: подтверждение звучит УЖЕ новым темпом."""
    inner = FakeTts()
    tts = PacedTts(inner, scale=1.15)

    await tts.synthesize("Before.")
    tts.set_scale(1.30)
    await tts.synthesize("After.")

    assert inner.scales == [1.15, 1.30]
    assert tts.scale == 1.30


@pytest.mark.asyncio
async def test_explicit_argument_wins_over_the_session_tempo() -> None:
    inner = FakeTts()
    tts = PacedTts(inner, scale=1.15)

    await tts.synthesize("Fixed.", length_scale=1.0)

    assert inner.scales == [1.0]
    assert tts.scale == 1.15  # разовый аргумент не меняет темп сессии
