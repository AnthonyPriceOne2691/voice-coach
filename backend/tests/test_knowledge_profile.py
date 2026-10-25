"""Профиль кандидата покрывает всё портфолио и влезает в бюджет (docs 05, 20).

Почему это тест, а не «посмотреть глазами»: профиль уезжает в системный промпт
КАЖДОГО хода. Превышение бюджета не падает и не логируется — оно молча съедает
`num_ctx` 8192, вытесняя транскрипт и удлиняя prefill, то есть проявляется как
деградация latency, а не как ошибка. Пропавший проект не проявляется никак:
агент просто никогда о нём не спросит.
"""

import re
from pathlib import Path

import pytest

from app.config import REPO_ROOT
from app.knowledge.prompts import PromptLibrary

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
    # P2: работы осени 2026 — без них Генри знает Антона по состоянию на август.
    "SEO case-study platform",
    "Prospecting & outreach platform",
    "G connect",
    "RAG over a rulebook",
    "Quality contour",
]

#: P3: строки, которые были правдой до осени 2026 и перестали ею быть. Каждая —
#: факт, о котором Генри иначе спросит как о нынешнем.
STALE = (
    "building his own products",  # с июля — работа на клиентов, а не свои продукты
    "~3.0 s per turn",  # до первого звука ~1.3 s; 3.0 s — гейт, а не замер
    "~2 weeks",  # проект живёт с июля по октябрь
    "205 backend",  # замер 2026-10-17 — 213
    "24 design docs",  # нумерованных доков 21
)

#: P4: личное Генри узнаёт только из разговора и только то, что Антон скажет сам
#: (решение человека 2026-10-17). В профиль оно не пишется — профиль коммитится и
#: уходит в промпт каждого хода. Слова — с границами, чтобы «person» не ловил «son».
PRIVATE_MARKERS = (
    r"\bdaughter",
    r"\bson\b",
    r"\bwife\b",
    r"\bhusband\b",
    r"\bfamily\b",
    r"\bmarried\b",
    r"\bkids?\b",
    r"\bchild(?:ren)?\b",
)


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


#: Номер пункта списка («7. **G connect**») и ссылка «#2» — цифры, но не замер.
#: С 2026-08-12 профиль нумеровал проекты, и F3 был зелёным у ЛЮБОГО проекта по
#: номеру пункта: мутация 2026-10-17 (цифры G connect стёрты) прошла незамеченной.
_LIST_INDEX = re.compile(r"^\s*(?:\*\*)?\d+\.\s|#\d+", re.MULTILINE)


def test_every_project_carries_a_number(profile_text: str) -> None:
    """F3, P2: у каждого проекта есть цифра — иначе вопрос агента будет пустым."""
    blocks = {name: _LIST_INDEX.sub("", _block_for(profile_text, name)) for name in PORTFOLIO}
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
        assert secret not in profile_text, f"в промпте личный контакт: {secret}"  # F7


def test_profile_states_current_position(profile_text: str) -> None:
    """P1: Генри знает, кем Антон работает СЕЙЧАС, а не летом.

    «AI Automation Engineer» остаётся: это прежняя должность, и её же ждёт
    `test_prompts.py::test_real_repo_prompts_load` как признак инжекта.
    """
    for phrase in (
        "AI Delivery Lead",  # позиция CV от 2026-10-08
        "AI Automation Engineer",  # прежняя должность
        "self-employed since July 2026",
        "SEO agency",  # нынешняя клиентская работа
        "Western",  # продажа автоматизации западным агентствам
        "remote role",  # поиск удалённой работы
    ):
        assert phrase in profile_text, f"профиль не говорит о нынешнем положении: {phrase!r}"


def test_profile_drops_stale_facts(profile_text: str) -> None:
    """P3: устаревшие факты убраны, нынешние цифры на месте своих проектов."""
    left = [line for line in STALE if line in profile_text]
    assert left == [], f"в профиле остались устаревшие факты: {left}"
    assert "~1.3 s" in _block_for(profile_text, "Voice Interview Coach")
    assert "451" in _block_for(profile_text, "Local Web Agent")
    assert "frozen" in _block_for(profile_text, "Lash Try-On")


def test_profile_keeps_private_life_out(profile_text: str) -> None:
    """P4: семья и личное — только из разговоров, в профиль они не пишутся."""
    found = [m for m in PRIVATE_MARKERS if re.search(m, profile_text, re.IGNORECASE)]
    assert found == [], f"в профиле личное: {found}"
    assert not re.search(r"\bAlly\b", profile_text), "в профиле приватный семейный проект"


def test_profile_says_why_spoken_english_matters(profile_text: str) -> None:
    """P5: зачем Антону разговорный английский — о чём говорить и что тренировать."""
    for reason in ("discovery calls", "interviews", "voice-overs"):
        assert reason in profile_text, f"не названа причина учить английский: {reason!r}"


def test_new_projects_reach_both_prompts() -> None:
    """P6: работы осени доехали до собранных промптов интервью И разбора (L20)."""
    library = PromptLibrary(REPO_ROOT / "data" / "prompts", REPO_ROOT / "data" / "knowledge")
    for name, system in (
        ("interviewer", library.interviewer_system()),
        ("review", library.review_system("")),
    ):
        for project in ("G connect", "SEO case-study platform"):
            assert project in system, f"{project!r} не доехал до промпта {name}"


def _block_for(text: str, name: str) -> str:
    """Строки профиля, относящиеся к проекту: от его записи до пустой строки.

    Запись — строка с именем жирным (`**LinkBuilder**`), как в индексе портфолио.
    Раньше блок начинался с ПЕРВОГО упоминания имени, и 2026-10-17 им оказался
    HTML-комментарий шапки с датами замеров: F3 видел там цифры и зеленел по
    чужому блоку, а цифра самого проекта не проверялась вовсе. Первое упоминание
    осталось запасным путём — для профиля без жирных имён.
    """
    lines = text.splitlines()
    entry = (i for i, line in enumerate(lines) if f"**{name}**" in line)
    mention = (i for i, line in enumerate(lines) if name in line)
    start = next(entry, None)
    if start is None:
        start = next(mention)
    block: list[str] = []
    for line in lines[start:]:
        if not line.strip() and block:
            break
        block.append(line)
    return "\n".join(block)
