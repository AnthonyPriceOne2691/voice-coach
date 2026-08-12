"""Question bank loading — questions are data, not code (doc 18)."""

import random
from dataclasses import dataclass
from enum import StrEnum
from itertools import zip_longest
from pathlib import Path

import yaml


class QuestionKind(StrEnum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"


@dataclass(frozen=True)
class Question:
    id: str
    theme: str
    seed: str
    first: bool = False
    #: Класс задаётся ФАЙЛОМ банка, а не строкой вопроса: банк и есть класс, и
    #: восемь одинаковых полей рассинхронизируются раньше, чем понадобится
    #: смешанный файл (decisions.md).
    kind: QuestionKind = QuestionKind.TECHNICAL


def load_bank(path: Path) -> list[Question]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    kind = QuestionKind(str(data.get("kind", QuestionKind.TECHNICAL)))
    questions = [
        Question(
            id=str(q["id"]),
            theme=str(q.get("theme", "")),
            seed=str(q["seed"]),
            first=bool(q.get("first", False)),
            kind=kind,
        )
        for q in data.get("questions", [])
    ]
    if not questions:
        raise ValueError(f"empty question bank: {path}")
    return questions


def pick_session_pool(
    technical: list[Question],
    behavioral: list[Question],
    *,
    count: int,
    rng: random.Random,
) -> list[Question]:
    """Открывающий вопрос, затем классы СТРОГО через один (doc 04).

    Чередование детерминированное, а не «случайно N из count»: случайная выборка
    регулярно даёт три behavioral подряд, и сессия перестаёт тренировать
    ПЕРЕКЛЮЧЕНИЕ между режимами речи — ровно то, ради чего классы и смешаны.
    Случаен только выбор вопросов внутри класса.
    """
    first = _opening_question(technical or behavioral)
    rest_technical = [q for q in technical if q.id != first.id]
    slots = max(0, count - 1)
    # Хвост чередуется как behavioral, technical, behavioral, … — открывающий
    # вопрос технический, поэтому первым в хвосте идёт behavioral.
    soft_slots = (slots + 1) // 2
    hard_slots = slots // 2
    soft = _sample(behavioral, soft_slots, rng)
    hard = _sample(rest_technical, hard_slots, rng)
    interleaved = [q for pair in zip_longest(soft, hard) for q in pair if q is not None]
    return [first, *interleaved]


def _opening_question(bank: list[Question]) -> Question:
    marked = [q for q in bank if q.first]
    return marked[0] if marked else bank[0]


def _sample(bank: list[Question], k: int, rng: random.Random) -> list[Question]:
    return rng.sample(bank, k=min(k, len(bank)))
