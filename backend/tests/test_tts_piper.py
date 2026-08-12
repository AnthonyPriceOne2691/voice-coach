"""PiperTts: темп доезжает до самого синтеза, а не останавливается на обёртке.

`FakeTts` доказать этого не может в принципе — он запишет любое число. Здесь
подставлен фальшивый голос Piper'а, и проверяется то, что реально уходит в
`SynthesisConfig`: именно эта строка — единственный адрес, по которому темп
превращается в звук (spec P1, plan §2).
"""

import io
import wave
from pathlib import Path
from typing import Any

import pytest

from app.voice.tts_piper import PiperTts


class FakeVoice:
    """Двойник `PiperVoice`: пишет тишину и запоминает конфиг синтеза."""

    def __init__(self) -> None:
        self.configs: list[Any] = []

    def synthesize_wav(self, text: str, wav_file: wave.Wave_write, syn_config: Any) -> None:
        self.configs.append(syn_config)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * len(text))


def _loaded(voice: FakeVoice, *, length_scale: float) -> PiperTts:
    tts = PiperTts(Path("/nonexistent/voice.onnx"), length_scale=length_scale)
    tts._voice = voice
    return tts


@pytest.mark.asyncio
async def test_configured_tempo_reaches_synthesis_config() -> None:
    voice = FakeVoice()
    tts = _loaded(voice, length_scale=1.15)

    await tts.synthesize("Hello.")

    assert voice.configs[0].length_scale == 1.15


@pytest.mark.asyncio
async def test_per_call_tempo_overrides_the_configured_one() -> None:
    """Ровно этот путь использует PacedTts, когда пользователь просит помедленнее."""
    voice = FakeVoice()
    tts = _loaded(voice, length_scale=1.15)

    await tts.synthesize("Slower now.", length_scale=1.60)
    await tts.synthesize("And back.")

    assert [c.length_scale for c in voice.configs] == [1.60, 1.15]


@pytest.mark.asyncio
async def test_result_is_a_readable_wav() -> None:
    tts = _loaded(FakeVoice(), length_scale=1.0)

    data = await tts.synthesize("Some words here.")

    with wave.open(io.BytesIO(data)) as wav:
        assert wav.getframerate() == 16000
        assert wav.getnframes() > 0
