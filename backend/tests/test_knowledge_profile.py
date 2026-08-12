"""Профиль кандидата покрывает всё портфолио и влезает в бюджет (docs 05, 20).

Почему это тест, а не «посмотреть глазами»: профиль уезжает в системный промпт
КАЖДОГО хода. Превышение бюджета не падает и не логируется — оно молча съедает
`num_ctx` 8192, вытесняя транскрипт и удлиняя prefill, то есть проявляется как
деградация latency, а не как ошибка. Пропавший проект не проявляется никак:
агент просто никогда о нём не спросит.
"""

from pathlib import Path

import pytest

from app.knowledge.prompts import PromptLibrary

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE = REPO_ROOT / "data" / "knowledge" / "profile_condensed.md"

# doc 20, Mode 1: condensed profile <= 1500 токенов при num_ctx 8192.
PROFILE_TOKEN_BUDGET = 1500
# doc 20: «1 токен ~ 0.75 англ. слова». Оценка по символам (4 симв./токен)
# грубее, но НЕ занижает на англоязычном тексте — а занижение здесь опаснее
# завышения: оно пропустило бы превышение бюджета.
CHARS_PER_TOKEN = 4

PORTFOLIO = [
    "LinkBuilder",
    "Voice Interview Coach",
    "Local Web Agent",
    "Lash Try-On",
    "Event Content System",
]


@pytest.fixture(scope="module")
def profile_text() -> str:
    return PROFILE.read_text(encoding="utf-8")


def test_profile_covers_whole_portfolio(profile_text: str) -> None:
    missing = [name for name in PORTFOLIO if name not in profile_text]
    assert missing == [], f"проекты не видны агенту: {missing}"  # F1


def test_profile_fits_token_budget(profile_text: str) -> None:
    estimated = len(profile_text) / CHARS_PER_TOKEN
    assert estimated <= PROFILE_TOKEN_BUDGET, (  # F2
        f"профиль ~{estimated:.0f} токенов при потолке {PROFILE_TOKEN_BUDGET} "
        f"(doc 20): лишнее вытеснит транскрипт из num_ctx молча"
    )


def test_every_project_carries_a_number(profile_text: str) -> None:
    """F3: у каждого проекта есть цифра — иначе вопрос агента будет пустым."""
    blocks = {name: _block_for(profile_text, name) for name in PORTFOLIO}
    without = [name for name, block in blocks.items() if not any(c.isdigit() for c in block)]
    assert without == [], f"проекты без единой проверяемой цифры: {without}"  # F3


def test_profile_reaches_the_interviewer_prompt(tmp_path: Path) -> None:
    """F4: знание доезжает до собранного промпта, а не просто лежит в файле."""
    library = PromptLibrary(REPO_ROOT / "data" / "prompts", REPO_ROOT / "data" / "knowledge")
    system = library.interviewer_system()
    assert "{{profile_condensed}}" not in system  # F4 — плейсхолдер подставлен
    assert "Lash Try-On" in system  # F4 — непрофильный проект доехал


def test_profile_has_no_personal_contacts(profile_text: str) -> None:
    """Промпт уезжает в транскрипты на диск; контакты агенту для интервью не нужны."""
    for secret in ("@gmail.com", "AnthonyPriceOne", "linkedin.com"):
        assert secret not in profile_text, f"в промпте личный контакт: {secret}"


def _block_for(text: str, name: str) -> str:
    """Строки профиля, относящиеся к проекту: от его упоминания до пустой строки."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if name in line)
    block: list[str] = []
    for line in lines[start:]:
        if not line.strip() and block:
            break
        block.append(line)
    return "\n".join(block)
