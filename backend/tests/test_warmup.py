"""Прогрев голосового цикла: что получают распознавание и модель (M8–M10).

Прогрев исполнялся в каждой WS-сессии сьюта, а утверждал о нём один тест — про
содержимое сообщений. Мутационный гейт на диффе talk-screen (2026-10-23) убил 7
мутантов `voice/warmup.py` из 63: формат файла для whisper, один токен генерации,
температура и обработка отказов могли поменяться молча.
"""

import io
import logging
import wave
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.common.interfaces import ChatMessage
from app.voice.warmup import warm_up

MODEL = "qwen2.5:14b-instruct"


class RecordingStt:
    """Читает файл прогрева ВО ВРЕМЯ вызова: после него каталог уже удалён."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.wavs: list[bytes] = []

    async def transcribe(self, wav_path: Path) -> str:
        if self.fail:
            raise RuntimeError("whisper-cli is missing")
        self.wavs.append(wav_path.read_bytes())
        return ""


class RecordingLlm:
    """Пишет параметры вызова и считает, сколько кусков стрима из него вычитали."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []
        self.pulled = 0

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if self.fail:
            raise ConnectionError("ollama is down")
        for token in ("Hello", ",", " there"):
            self.pulled += 1
            yield token


async def test_speech_warmup_is_one_second_of_silence_in_whisper_format() -> None:
    """M8: whisper получает WAV моно, 16 бит, 16 000 Гц — секунду тишины."""
    stt = RecordingStt()
    await warm_up(stt, RecordingLlm(), model=MODEL)
    assert len(stt.wavs) == 1
    with wave.open(io.BytesIO(stt.wavs[0])) as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16000
        assert wav.getnframes() == 16000
        assert set(wav.readframes(16000)) == {0}


async def test_model_warmup_sends_the_session_prefix_for_one_token() -> None:
    """M9: сообщения сессии, её модель, температура 0 и ровно один токен генерации."""
    llm = RecordingLlm()
    session: list[ChatMessage] = [
        {"role": "system", "content": "You are Henry."},
        {"role": "assistant", "content": "Hi, I'm Henry."},
    ]
    await warm_up(RecordingStt(), llm, model=MODEL, messages=session)
    assert llm.calls == [{"messages": session, "model": MODEL, "temperature": 0.0, "max_tokens": 1}]


async def test_model_warmup_without_session_messages_says_hi() -> None:
    """M9: без сообщений сессии прогрев грузит веса одной репликой «hi»."""
    llm = RecordingLlm()
    await warm_up(RecordingStt(), llm, model=MODEL)
    assert llm.calls[0]["messages"] == [{"role": "user", "content": "hi"}]


async def test_model_warmup_stops_after_the_first_chunk() -> None:
    """M9: прогреву нужен префикс в кэше, а не ответ — стрим читается до первого куска."""
    llm = RecordingLlm()
    await warm_up(RecordingStt(), llm, model=MODEL)
    assert llm.pulled == 1


async def test_failed_speech_warmup_still_warms_the_model(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """M10: отказ распознавания пишется в лог с причиной и не отменяет прогрев модели."""
    llm = RecordingLlm()
    with caplog.at_level(logging.WARNING, logger="app.voice.warmup"):
        await warm_up(RecordingStt(fail=True), llm, model=MODEL)
    assert len(llm.calls) == 1
    [record] = caplog.records
    assert record.getMessage() == "STT warmup failed"
    assert record.exc_info is not None
    assert record.exc_info[0] is RuntimeError  # причина — сам отказ whisper


async def test_failed_model_warmup_is_logged_not_raised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """M10: недоступная модель не роняет сессию — только строка в логе с причиной."""
    with caplog.at_level(logging.WARNING, logger="app.voice.warmup"):
        await warm_up(RecordingStt(), RecordingLlm(fail=True), model=MODEL)
    [record] = caplog.records
    assert record.getMessage() == "LLM warmup failed"
    assert record.exc_info is not None
    assert record.exc_info[0] is ConnectionError  # причина — сам отказ модели
