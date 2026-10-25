"""Speech-pace policy: deterministic, no LLM (I1-H6, same nature as follow-up policy).

Piper's `length_scale`: 1.0 is the voice's native tempo, larger is slower. The
user asks in words ("speak slower"), the orchestrator turns that into a number —
the model is never asked to classify, because classification is structure.
"""

import re
from enum import StrEnum

#: Настройка, в которой живёт темп речи между сессиями (doc 15).
PACE_SETTING = "speech_length_scale"

#: Одна просьба = одна ступень. Пять ступеней от заметно быстрее до заметно
#: медленнее; подтверждено человеком 2026-08-12 вместе со спекой.
PACE_STEP = 0.15
PACE_FASTEST = 0.85
PACE_SLOWEST = 1.60

#: Просьбой считается только КОРОТКАЯ реплика. Это единственное, что отделяет
#: «speak slower» от ответа, в котором просто упомянута скорость: без порога
#: содержательный ответ стал бы мета-ходом и пропал бы из транскрипта. Цена
#: ложного срабатывания здесь выше цены пропуска, поэтому порог низкий.
MAX_REQUEST_WORDS = 12


class PaceRequest(StrEnum):
    SLOWER = "slower"
    FASTER = "faster"


#: Таблица формулировок. Живёт в коде, а не в `data/`, потому что это политика
#: распознавания, а не произносимый текст (см. decisions.md): `data/` в этом
#: проекте хранит промпты, контракты и вопросы — то, что читает модель.
#:
#: ⚠ Порядок — часть правила, а не оформление. «That's too slow» содержит
#: «slow», и общий шаблон замедления перехватил бы просьбу УСКОРИТЬСЯ, выдав
#: ровно обратное желаемому. Поэтому составные формулировки идут до общих.
_PATTERNS: tuple[tuple[re.Pattern[str], PaceRequest], ...] = (
    (re.compile(r"\btoo slow\b"), PaceRequest.FASTER),
    (re.compile(r"\bspeed up\b"), PaceRequest.FASTER),
    (re.compile(r"\bfaster\b"), PaceRequest.FASTER),
    (re.compile(r"\btoo fast\b"), PaceRequest.SLOWER),
    (re.compile(r"\bnot so fast\b"), PaceRequest.SLOWER),
    (re.compile(r"\bslow down\b"), PaceRequest.SLOWER),
    (re.compile(r"\bslow(?:er|ly)?\b"), PaceRequest.SLOWER),
    (re.compile(r"\btake it easy\b"), PaceRequest.SLOWER),
)


#: Разговор (D3a) — другой класс данных. В интервью ответы длинные, и короткая
#: фраза со словом «slow» почти всегда просьба; в разговоре короткая фраза — норма,
#: и «It was a slow day» — рассказ (L33). Здесь просьба узнаётся по ФОРМЕ:
#: глагол речи, обращение к Генри или реплика целиком.
_TALK = r"(?:speak|talk|go|say it)(?: a (?:bit|little))?"
_TO_HENRY = (
    r"\byou(?:'re| are)?(?: speaking| talking| going| speak| talk)?(?: a bit| a little)? too"
)
_ALONE = r"^\W*(?:please )?(?:{})(?: a (?:bit|little))?(?:,? please)?\W*$"
_CASUAL_PATTERNS: tuple[tuple[re.Pattern[str], PaceRequest], ...] = (
    (re.compile(rf"\b{_TALK} (?:slower|more slowly)\b"), PaceRequest.SLOWER),
    (re.compile(r"\b(?:can|could|would|will) you (?:please )?slow down\b"), PaceRequest.SLOWER),
    (re.compile(_ALONE.format("slower|slow down")), PaceRequest.SLOWER),
    (re.compile(_TO_HENRY + r" fast\b"), PaceRequest.SLOWER),
    (re.compile(rf"\b{_TALK} (?:faster|quicker|more quickly)\b"), PaceRequest.FASTER),
    (re.compile(r"\b(?:can|could|would|will) you (?:please )?speed up\b"), PaceRequest.FASTER),
    (re.compile(_ALONE.format("faster|speed up")), PaceRequest.FASTER),
    (re.compile(_TO_HENRY + r" slow(?:ly)?\b"), PaceRequest.FASTER),
)


def detect(text: str, *, casual: bool = False) -> PaceRequest | None:
    """Return the pace request in this utterance, or None if it is a normal answer.

    `casual=True` — разговор (D3a): засчитывается только форма просьбы.
    """
    if len(text.split()) > MAX_REQUEST_WORDS:
        return None
    lowered = text.lower().replace("’", "'")
    for pattern, request in _CASUAL_PATTERNS if casual else _PATTERNS:
        if pattern.search(lowered):
            return request
    return None


#: Какую реплику подтверждения произнести. Ключ — (просьба, уже на границе):
#: на границе Генри обязан сказать, что дальше некуда, иначе «Sure» прозвучит
#: обещанием изменения, которого не будет.
_ACK_TEMPLATES = {
    (PaceRequest.SLOWER, False): "pace_slower",
    (PaceRequest.SLOWER, True): "pace_slowest",
    (PaceRequest.FASTER, False): "pace_faster",
    (PaceRequest.FASTER, True): "pace_fastest",
}


def ack_template(request: PaceRequest, *, at_limit: bool) -> str:
    """Имя шаблона подтверждения из `data/prompts/templates/` для этой просьбы."""
    return _ACK_TEMPLATES[request, at_limit]


def apply(current: float, request: PaceRequest) -> tuple[float, bool]:
    """Return (new scale, already at the limit).

    The flag matters: at the limit Henry has to say so. Silently confirming a
    change that did not happen is the same defect class as a silent clamp — the
    user hears "sure" and keeps waiting for a difference that will never come.
    """
    step = PACE_STEP if request is PaceRequest.SLOWER else -PACE_STEP
    clamped = min(PACE_SLOWEST, max(PACE_FASTEST, round(current + step, 2)))
    return clamped, clamped == round(current, 2)


def in_range(value: float) -> bool:
    return PACE_FASTEST <= value <= PACE_SLOWEST
