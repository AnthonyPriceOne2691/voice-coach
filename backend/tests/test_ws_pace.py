"""Просьба о темпе как мета-ход (spec P1, P2, P4, P5, P7, P9).

Проверяется не «ключ записан», а **с каким числом позван синтез** и **что
осталось в транскрипте**: настройка, доехавшая до базы, и речь, зазвучавшая
иначе, — разные утверждения (L20/L22).
"""

import json
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from app.main import create_app
from app.storage.turns import META_STATE
from tests.fakes import FakeLlm, FakeStt, FakeTts
from tests.helpers import (
    collect_until,
    drain_intro,
    drain_until_listening,
    fetch_interview,
    fetch_review,
    make_container,
    seed_finished_interview,
    send_utterance,
)

INTRO = "Hi, I'm Henry. Walk me through an internal tool you built end-to-end."
DEFAULT_SCALE = 1.15


def _agent_lines(messages: list[dict[str, Any]]) -> list[str]:
    return [
        str(m["payload"]["text"])
        for m in messages
        if m["type"] == "transcript" and m["payload"]["role"] == "agent"
    ]


def test_slower_request_changes_tempo_and_costs_no_question(tmp_path: Path) -> None:
    """P1 + P9: темп сменился, вопрос цел, ход помечен как мета."""
    llm = FakeLlm(["Got it. ", "Why separate queues? "])
    container = make_container(tmp_path, llm, FakeStt("Could you speak a bit slower, please?"))
    tts = container.tts
    assert isinstance(tts, FakeTts)

    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        session_id = drain_intro(ws)
        assert tts.scales == [DEFAULT_SCALE]  # интро — прежним темпом

        send_utterance(ws)
        turn = drain_until_listening(ws)

    # P1: подтверждение и дословный повтор — и оба УЖЕ новым темпом
    assert _agent_lines(turn) == [f"Sure, slowing down. Here it is again. {INTRO}"]
    assert tts.scales == [DEFAULT_SCALE, 1.30, 1.30]

    # P1: модель об этом ходе не знает ничего — ни просьбы, ни повтора
    spoken_to_llm = json.dumps(llm.calls)
    assert "slower" not in spoken_to_llm
    assert "Here it is again" not in spoken_to_llm

    row = fetch_interview(container.settings.database_url, session_id)
    assert row is not None
    metadata = json.loads(row.metadata_json)
    # P1: состояние интервью не двинулось — вопрос не потрачен
    assert metadata["phase"] == "INTRO"
    assert metadata["questions_asked"] == 1
    assert metadata["follow_ups"] == 0

    # P9: мета-ход отличим и ни к какому вопросу не относится
    turns = json.loads(row.transcript_json)
    assert [t["state"] for t in turns[-2:]] == [META_STATE, META_STATE]
    assert [t["question_id"] for t in turns[-2:]] == [None, None]
    assert [t["role"] for t in turns[-2:]] == ["user", "agent"]


def test_faster_request_speeds_henry_up(tmp_path: Path) -> None:
    """P2."""
    container = make_container(
        tmp_path, FakeLlm(["x. "]), FakeStt("That's too slow, speak faster.")
    )
    tts = container.tts
    assert isinstance(tts, FakeTts)

    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        drain_intro(ws)
        send_utterance(ws)
        turn = drain_until_listening(ws)

    assert _agent_lines(turn) == [f"Sure, speeding up. Here it is again. {INTRO}"]
    assert tts.scales[-2:] == [1.00, 1.00]


def test_answer_mentioning_speed_is_a_normal_turn(tmp_path: Path) -> None:
    """P4: длинный ответ со словами «speed up» и «too slow» — это ответ."""
    answer = (
        "We had to speed up the ingest pipeline, the old version was too slow for "
        "our SLA, so I rewrote the batching layer."
    )
    llm = FakeLlm(["Got it. ", "Why the batching layer? "])
    container = make_container(tmp_path, llm, FakeStt(answer))
    tts = container.tts
    assert isinstance(tts, FakeTts)

    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        session_id = drain_intro(ws)
        send_utterance(ws)
        turn = drain_until_listening(ws)

    assert _agent_lines(turn) == ["Got it. Why the batching layer?"]  # ответила модель
    assert set(tts.scales) == {DEFAULT_SCALE}  # темп не тронут
    assert answer in json.dumps(llm.calls)  # ответ дошёл до модели

    row = fetch_interview(container.settings.database_url, session_id)
    assert row is not None
    assert json.loads(row.metadata_json)["phase"] != "INTRO"  # состояние продвинулось
    assert all(t["state"] != META_STATE for t in json.loads(row.transcript_json))


def test_pace_survives_the_session(tmp_path: Path) -> None:
    """P5: попросил один раз — Генри говорит так и в следующей сессии."""
    container = make_container(tmp_path, FakeLlm(["x. "]), FakeStt("Slower, please."))
    tts = container.tts
    assert isinstance(tts, FakeTts)

    with TestClient(create_app(container)) as client:
        with client.websocket_connect("/ws/session") as ws:
            ws.send_json({"type": "start_interview", "payload": {}})
            drain_intro(ws)
            send_utterance(ws)
            drain_until_listening(ws)
            ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
            collect_until(ws, "session_ended")

        assert client.get("/settings").json()["speech_length_scale"] == 1.30

        tts.scales.clear()
        with client.websocket_connect("/ws/session") as ws:
            ws.send_json({"type": "start_interview", "payload": {}})
            drain_intro(ws)
            ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
            collect_until(ws, "session_ended")

    # интро НОВОЙ сессии озвучено сохранённым темпом, а не дефолтом из конфига
    assert tts.scales[0] == 1.30


def test_pace_request_works_in_review_mode(tmp_path: Path) -> None:
    """P7: Mode 2 — тот же мета-ход, состояние разбора не двигается."""
    llm = FakeLlm(["Q1 was strong. ", "You led with the metric. "])
    container = make_container(tmp_path, llm, FakeStt("Slow down a little."))
    seed_finished_interview(container.settings.database_url, "int-1")
    tts = container.tts
    assert isinstance(tts, FakeTts)

    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_review", "payload": {"interview_id": "int-1"}})
        started = ws.receive_json()
        review_id = started["payload"]["session_id"]
        drain_until_listening(ws)
        agent_intro = "Q1 was strong. You led with the metric."

        send_utterance(ws)
        turn = drain_until_listening(ws)
        ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
        collect_until(ws, "session_ended")

    assert _agent_lines(turn) == [f"Sure, slowing down. Here it is again. {agent_intro}"]
    assert tts.scales[-2:] == [1.30, 1.30]

    row = fetch_review(container.settings.database_url, review_id)
    assert row is not None
    # разбор не сдвинулся: ответ на первый вопрос перевёл бы счётчик в 1
    assert json.loads(row.metadata_json)["questions_reviewed"] == 0
    turns = json.loads(row.transcript_json)
    assert [t["state"] for t in turns[-2:]] == [META_STATE, META_STATE]
