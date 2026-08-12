"""Дыхание между предложениями — тишина в самих байтах (spec E2, E3)."""

import io
import wave

import pytest

from app.voice.prosody import lead_in

from .fakes import fake_wav, wav_duration_s

RATE = 22050


def test_silence_is_prepended_and_lasts_exactly_the_pause() -> None:
    """E2: длительность выросла РОВНО на паузу, ни больше ни меньше."""
    original = fake_wav(frames=RATE)  # ровно секунда

    padded = lead_in(original, 0.35)

    assert wav_duration_s(original) == pytest.approx(1.0)
    assert wav_duration_s(padded) == pytest.approx(1.35, abs=0.001)


def test_format_survives_and_the_result_is_readable() -> None:
    """E3: это WAV того же формата, а не «звук стал длиннее»."""
    original = fake_wav(frames=RATE // 2)

    padded = lead_in(original, 0.35)

    with wave.open(io.BytesIO(original)) as before, wave.open(io.BytesIO(padded)) as after:
        assert after.getframerate() == before.getframerate()
        assert after.getsampwidth() == before.getsampwidth()
        assert after.getnchannels() == before.getnchannels()
        # добавленное — НУЛЕВЫЕ сэмплы в начале, а не что-нибудь ещё
        head = after.readframes(int(0.35 * after.getframerate()))
        assert head == b"\x00" * len(head)


def test_the_pause_goes_before_the_sound_not_after() -> None:
    """Разница слышна на микрофоне: пауза в конце — ожидание на каждом ходе."""
    speech = fake_wav(frames=RATE // 10)
    # различимый «звук»: ненулевой хвост
    with wave.open(io.BytesIO(speech)) as reader:
        params = reader.getparams()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(params.nchannels)
        writer.setsampwidth(params.sampwidth)
        writer.setframerate(params.framerate)
        writer.writeframes(b"\x10\x10" * (RATE // 10))
    loud = buffer.getvalue()

    padded = lead_in(loud, 0.2)

    with wave.open(io.BytesIO(padded)) as reader:
        frames = reader.readframes(reader.getnframes())
    silence_len = int(0.2 * RATE) * 2
    assert frames[:silence_len] == b"\x00" * silence_len
    assert frames[silence_len:] == b"\x10\x10" * (RATE // 10)  # звук цел и в конце


@pytest.mark.parametrize("seconds", [0.0, -1.0])
def test_no_pause_means_untouched_bytes(seconds: float) -> None:
    original = fake_wav(frames=RATE // 4)
    assert lead_in(original, seconds) is original
