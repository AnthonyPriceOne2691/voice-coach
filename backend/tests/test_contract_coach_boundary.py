"""Граница «помогать можно, оценивать нельзя» (docs 09, 13).

Решение человека 2026-08-12: Генри — добрый тренер-помощник, задача снять
барьер, а не давить. До этого дня контракт `I1-H2_no_coaching` резал подсказки
ДО озвучки: модель могла согласиться помочь, а пользователь этого не слышал.

Граница проходит не по тону — тон машиной не проверяется (doc 13, I1-S1
prompt-level only), — а по конкретным конструкциям: **баллы, рубрики и
итоговый разбор** остаются работой Mode 2 и debrief.

Тест проверяет ОБА направления: пропускает разрешённое и режет запрещённое.
Односторонний был бы зелёным при любом контракте, включая пустой.
"""

import pytest

from app.config import REPO_ROOT
from app.contracts.enforcer import ContractEnforcer, TurnContext
from app.contracts.spec import load_contract

CONTRACTS = REPO_ROOT / "data" / "contracts"


@pytest.fixture(scope="module")
def enforcer() -> ContractEnforcer:
    return ContractEnforcer(load_contract(CONTRACTS / "interview.contract.yaml"))


def _speak(enforcer: ContractEnforcer, sentence: str) -> object | None:
    """Пропустить фразу через per-sentence гейт — как перед озвучкой."""
    turn = enforcer.start_turn(TurnContext(state="FOLLOW_UP", question_count=8))
    return turn.feed(sentence)


# Фразы подобраны так, чтобы задевать ИМЕННО те паттерны, которые старый
# контракт резал (`interview_forbidden.txt`): иначе тест был бы зелёным и до
# правки, то есть не сторожил бы ничего (урок L12 — сторож проверяется в обе
# стороны).
ALLOWED = [
    pytest.param("You should open with the metric, then the architecture.", id="G1-подсказка"),
    pytest.param("Great answer — you led with the trade-off.", id="G2-похвала"),
    pytest.param("Try saying it in one sentence first.", id="G1-наталкивание"),
]

BLOCKED = [
    pytest.param("I'd score that answer 3 out of 5.", id="G3-баллы"),
    pytest.param("Overall your performance today was solid.", id="G4-итоговый разбор"),
]


@pytest.mark.parametrize("sentence", ALLOWED)
def test_help_is_allowed(enforcer: ContractEnforcer, sentence: str) -> None:
    """G1/G2: помощь — работа Генри, а не нарушение."""
    assert _speak(enforcer, sentence) is None, (  # G1, G2
        f"контракт срезал помощь: {sentence!r} — это и есть барьер, который сняли"
    )


@pytest.mark.parametrize("sentence", BLOCKED)
def test_scoring_stays_out_of_the_interview(enforcer: ContractEnforcer, sentence: str) -> None:
    """G3/G4: оценка живёт в Mode 2 и debrief, иначе тренироваться негде."""
    violation = _speak(enforcer, sentence)
    assert violation is not None, f"оценка прошла в интервью: {sentence!r}"  # G3, G4


def test_untouched_invariants_still_hold(enforcer: ContractEnforcer) -> None:
    """G5: английский-only и лимит предложений границей не затронуты."""
    assert _speak(enforcer, "Расскажи про архитектуру.") is not None  # G5 — не английский
    turn = enforcer.start_turn(TurnContext(state="FOLLOW_UP", question_count=8))
    assert turn.feed("One. ") is None
    assert turn.feed("Two. ") is None
    assert turn.feed("Three. ") is None
    assert turn.feed("Four. ") is not None  # G5 — четвёртое предложение
