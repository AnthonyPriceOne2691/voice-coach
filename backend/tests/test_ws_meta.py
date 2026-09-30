"""Просьба к Генри как мета-ход: отказ шаблоном, вопрос цел, модель не знает о ходе.

Проверяется то, что увидит человек (что прозвучало) и что осталось в базе
(состояние интервью не сдвинулось), а не «функция вызвана».
"""

import json
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from app.main import create_app
from app.storage.turns import META_STATE
from tests.fakes import FakeLlm, FakeStt
from tests.helpers import (
    META_TEMPLATES,
    drain_intro,
    drain_until_listening,
    fetch_interview,
    make_container,
    send_utterance,
)

INTRO_QUESTION = "Walk me through an internal tool you built end-to-end."


def _agent_lines(messages: list[dict[str, Any]]) -> list[str]:
    return [
        str(m["payload"]["text"])
        for m in messages
        if m["type"] == "transcript" and m["payload"]["role"] == "agent"
    ]


def _one_turn(tmp_path: Path, said: str) -> tuple[list[str], FakeLlm, dict[str, Any], list[Any]]:
    llm = FakeLlm(["Got it. ", "Why separate queues? "])
    container = make_container(tmp_path, llm, FakeStt(said))
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        session_id = drain_intro(ws)
        send_utterance(ws)
        turn = drain_until_listening(ws)
    row = fetch_interview(container.settings.database_url, session_id)
    assert row is not None
    return _agent_lines(turn), llm, json.loads(row.metadata_json), json.loads(row.transcript_json)


def test_score_request_is_refused_and_the_question_comes_back(tmp_path: Path) -> None:
    lines, llm, metadata, turns = _one_turn(tmp_path, "How would you rate that answer, out of 10?")

    assert lines == [f"{META_TEMPLATES['meta_score']} {INTRO_QUESTION}"]
    # Модель об этом ходе не знает: отказ держит код, а не её послушание
    assert "rate that answer" not in json.dumps(llm.calls)
    # Вопрос не потрачен
    assert metadata["phase"] == "INTRO"
    assert metadata["questions_asked"] == 1
    assert metadata["follow_ups"] == 0
    # Ход отличим и ни к какому вопросу не относится (P9)
    assert [t["state"] for t in turns[-2:]] == [META_STATE, META_STATE]
    assert [t["question_id"] for t in turns[-2:]] == [None, None]


def test_language_switch_is_refused_in_english(tmp_path: Path) -> None:
    lines, _, metadata, _ = _one_turn(tmp_path, "Can we switch to Russian for a minute?")

    assert lines == [f"{META_TEMPLATES['meta_language']} {INTRO_QUESTION}"]
    assert metadata["follow_ups"] == 0


def test_where_to_start_gets_advice_without_repeating_the_question(tmp_path: Path) -> None:
    lines, _, metadata, _ = _one_turn(
        tmp_path, "Where should I start: the business or the architecture?"
    )

    assert lines == [META_TEMPLATES["meta_where_to_start"]]
    assert metadata["questions_asked"] == 1


def test_a_real_answer_still_reaches_the_orchestrator(tmp_path: Path) -> None:
    """Красная сторона: без неё тест выше был бы зелёным и при политике «всё — мета»."""
    lines, llm, metadata, _ = _one_turn(
        tmp_path, "Our reply rate was fifteen percent, and that was good."
    )

    assert llm.calls, "ответ обязан дойти до модели"
    assert metadata["follow_ups"] == 1
    assert lines and META_TEMPLATES["meta_score"] not in lines[0]
