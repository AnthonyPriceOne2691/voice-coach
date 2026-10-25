"""Заметки к речи Антона в разговоре (D3a.2): модель предлагает, решает код.

Модель после ответа Генри возвращает ОДНОГО кандидата строгим JSON (схема ниже
ограничивает выборку Ollama). Всё остальное — здесь, без модели:

* фрагмент обязан дословно стоять в распознанном тексте: whisper мог ослышаться, а
  поправлять несказанное нельзя (C6). Сверка — по словам, без регистра, пунктуации
  и вида апострофа; в заметку идёт фрагмент КАК ОН РАСПОЗНАН, а не как его
  процитировала модель;
* вариант обязан менять слова, а не регистр и запятые;
* вариант проходит контракт разговора — тот же енфорсер, что режет реплики Генри
  (английский, никаких оценок);
* причина — до пяти слов и тоже через контракт; не прошла — заметка остаётся без
  причины, а не пропадает;
* та же поправка в этом разговоре второй раз не записывается (C7).

Что считать ошибкой и что бедной речью, решает просьба к модели
(`data/prompts/language_check.txt`), а не этот модуль: словарь «плоских слов» в
коде вырождался бы в «поправлять всегда» на каждом «good» (L35).
"""

import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.contracts.enforcer import ContractEnforcer, TurnContext

#: Ответ модели ограничен этой схемой: ровно один кандидат и никакой прозы.
CANDIDATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["none", "error", "style"]},
        "said": {"type": "string"},
        "better": {"type": "string"},
        "why": {"type": "string"},
    },
    "required": ["kind", "said", "better", "why"],
}

#: Длиннее — это уже пересказ реплики, а не поправка фрагмента.
MAX_FRAGMENT_WORDS = 20
MAX_WHY_WORDS = 5

_WORD = re.compile(r"[A-Za-z0-9]+(?:['’‘][A-Za-z0-9]+)*")


class NoteKind(StrEnum):
    ERROR = "error"
    STYLE = "style"


class Rejection(StrEnum):
    """Почему кандидат не стал заметкой — в журнал, чтобы отказ был виден."""

    NONE = "none"  # модель ничего не нашла — штатный исход
    MALFORMED = "malformed"
    NOT_SAID = "not_said"  # C6: фрагмента нет в распознанном
    UNCHANGED = "unchanged"  # вариант меняет только регистр и пунктуацию
    TOO_LONG = "too_long"
    CONTRACT = "contract"  # вариант не проходит контракт разговора
    REPEAT = "repeat"  # C7: такая поправка уже была


@dataclass(frozen=True)
class Candidate:
    kind: NoteKind
    said: str
    better: str
    why: str


def contract_gate(enforcer: ContractEnforcer) -> Callable[[str], bool]:
    """Проходит ли текст контракт разговора — тот же, что режет реплики Генри."""

    def passes(text: str) -> bool:
        return enforcer.start_turn(TurnContext(state="CHAT")).feed(text) is None

    return passes


def parse_candidate(raw: str) -> Candidate | Rejection:
    """Ответ модели → кандидат; всё, что не схема, — отказ, а не исключение."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return Rejection.MALFORMED
    if not isinstance(data, dict):
        return Rejection.MALFORMED
    kind = data.get("kind")
    if kind == "none":
        return Rejection.NONE
    fields = [data.get(key) for key in ("said", "better", "why")]
    if kind not in ("error", "style") or not all(isinstance(f, str) for f in fields):
        return Rejection.MALFORMED
    said, better, why = (str(f).strip() for f in fields)
    if not said or not better:
        return Rejection.MALFORMED
    return Candidate(NoteKind(kind), said, better, why)


def words(text: str) -> list[str]:
    """Слова для сверки: без регистра, пунктуации и вида апострофа; общие с памятью (D3b)."""
    return [_normal(m.group(0)) for m in _WORD.finditer(text)]


def decide(
    candidate: Candidate,
    utterance: str,
    *,
    seen: Iterable[Mapping[str, Any]],
    passes_contract: Callable[[str], bool],
) -> dict[str, Any] | Rejection:
    """Станет ли кандидат заметкой — и в каком виде она запишется."""
    said_words, better_words = words(candidate.said), words(candidate.better)
    fragment = locate(utterance, said_words)
    if fragment is None:
        return Rejection.NOT_SAID
    # Контракт — ДО сравнения слов: `words` видит только латиницу, и вариант на
    # кириллице иначе выглядел бы «пустым», то есть «не меняющим слов».
    if not _english(candidate.better, passes_contract):
        return Rejection.CONTRACT
    if not better_words or better_words == said_words:
        return Rejection.UNCHANGED
    if max(len(said_words), len(better_words)) > MAX_FRAGMENT_WORDS:
        return Rejection.TOO_LONG
    if any(_same_fix(note, said_words, better_words) for note in seen):
        return Rejection.REPEAT
    return {
        "kind": candidate.kind.value,
        "said": fragment,
        "better": candidate.better,
        "why": _reason(candidate.why, passes_contract),
        "spoken": False,
    }


def _normal(word: str) -> str:
    return word.lower().replace("’", "'").replace("‘", "'")


def locate(utterance: str, needle: list[str]) -> str | None:
    """Фрагмент реплики, совпавший по словам, — в её собственном написании."""
    tokens = list(_WORD.finditer(utterance))
    size = len(needle)
    if not size:
        return None
    for start in range(len(tokens) - size + 1):
        window = tokens[start : start + size]
        if [_normal(m.group(0)) for m in window] == needle:
            return utterance[window[0].start() : window[-1].end()]
    return None


def _same_fix(note: Mapping[str, Any], said: list[str], better: list[str]) -> bool:
    return words(str(note.get("said", ""))) == said or words(str(note.get("better", ""))) == better


def latin_only(text: str) -> bool:
    """Все буквы — латиница: I3-H1 режет только кириллицу, а иероглифы (утечка, уже
    виденная у R1 в переводах, L55) и любой третий алфавит прошли бы его насквозь."""
    return all(ch.isascii() for ch in text if ch.isalpha())


def _english(text: str, passes_contract: Callable[[str], bool]) -> bool:
    """Контракт разговора И латиница."""
    return latin_only(text) and passes_contract(text)


def _reason(why: str, passes_contract: Callable[[str], bool]) -> str:
    if not why or len(words(why)) > MAX_WHY_WORDS or not _english(why, passes_contract):
        return ""
    return why
