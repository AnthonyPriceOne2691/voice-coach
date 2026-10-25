"""Подсказка вслух после ответа по сути (D3a.2, talk-tips) — её говорит код по шаблону.

Что поправить, решено раньше и без модели (`orchestrator/tips.py`, заметка). Здесь —
когда и как это прозвучит:

* одна подсказка после ответа Генри и только к реплике этого хода;
* микрофон ждёт проверку не дольше конца ответа плюс `TIP_GRACE_S` (инвариант 2
  спеки). Конец ответа сервер знает сам — по длительности отправленного звука
  (`PlaybackClock`): клиент ставит чанки встык, и счёт идёт так же;
* не успела — подсказки в этом ходе нет, а проверка НЕ снимается: её заметка ещё
  ляжет в список, если кончится до следующей реплики (C17);
* текст — шаблон из `data/talk/talk.yaml` (`tips:`). Модель его не видит
  (инвариант 4): в историю разговора подсказка не попадает (`TalkFlow.on_tip`).
"""

import io
import time
import wave
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.voice.talk_checks import TalkChecks

#: Сколько после конца ответа микрофон ждёт проверку речи (спека D3a.2, инвариант 2).
TIP_GRACE_S = 1.5


@dataclass(frozen=True)
class Tip:
    """Что прозвучит и к какой заметке: после звука заметке ставится `spoken`."""

    line: str
    note: dict[str, Any]


def tip_line(note: Mapping[str, Any], templates: Mapping[str, str]) -> str:
    """Подсказка по заметке: лучший вариант и, если есть, причина — точку ставит шаблон."""
    better = str(note["better"]).strip().rstrip(".!?")
    why = str(note["why"]).strip().rstrip(".!?")
    if why:
        return templates["with_reason"].format(better=better, why=why)
    return templates["without_reason"].format(better=better)


def wav_seconds(wav: bytes) -> float:
    """Сколько клиент будет играть этот WAV — по его заголовку."""
    with wave.open(io.BytesIO(wav), "rb") as reader:
        return reader.getnframes() / reader.getframerate()


class PlaybackClock:
    """Когда у клиента доиграет звук текущей реплики — по часам сервера.

    `AudioQueue` ставит чанк в `max(сейчас, конец прежнего)`, и счёт здесь тот же.
    `final` закрывает реплику: следующую сервер шлёт, только когда человек заговорил,
    то есть когда клиент эту уже доиграл. Сеть и декодирование на локальной машине —
    миллисекунды; их покрывает срок.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self.ends_at = 0.0

    def sent(self, wav: bytes, *, final: bool) -> None:
        if wav:
            self.ends_at = max(self._clock(), self.ends_at) + wav_seconds(wav)
        if final:
            self.ends_at = 0.0


class TalkTips:
    """Подсказка к ходу: заметка проверки, успевшей к сроку, — в реплику по шаблону."""

    def __init__(self, checks: TalkChecks, templates: Mapping[str, str]) -> None:
        self._checks = checks
        self._templates = templates

    async def after_reply(self, *, audio_ends_at: float) -> Tip | None:
        """Подсказка, если проверка кончится к концу звука ответа + `TIP_GRACE_S`."""
        note = await self._checks.note_by(audio_ends_at + TIP_GRACE_S)
        return None if note is None else Tip(tip_line(note, self._templates), note)
