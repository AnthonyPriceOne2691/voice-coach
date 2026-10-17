"""Talk with Henry (D3a): code owns the conversation's structure, the model its wording.

The same split as the interview (I1-H6, L23): the greeting, the opening topic, a
topic change, the goodbye and the end after the time limit are decided here,
deterministically; the model only phrases its replies in between. Requests to
Henry himself are caught here too — before the model — by the SHAPE of a request,
not by a keyword: short casual turns are the norm in a conversation, and «I said
goodbye to my friend» is a story, not the end of the session (L33).
"""

import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from app.orchestrator import meta_request

#: Мягкий потолок разговора: дальше Генри прощается на следующем ходе. Конец —
#: решение кода, а не модели; кнопка End и «bye» работают раньше.
TALK_LIMIT_S = 20 * 60

#: Просьба — короткая реплика; длинная — рассказ, даже если в ней «bye» или «rate».
MAX_REQUEST_WORDS = 14

#: Намерение хода беседы — им же модель поправляют при повторе (`TurnRunner`).
CHAT_INTENT = (
    "reply as his friend to what he just said: react to it, add a short thought of "
    "your own, and ask one natural question back"
)

REQUIRED_LINES = (
    "intro",
    "topic_switch",
    "goodbye",
    "time_up",
    "no_grades",
    "keep_english",
    "fallback",
)


class TalkState(StrEnum):
    INTRO = "INTRO"
    CHAT = "CHAT"
    TOPIC = "TOPIC"
    REQUEST = "REQUEST"
    GOODBYE = "GOODBYE"


class Ask(StrEnum):
    GOODBYE = "goodbye"
    GRADE = "grade"
    TOPIC = "topic"
    LANGUAGE = "language"


#: ⚠ Каждый шаблон — форма просьбы, а не слово: «I have to go to the dentist» и
#: «My teacher rates essays» короткие, но это рассказ (отрицательные примеры —
#: в test_talk_orchestrator.py).
_PATTERNS: tuple[tuple[re.Pattern[str], Ask], ...] = (
    (
        re.compile(r"^\W*(?:ok(?:ay)?|well|alright|right|so)?\W*(?:bye|goodbye|good night)\b"),
        Ask.GOODBYE,
    ),
    (re.compile(r"(?<!said )\b(?:bye|goodbye)(?:,? henry)?\W*$"), Ask.GOODBYE),
    (re.compile(r"\bi (?:have|need|'ve got|got) to go(?: now)?\W*$"), Ask.GOODBYE),
    (re.compile(r"\b(?:that's|that is) (?:all|it|enough) for (?:today|now)\b"), Ask.GOODBYE),
    (re.compile(r"\blet's (?:stop|finish|end|wrap up)(?: here| now| for today)?\W*$"), Ask.GOODBYE),
    (re.compile(r"\b(?:see|talk to) you (?:later|soon|tomorrow|next time)\W*$"), Ask.GOODBYE),
    (re.compile(r"\b(?:rate|score|grade|assess|evaluate) (?:my|me)\b"), Ask.GRADE),
    (re.compile(r"\bhow(?:'s| is| good is) my english\b"), Ask.GRADE),
    (re.compile(r"\bwhat(?:'s| is) my (?:english )?(?:level|score|grade|mark)\b"), Ask.GRADE),
    (re.compile(r"\bgive me (?:a|your) (?:score|grade|mark|rating)\b"), Ask.GRADE),
    (re.compile(r"\b(?:talk|chat|speak) about something else\W*$"), Ask.TOPIC),
    (re.compile(r"\b(?:change|switch) (?:the )?(?:topic|subject)\b"), Ask.TOPIC),
    (re.compile(r"\bi (?:don't|do not) know what to (?:talk|say|speak) about\b"), Ask.TOPIC),
    (re.compile(r"^\W*something else(?:,? please)?\W*$"), Ask.TOPIC),
)


def classify(text: str) -> Ask | None:
    """Просьба к Генри в этой реплике — или None, если это беседа."""
    if len(text.split()) > MAX_REQUEST_WORDS:
        return None
    lowered = text.lower().replace("’", "'")
    for pattern, ask in _PATTERNS:
        if pattern.search(lowered):
            return ask
    asked = meta_request.detect(text)  # «switch to Russian», «how would you rate that»
    if asked is meta_request.MetaRequest.LANGUAGE:
        return Ask.LANGUAGE
    return Ask.GRADE if asked is meta_request.MetaRequest.SCORE else None


@dataclass(frozen=True)
class TalkScript:
    """Что Генри говорит сам, без модели, и банк тем — из `data/talk/talk.yaml`."""

    lines: dict[str, str]
    topics: dict[str, tuple[str, ...]]


def load_script(path: Path) -> TalkScript:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    lines = {str(k): str(v) for k, v in (data.get("lines") or {}).items()}
    topics = {str(k): tuple(map(str, v or ())) for k, v in (data.get("topics") or {}).items()}
    missing = [name for name in REQUIRED_LINES if not lines.get(name)]
    if missing or not topics or not all(topics.values()):
        raise ValueError(f"{path}: talk script incomplete — lines missing {missing}")
    return TalkScript(lines=lines, topics=topics)


@dataclass(frozen=True)
class TalkPlan:
    state: TalkState
    #: Непусто — реплику говорит код, модель не вызывается.
    lines: tuple[str, ...] = ()
    #: После отказа вернуть последний вопрос Генри (как мета-ход интервью).
    repeat_question: bool = False
    #: Попадает ли обмен в историю модели: смена темы — да, отказ и прощание — нет.
    remember: bool = True
    seed: str = ""
    instruction: str = CHAT_INTENT
    #: Ход разговора не отвечает ни на какой вопрос интервью; поля нужны общей
    #: записи транскрипта (`SessionFlow`), как у разбора.
    question_id: str | None = None
    question_kind: str | None = None

    @property
    def finished(self) -> bool:
        return self.state is TalkState.GOODBYE


class TalkOrchestrator:
    def __init__(
        self,
        script: TalkScript,
        *,
        rng: random.Random,
        clock: Callable[[], float] = time.monotonic,
        limit_s: float = TALK_LIMIT_S,
    ) -> None:
        self._script = script
        self._rng = rng
        self._clock = clock
        self._limit_s = limit_s
        self._started = clock()
        self._topics: list[str] = []
        self.phase = TalkState.INTRO

    @property
    def finished(self) -> bool:
        return self.phase is TalkState.GOODBYE

    def snapshot(self) -> dict[str, Any]:
        return {"phase": self.phase.value, "topics": list(self._topics)}

    def intro_plan(self) -> TalkPlan:
        return TalkPlan(TalkState.INTRO, lines=(self._line("intro"), self._next_opener()))

    def on_user(self, text: str) -> TalkPlan:
        plan = self._plan_for(classify(text))
        self.phase = plan.state
        return plan

    def _plan_for(self, ask: Ask | None) -> TalkPlan:
        if ask is Ask.GOODBYE:
            return TalkPlan(TalkState.GOODBYE, lines=(self._line("goodbye"),), remember=False)
        if self._clock() - self._started >= self._limit_s:
            return TalkPlan(TalkState.GOODBYE, lines=(self._line("time_up"),), remember=False)
        if ask is Ask.TOPIC:
            return TalkPlan(
                TalkState.TOPIC, lines=(self._line("topic_switch"), self._next_opener())
            )
        if ask is not None:  # оценка или другой язык: отказ и вопрос назад
            line = self._line("no_grades" if ask is Ask.GRADE else "keep_english")
            return TalkPlan(TalkState.REQUEST, lines=(line,), repeat_question=True, remember=False)
        return TalkPlan(TalkState.CHAT, seed=self._line("fallback"))

    def _next_opener(self) -> str:
        """Тема, которой ещё не было; банк пройден — по кругу, но не та же подряд."""
        fresh = [t for t in self._script.topics if t not in self._topics]
        if not fresh:
            fresh = [t for t in self._script.topics if t != self._topics[-1]] or [self._topics[-1]]
        topic = self._rng.choice(fresh)
        self._topics.append(topic)
        return self._rng.choice(self._script.topics[topic])

    def _line(self, name: str) -> str:
        return self._script.lines[name]
