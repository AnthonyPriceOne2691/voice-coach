"""Правила памяти из данных (D3b): числа контракта и список «никогда».

Код берёт их из `data/contracts/`, а не держит копией: поле контракта, которого не
читает никто, обещает то, чего не исполняет никто (L73). Умолчаний нет — не хватает
поля, и загрузка падает, а не подставляет тихое число.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml

from app.contracts.spec import ContractError


class Category(StrEnum):
    """Чего память не хранит никогда (M-H4, инвариант 3 спеки)."""

    CONTACTS = "contacts"
    MONEY = "money"
    LEGAL = "legal"
    HEALTH = "health"
    FAMILY = "family"
    ALLY = "ally"


@dataclass(frozen=True)
class NeverStore:
    """M-H4: шаблоны по категориям из списка «никогда»."""

    patterns: tuple[tuple[Category, re.Pattern[str]], ...]

    def category(self, *texts: str) -> Category | None:
        """Первая категория, чей шаблон стоит хоть в одном тексте; `None` — чисто."""
        for category, pattern in self.patterns:
            if any(pattern.search(text) for text in texts):
                return category
        return None


@dataclass(frozen=True)
class MemoryRules:
    """Всё, что код памяти берёт из контракта."""

    max_memories: int  # M-H1: годных больше — первые в порядке модели
    min_quote_words: int  # M-H3
    text_words: tuple[int, int]  # M-H5: от и до
    follow_up_max_words: int  # M-H5
    repeat_share: float  # M-H6: столько общих значимых слов от меньшего набора — повтор
    never_store: NeverStore  # M-H4


def load_rules(contracts_dir: Path) -> MemoryRules:
    """Контракт памяти и его список «никогда» → правила; кривой контракт — ошибка."""
    path = contracts_dir / "memory.contract.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        hard = {str(rule["id"]).split("_", 1)[0]: rule for rule in data["invariants"]["hard"]}
        form = hard["M-H5"]
        return MemoryRules(
            max_memories=int(hard["M-H1"]["max_candidates"]),
            min_quote_words=int(hard["M-H3"]["min_quote_words"]),
            text_words=(int(form["text_min_words"]), int(form["text_max_words"])),
            follow_up_max_words=int(form["follow_up_max_words"]),
            repeat_share=float(hard["M-H6"]["max_shared"]),
            never_store=load_never_store(contracts_dir / str(hard["M-H4"]["patterns_file"])),
        )
    except ContractError:
        raise  # ошибка списка уже названа своей строкой
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError(f"{path.name}: правило без нужного поля — {exc!r}") from exc


def load_never_store(path: Path) -> NeverStore:
    """«категория: шаблон» построчно. Строка, которую нельзя прочесть, и категория без
    шаблонов роняют загрузку: молча пропущенная строка ослабила бы приватность."""
    patterns: list[tuple[Category, re.Pattern[str]]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            patterns.append(_entry(line))
        except (ValueError, re.error) as exc:
            raise ContractError(
                f"{path.name}:{number}: {line!r} — ожидается «категория: шаблон», "
                f"категории: {', '.join(Category)} ({exc})"
            ) from exc
    if missing := sorted(c.value for c in set(Category) - {category for category, _ in patterns}):
        raise ContractError(f"{path.name}: у категорий {missing} нет ни одного шаблона")
    return NeverStore(tuple(patterns))


def _entry(line: str) -> tuple[Category, re.Pattern[str]]:
    name, _, pattern = (part.strip() for part in line.partition(":"))
    if not pattern:
        # Пустой шаблон совпал бы с любым текстом — память молча перестала бы писаться.
        raise ValueError(f"пустой шаблон у категории {name!r}")
    return Category(name), re.compile(pattern, re.IGNORECASE)
