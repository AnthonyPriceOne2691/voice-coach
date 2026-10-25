"""Дыхание между предложениями — тишина в самих байтах аудио.

Почему на бэкенде, а не в очереди воспроизведения: `AudioQueue` ставит чанки
встык (`nextStartTime = startAt + buffer.duration`) и ничего не знает о речи —
таким он и должен остаться. Пауза, приехавшая в WAV, работает в любом клиенте
и не требует браузерной приёмки.

Почему ПЕРЕД звуком, а не после: тишина после последнего предложения — это
задержка перед открытием микрофона, то есть плата на каждом ходе за паузу,
которую никто не услышит.
"""

import io
import wave

#: Дыхание — доли секунды (`sentence_pause_ms` = 350). Дольше — ошибка настройки, а
#: не тишина: нули ложатся прямо в память, и 350 000 s (мутант `* 1000` вместо
#: `/ 1000`) дали 15 GB — раннер CI на 16 GB снял шаг мутаций SIGTERM (2026-10-25).
MAX_LEAD_IN_S = 5.0


def lead_in(wav: bytes, seconds: float) -> bytes:
    """Return the same WAV with `seconds` of silence prepended.

    Формат сохраняется байт в байт: тишина — нулевые сэмплы той же частоты и
    разрядности, а не смена длительности звучащей части.
    """
    if seconds <= 0:
        return wav
    if seconds > MAX_LEAD_IN_S:
        raise ValueError(
            f"lead-in {seconds:g} s exceeds {MAX_LEAD_IN_S:g} s: check sentence_pause_ms"
        )
    with wave.open(io.BytesIO(wav)) as source:
        params = source.getparams()
        frames = source.readframes(source.getnframes())

    silence = b"\x00" * (int(seconds * params.framerate) * params.sampwidth * params.nchannels)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(params.nchannels)
        out.setsampwidth(params.sampwidth)
        out.setframerate(params.framerate)
        out.writeframes(silence + frames)
    return buffer.getvalue()
