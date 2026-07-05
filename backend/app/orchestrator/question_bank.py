"""Question bank loading — questions are data, not code (doc 18)."""

import random
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Question:
    id: str
    theme: str
    seed: str
    first: bool = False


def load_bank(path: Path) -> list[Question]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    questions = [
        Question(
            id=str(q["id"]),
            theme=str(q.get("theme", "")),
            seed=str(q["seed"]),
            first=bool(q.get("first", False)),
        )
        for q in data.get("questions", [])
    ]
    if not questions:
        raise ValueError(f"empty question bank: {path}")
    return questions


def pick_session_pool(bank: list[Question], *, count: int, rng: random.Random) -> list[Question]:
    """First-marked question opens the session; the rest are sampled (doc 04: 5-6 per session)."""
    first = [q for q in bank if q.first][:1] or bank[:1]
    rest = [q for q in bank if q.id != first[0].id]
    sampled = rng.sample(rest, k=min(count - 1, len(rest)))
    return first + sampled
