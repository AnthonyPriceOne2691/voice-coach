"""Speech-pace policy: deterministic, no LLM (I1-H6, same nature as follow-up policy).

Piper's `length_scale`: 1.0 is the voice's native tempo, larger is slower. The
user asks in words ("speak slower"), the orchestrator turns that into a number —
the model is never asked to classify, because classification is structure.
"""

import re
from enum import StrEnum

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


def detect(text: str) -> PaceRequest | None:
    """Return the pace request in this utterance, or None if it is a normal answer."""
    if len(text.split()) > MAX_REQUEST_WORDS:
        return None
    lowered = text.lower()
    for pattern, request in _PATTERNS:
        if pattern.search(lowered):
            return request
    return None


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
