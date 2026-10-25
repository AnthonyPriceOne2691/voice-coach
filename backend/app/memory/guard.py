"""Что может попасть в память Генри (D3b): модель предлагает, решает код.

После разговора модель предлагает до трёх кандидатов JSON (вызов — memory-write);
сохранить ли кандидата, решает этот модуль — без модели и целиком: негодный
отбрасывается, а не правится (I1-H6). Правила M-H1…M-H7 — `memory.contract.yaml`,
числа и список «никогда» — оттуда же (`rules.py`). Разбор слов, дословный поиск и
латиница — те же, что у заметок к речи (`orchestrator/tips.py`).
"""

import json
import logging
import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from app.memory.rules import Category, MemoryRules
from app.orchestrator.tips import latin_only, locate, words

logger = logging.getLogger(__name__)


class MemoryKind(StrEnum):
    PLAN = "plan"  # что впереди
    UPDATE = "update"  # что происходит в работе и жизни
    TOPIC = "topic"  # о чём говорили, чем он увлечён


class Reason(StrEnum):
    """Почему кандидат не стал заметкой — в лог числом, без текста."""

    MALFORMED = "malformed"  # M-H1: не той формы
    OVER_LIMIT = "over_limit"  # M-H1: годных больше трёх
    NOT_ENGLISH = "not_english"  # M-H2
    NOT_SAID = "not_said"  # M-H3: цитата короче трёх слов или её нет в его репликах
    UNRELATED = "unrelated"  # M-H3: текст не делит с цитатой ни одного значимого слова
    NEVER_STORE = "never_store"  # M-H4
    FORM = "form"  # M-H5
    REPEAT = "repeat"  # M-H6
    CONTRACT = "contract"  # M-H7


@dataclass(frozen=True)
class Rejection:
    reason: Reason
    category: Category | None = None  # только у NEVER_STORE


@dataclass(frozen=True)
class Candidate:
    """Кандидат модели; принятый — та же форма, цитата в написании распознанного."""

    kind: MemoryKind
    text: str
    follow_up: str
    evidence: str


@dataclass(frozen=True)
class Sifted:
    kept: list[Candidate]
    rejected: list[Rejection]


#: Служебные слова не делают два текста «о том же» (M-H3, M-H6). Словарь, а не модель,
#: как признаки ответа в `orchestrator/interview.py`.
_STOPWORDS = frozenset(
    """
    a an the i me my mine myself you your yours yourself we us our ours he him his she her hers
    it its they them their theirs this that these those there here am is are was were be been
    being have has had do does did will would shall should can could may might must and or but
    so if then than because as while when where which who whom whose what how why to of in on
    at by for from with about into onto over under up down out off through after before during
    until again not no just very really also too still already even only quite some any all
    each every both few more most much many lot
    """.split()  # noqa: SIM905 -- словарь читается строкой, литерал дал бы 124 строки по слову
)
_CLITIC = re.compile(r"'(?:s|re|ve|ll|d|m)$")
#: «you …» и его сокращения: «Last time you mentioned that {text}» звучит с каждым.
_SECOND_PERSON = frozenset({"you", "you're", "you've", "you'll", "you'd", "your"})
#: Конец предложения внутри текста. Точка после «St», «Mr» или одной заглавной —
#: сокращение, а не граница: «You moved to St. Petersburg.» — одно предложение.
_SENTENCE_BREAK = re.compile(r"(?<!\b[A-Z][a-z])(?<!\b[A-Z])[.!][\"')\]]?\s")
_KIND_NAMES = tuple(MemoryKind)
_FIELDS = ("text", "follow_up", "evidence")


def parse_candidates(raw: str) -> list[Candidate | Rejection] | Rejection:
    """M-H1: ответ модели → кандидаты. Не-JSON — отказ всего ответа (повтор решает
    memory-write); кривой кандидат — отказ только ему."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return Rejection(Reason.MALFORMED)
    items = data.get("memories") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return Rejection(Reason.MALFORMED)
    return [_candidate(item) for item in items]


def decide(
    candidate: Candidate,
    *,
    said: Sequence[str],
    known: Sequence[str],
    rules: MemoryRules,
    passes_contract: Callable[[str], bool],
) -> Candidate | Rejection:
    """Станет ли кандидат заметкой: `said` — его реплики беседы этого разговора, `known` —
    тексты заметок, с которыми нельзя совпасть (сохранённые и принятые из этого ответа)."""
    refused = _language_and_form(candidate, rules)
    if refused is not None:
        return refused
    found = _his_words(candidate, said, rules)
    if isinstance(found, Rejection):
        return found
    fragment, utterance = found
    # M-H4 — и над репликой, где стоит цитата: цитата, обрезанная до безобидного
    # хвоста («so I barely slept»), иначе вымарывала бы категорию руками модели (K7).
    category = rules.never_store.category(
        candidate.text, candidate.follow_up, candidate.evidence, utterance
    )
    if category is not None:
        return Rejection(Reason.NEVER_STORE, category)
    if not (passes_contract(candidate.text) and passes_contract(candidate.follow_up)):  # M-H7
        return Rejection(Reason.CONTRACT)
    if any(is_repeat(candidate.text, other, rules.repeat_share) for other in known):  # M-H6
        return Rejection(Reason.REPEAT)
    return replace(candidate, evidence=fragment)


def sift(
    raw: str,
    *,
    said: Sequence[str],
    saved: Sequence[str],
    rules: MemoryRules,
    passes_contract: Callable[[str], bool],
) -> Sifted | Rejection:
    """Ответ модели → заметки к записи (первые годные в порядке модели, K10) и отказы, в
    лог — числом. Не-JSON — отказ всего ответа: повтор и `failed` решает memory-write."""
    parsed = parse_candidates(raw)
    if isinstance(parsed, Rejection):
        return parsed
    kept: list[Candidate] = []
    rejected: list[Rejection] = []
    for item in parsed:
        known = [*saved, *(memory.text for memory in kept)]
        verdict = (
            item
            if isinstance(item, Rejection)
            else decide(item, said=said, known=known, rules=rules, passes_contract=passes_contract)
        )
        if isinstance(verdict, Rejection):
            rejected.append(verdict)
        elif len(kept) < rules.max_memories:
            kept.append(verdict)
        else:
            rejected.append(Rejection(Reason.OVER_LIMIT))  # M-H1
    _log(rejected)
    return Sifted(kept, rejected)


def significant(text: str) -> set[str]:
    """Значимые слова (M-H3, M-H6): без служебных и без хвоста сокращения."""
    found: set[str] = set()
    for word in words(text):
        base = _CLITIC.sub("", word)
        if not word.endswith("n't") and base not in _STOPWORDS:
            found.add(base)
    return found


def is_repeat(text: str, other: str, share: float) -> bool:
    """M-H6: доля общих значимых слов — от МЕНЬШЕГО набора. От большего или от
    объединения короткий пересказ длинной заметки прошёл бы как новая (K12)."""
    mine, theirs = significant(text), significant(other)
    smaller = min(len(mine), len(theirs))
    return smaller > 0 and len(mine & theirs) / smaller >= share


def _candidate(item: object) -> Candidate | Rejection:
    if not isinstance(item, dict):
        return Rejection(Reason.MALFORMED)
    kind, *fields = (item.get(key) for key in ("kind", *_FIELDS))
    if kind not in _KIND_NAMES or not all(isinstance(f, str) and f.strip() for f in fields):
        return Rejection(Reason.MALFORMED)
    text, follow_up, evidence = (str(f).strip() for f in fields)
    return Candidate(MemoryKind(str(kind)), text, follow_up, evidence)


def _language_and_form(candidate: Candidate, rules: MemoryRules) -> Rejection | None:
    # M-H2 — ДО разбора слов: `words` видит только латиницу, и текст на кириллице
    # иначе выглядел бы «коротким», то есть получил бы неверную причину (L82).
    fields = (candidate.text, candidate.follow_up, candidate.evidence)
    if not all(latin_only(field) for field in fields):
        return Rejection(Reason.NOT_ENGLISH)
    if not _well_formed(candidate, rules):  # M-H5
        return Rejection(Reason.FORM)
    return None


def _well_formed(candidate: Candidate, rules: MemoryRules) -> bool:
    text, question = candidate.text, candidate.follow_up
    told = words(text)
    low, high = rules.text_words
    return (
        bool(told)
        and told[0] in _SECOND_PERSON
        and low <= len(told) <= high
        and "?" not in text
        and _SENTENCE_BREAK.search(text) is None
        and question.endswith("?")
        and len(words(question)) <= rules.follow_up_max_words
    )


def _his_words(
    candidate: Candidate, said: Sequence[str], rules: MemoryRules
) -> tuple[str, str] | Rejection:
    """M-H3: (цитата в написании распознанного, реплика с ней) или отказ."""
    quoted = words(candidate.evidence)
    enough = len(quoted) >= rules.min_quote_words
    found = next(((f, u) for u in said if enough and (f := locate(u, quoted)) is not None), None)
    if found is None:
        return Rejection(Reason.NOT_SAID)
    if not significant(candidate.text) & significant(found[0]):
        return Rejection(Reason.UNRELATED)
    return found


def _log(rejected: Sequence[Rejection]) -> None:
    """Причина, категория и число — без текста: иначе отброшенное легло бы в лог."""
    for (reason, category), count in Counter((r.reason, r.category) for r in rejected).items():
        logger.info(
            "memory candidates rejected",
            extra={"reason": reason.value, "category": category, "count": count},
        )
