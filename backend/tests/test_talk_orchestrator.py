"""Разговор с Генри: структуру держит код — тема, просьбы к Генри, прощание (D3a).

Каждая просьба проверяется с ОБЕИХ сторон: реплика, которая похожа на просьбу
словом, но не формой, обязана остаться беседой. В разговоре короткая фраза —
норма, и детектор «по слову» молча превращал бы рассказ в мета-ход (L33).
"""

import itertools
import random
from pathlib import Path

import pytest

from app.contracts.enforcer import ContractEnforcer, TurnContext
from app.contracts.spec import load_contract
from app.orchestrator.talk import TalkOrchestrator, TalkScript, TalkState, load_script

REPO_ROOT = Path(__file__).resolve().parents[2]

LINES = {
    "intro": "Hi, I'm Henry.",
    "topic_switch": "Sure, let's switch.",
    "goodbye": "Bye for now!",
    "time_up": "Let's stop here for today.",
    "no_grades": "No grades here.",
    "keep_english": "Let's keep it in English.",
    "fallback": "Tell me more.",
}
TOPICS = {"day": ("How's your day?",), "food": ("Cooked anything good?",), "trip": ("Any trips?",)}


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _talk(clock: Clock | None = None) -> TalkOrchestrator:
    script = TalkScript(lines=LINES, topics=TOPICS)
    return TalkOrchestrator(script, rng=random.Random(7), clock=clock or Clock())


def test_intro_greets_and_opens_a_topic_from_the_bank() -> None:
    """T1: тему открытия выбирает код, и это вопрос из банка."""
    plan = _talk().intro_plan()

    assert plan.state is TalkState.INTRO
    assert plan.lines[0] == LINES["intro"]
    assert plan.lines[1] in [opener for openers in TOPICS.values() for opener in openers]


@pytest.mark.parametrize(
    "said",
    [
        "Let's talk about something else.",
        "Can we change the topic?",
        "I don't know what to talk about.",
        "Something else, please.",
    ],
)
def test_topic_change_picks_a_topic_not_heard_yet(said: str) -> None:
    """T3: смена темы — без модели, и тема новая, а не та же."""
    talk = _talk()
    opened = talk.intro_plan().lines[1]

    plan = talk.on_user(said)

    assert plan.state is TalkState.TOPIC
    assert plan.lines[0] == LINES["topic_switch"]
    assert plan.lines[1] != opened
    assert plan.remember  # модель обязана знать, о чём теперь спросили


def test_topics_never_run_out() -> None:
    talk = _talk()
    talk.intro_plan()
    openers = [talk.on_user("Change the topic, please.").lines[1] for _ in range(7)]

    assert all(a != b for a, b in itertools.pairwise(openers))


@pytest.mark.parametrize(
    ("said", "line"),
    [
        ("How's my English? Give me a score.", "no_grades"),  # T6
        ("Can you rate my English?", "no_grades"),
        ("What's my level?", "no_grades"),
        ("Can we switch to Russian?", "keep_english"),  # T7
    ],
)
def test_requests_to_henry_get_a_line_and_the_question_back(said: str, line: str) -> None:
    """T6, T7: отказ шаблоном, вопрос возвращается, модель о ходе не знает."""
    talk = _talk()
    talk.intro_plan()

    plan = talk.on_user(said)

    assert plan.state is TalkState.REQUEST
    assert plan.lines == (LINES[line],)
    assert plan.repeat_question
    assert not plan.remember


@pytest.mark.parametrize(
    "said",
    ["Okay, I have to go. Bye, Henry!", "Bye!", "That's all for today.", "See you next time."],
)
def test_goodbye_ends_the_talk(said: str) -> None:
    """T8: прощание — решение кода, сессия кончается."""
    talk = _talk()
    talk.intro_plan()

    plan = talk.on_user(said)

    assert plan.state is TalkState.GOODBYE
    assert plan.lines == (LINES["goodbye"],)
    assert plan.finished and talk.finished


@pytest.mark.parametrize(
    "said",
    [
        "It was a slow day.",  # T4
        "Trains are faster than buses here.",  # T4
        "I said goodbye to my friend at the station.",
        "I have to go to the dentist tomorrow.",
        "My English teacher rates essays every week.",
        "We talked about something else at lunch.",
        "I want to talk about something else that happened.",
        "I went to the gym this morning and it was packed.",  # T2
    ],
)
def test_words_without_the_shape_of_a_request_stay_talk(said: str) -> None:
    """T2, T4: слово «bye», «rate» или «something else» ещё не просьба."""
    talk = _talk()
    talk.intro_plan()

    plan = talk.on_user(said)

    assert plan.state is TalkState.CHAT
    assert plan.lines == ()
    assert plan.seed == LINES["fallback"]


def test_after_the_time_limit_henry_says_goodbye() -> None:
    clock = Clock()
    talk = _talk(clock)
    talk.intro_plan()
    assert talk.on_user("It was fine.").state is TalkState.CHAT

    clock.now = 20 * 60
    plan = talk.on_user("And then we went home.")

    assert plan.state is TalkState.GOODBYE
    assert plan.lines == (LINES["time_up"],)


def test_the_real_script_has_every_line_and_a_bank_of_topics() -> None:
    """T1: банк не меньше 10 повседневных тем, у каждой есть открывающий вопрос."""
    script = load_script(REPO_ROOT / "data" / "talk" / "talk.yaml")

    assert set(LINES) <= set(script.lines)
    assert len(script.topics) >= 10
    assert all(
        openers and all(o.endswith("?") for o in openers) for openers in script.topics.values()
    )


def test_every_scripted_line_survives_the_talk_contract() -> None:
    """Реплики сценария звучат дословно, мимо енфорсера, — значит, судятся здесь."""
    script = load_script(REPO_ROOT / "data" / "talk" / "talk.yaml")
    talk = ContractEnforcer(load_contract(REPO_ROOT / "data" / "contracts" / "talk.contract.yaml"))
    lines = [*script.lines.values(), *(o for openers in script.topics.values() for o in openers)]

    rejected = [line for line in lines if talk.start_turn(TurnContext(state="CHAT")).feed(line)]
    assert rejected == []
