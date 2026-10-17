"""Разговор с Генри через WS (D3a.1): что прозвучало, что записано, звалась ли модель.

Модель, STT и голос — фейки; контракт, сценарий тем и база — настоящие. Проверяется
то, что услышит человек, и то, что останется в базе, а не «функция вызвана».
"""

import json
import random
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.main import create_app
from app.orchestrator.talk import TalkOrchestrator, load_script
from app.voice.talk_flow import WINDOW_MAX, WINDOW_STEP, TalkFlow
from tests.fakes import FakeLlm, FakeStt
from tests.helpers import (
    PACE_TEMPLATES,
    drain_until_listening,
    fetch_talk,
    make_container,
    send_utterance,
)

SCRIPT = load_script(Path(__file__).resolve().parents[2] / "data" / "talk" / "talk.yaml")
OPENERS = {opener for openers in SCRIPT.topics.values() for opener in openers}
REPLY = ["That sounds fun! ", "What did you train today? "]


def _lines(messages: list[dict[str, Any]], role: str = "agent") -> list[str]:
    return [
        str(m["payload"]["text"])
        for m in messages
        if m["type"] == "transcript" and m["payload"]["role"] == role
    ]


def _until_turn_end(ws: Any) -> list[dict[str, Any]]:
    """Сообщения хода до его конца: сервер снова слушает — или сессия закрыта."""
    messages: list[dict[str, Any]] = []
    while not messages or not (
        messages[-1]["type"] == "session_ended"
        or (messages[-1]["type"] == "state" and messages[-1]["payload"]["value"] == "listening")
    ):
        messages.append(ws.receive_json())
    return messages


def _talk(tmp_path: Path, said: str) -> dict[str, Any]:
    """T1: открыть разговор, сказать одну реплику; сессия обязана быть записана в базе."""
    llm = FakeLlm(REPLY)
    container = make_container(tmp_path, llm, FakeStt(said))
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_talk", "payload": {}})
        started = ws.receive_json()
        opening = drain_until_listening(ws)
        send_utterance(ws)
        turn = _until_turn_end(ws)
    row = fetch_talk(container.settings.database_url, str(started["payload"]["session_id"]))
    assert row is not None
    return {
        "started": started,
        "opening": _lines(opening)[0],
        "henry": _lines(turn)[-1],
        "messages": opening + turn,
        "llm": llm,
        "said": said,
        "row": row,
    }


def _model_heard(result: dict[str, Any]) -> bool:
    return result["said"] in json.dumps(result["llm"].calls)


def test_start_talk_opens_with_a_greeting_and_a_topic_from_the_bank(tmp_path: Path) -> None:
    """T1: тему открытия выбирает код; сессия своя, не интервью."""
    result = _talk(tmp_path, "It was a slow day.")

    assert result["started"]["payload"]["session_kind"] == "talk"
    assert result["opening"].startswith(SCRIPT.lines["intro"])
    assert any(result["opening"].endswith(opener) for opener in OPENERS)
    assert result["row"].persona == "friend_mentor"
    states = [m["payload"] for m in result["messages"] if m["type"] == "state"]
    assert {s["session_kind"] for s in states} == {"talk"}
    assert {s["question_index"] for s in states} == {None}


@pytest.mark.parametrize(
    "said",
    ["I went to the gym this morning and it was packed.", "It was a slow day."],  # T2, T4
)
def test_talk_reaches_the_model_and_the_pace_stays(tmp_path: Path, said: str) -> None:
    """T2, T4: реплика — беседе; «slow» в рассказе темп не трогает."""
    result = _talk(tmp_path, said)

    assert result["henry"] == "".join(REPLY).strip()
    # Прогрев идёт фоновой задачей, поэтому ход ищется по системному промпту
    last_call = next(c for c in result["llm"].calls if c[0]["role"] == "system")
    assert last_call[-1] == {"role": "user", "content": said}  # сырая реплика, без обёртки
    assert PACE_TEMPLATES["pace_slower"] not in result["henry"]
    turns = json.loads(result["row"].transcript_json)
    assert [t["role"] for t in turns] == ["agent", "user", "agent"]


@pytest.mark.parametrize(
    ("said", "first_line", "question_back"),
    [
        ("Let's talk about something else.", "topic_switch", False),  # T3
        ("How's my English? Give me a score.", "no_grades", True),  # T6
        ("Can we switch to Russian?", "keep_english", True),  # T7
    ],
)
def test_requests_are_answered_by_code_not_by_the_model(
    tmp_path: Path, said: str, first_line: str, question_back: bool
) -> None:
    """T3, T6, T7: реплика из сценария; модель о ходе не знает."""
    result = _talk(tmp_path, said)

    assert result["henry"].startswith(SCRIPT.lines[first_line])
    assert not _model_heard(result)
    opener = result["opening"].removeprefix(SCRIPT.lines["intro"]).strip()
    assert result["henry"].endswith(opener) is question_back


def test_pace_request_in_talk_slows_down_and_repeats(tmp_path: Path) -> None:
    """T5: просьба по форме — мета-ход темпа, как в интервью."""
    result = _talk(tmp_path, "Could you speak a bit slower?")

    assert result["henry"] == f"{PACE_TEMPLATES['pace_slower']} {result['opening']}"
    assert not _model_heard(result)


def test_goodbye_ends_the_talk_as_completed(tmp_path: Path) -> None:
    """T8: прощание шаблоном, сессия закрыта и сохранена завершённой."""
    result = _talk(tmp_path, "Okay, I have to go. Bye, Henry!")

    assert result["henry"] == SCRIPT.lines["goodbye"]
    ended = [m["payload"] for m in result["messages"] if m["type"] == "session_ended"]
    assert ended and ended[0]["session_kind"] == "talk"
    assert result["row"].status == "completed"
    assert not _model_heard(result)


class NullRepo:
    async def create(self, talk_id: str, *, persona: str) -> None: ...
    async def checkpoint(self, *_: Any) -> None: ...
    async def finish(self, talk_id: str, *, status: str) -> None: ...


async def test_long_talk_sends_a_window_with_the_system_prompt_first() -> None:
    """T9: история разговора не вытесняет системный промпт из num_ctx (doc 20)."""
    talk = TalkOrchestrator(SCRIPT, rng=random.Random(1))
    flow = TalkFlow("t-1", talk, "SYSTEM", NullRepo())  # type: ignore[arg-type]
    await flow.start()
    firsts = []
    for i in range(40):
        await flow.on_user(f"I did thing number {i} today.")
        await flow.on_agent(f"Nice, thing {i}!", violations=[], fallback_used=False)
        messages = flow.messages
        assert messages[0] == {"role": "system", "content": "SYSTEM"}
        assert len(messages) - 1 <= WINDOW_MAX
        firsts.append(messages[1]["content"])

    assert messages[-1]["content"] == "Nice, thing 39!"
    # Окно сдвигается ступенькой: префикс для KV-кэша меняется раз в WINDOW_STEP
    # сообщений, а не на каждом ходе.
    assert len(set(firsts)) <= 1 + (2 * 40 + 1) // WINDOW_STEP


async def test_requests_stay_out_of_the_models_history() -> None:
    """T6, T7: отказ — не реплика беседы; модель не узнает о нём и на следующем ходе."""
    flow = TalkFlow("t-2", TalkOrchestrator(SCRIPT, rng=random.Random(2)), "SYSTEM", NullRepo())  # type: ignore[arg-type]
    await flow.start()
    before = list(flow.messages)

    await flow.on_user("How's my English? Give me a score.")
    await flow.on_spoken(SCRIPT.lines["no_grades"])

    assert flow.messages == before
    assert [t["state"] for t in flow.buffer.to_json_list()[-2:]] == ["REQUEST", "REQUEST"]
