"""WebSocket contract tests (doc 15) — orchestrated Mode 1 with mocked AI."""

import base64
import json
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient, WebSocketTestSession

from app.main import create_app
from tests.fakes import FakeLlm, FakeStt
from tests.helpers import fetch_interview, fetch_review, make_container, seed_finished_interview

LONG_ANSWER = "I built an internal CRM tool with separate queues and cut the team from 5 to 1"

# ⚠ Эти два теста выходят из `with TestClient(...) as ws` при ЖИВОЙ сессии, не
# послав `end_session`, — то есть исполняют инвариант «отключение клиента
# завершает сессию». До 2026-08-12 они висели на linux (6 прогонов из 10) и
# были подавлены `skipif(CI)`: отмена приходила внутрь записи статуса, соединение
# оставалось вне пула, SQLAlchemy добивал его задачей, а закрытие цикла ждало её
# вечно — падал ВЕСЬ прогон, а не тест. Подавление снято вместе с починкой;
# разбор — delivery/archive/<этой поставки>/diagnosis.md.


def _collect_until(ws: WebSocketTestSession, msg_type: str) -> list[dict[str, Any]]:
    messages = []
    while True:
        message = ws.receive_json()
        messages.append(message)
        if message["type"] == msg_type:
            return messages


def _drain_intro(ws: WebSocketTestSession) -> str:
    started = ws.receive_json()
    assert started["type"] == "session_started"
    messages = _collect_until(ws, "state")  # speaking ... listening
    while messages[-1]["payload"]["value"] != "listening":
        messages += _collect_until(ws, "state")
    return str(started["payload"]["session_id"])


def _send_utterance(ws: WebSocketTestSession, payload: bytes = b"webm") -> None:
    ws.send_json(
        {
            "type": "utterance_end",
            "payload": {"audio_base64": base64.b64encode(payload).decode()},
        }
    )


def test_hello_ready(tmp_path: Path) -> None:
    container = make_container(tmp_path, FakeLlm(["Ok? "]), FakeStt())
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "hello", "payload": {}})
        reply = ws.receive_json()
        assert reply["type"] == "ready"
        assert reply["payload"]["ollama_ok"] is True


def test_full_orchestrated_turn_persists_to_sqlite(tmp_path: Path) -> None:
    llm = FakeLlm(["Got it. ", "Why separate queues? "])
    container = make_container(tmp_path, llm, FakeStt(LONG_ANSWER))
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        session_id = _drain_intro(ws)

        _send_utterance(ws)
        turn = _collect_until(ws, "state")
        while turn[-1]["payload"]["value"] != "listening":
            turn += _collect_until(ws, "state")

        transcripts = [m for m in turn if m["type"] == "transcript"]
        assert transcripts[0]["payload"]["role"] == "user"
        assert transcripts[0]["payload"]["text"] == LONG_ANSWER
        agent = [m for m in transcripts if m["payload"]["role"] == "agent"]
        assert agent[0]["payload"]["text"] == "Got it. Why separate queues?"
        audio_chunks = [m for m in turn if m["type"] == "audio" and m["payload"]["chunk_base64"]]
        assert len(audio_chunks) == 2  # sentence streaming survived the enforcer

        # user message got the orchestrator wrapper (doc 16): first follow-up always
        assert llm.last_messages is not None
        wrapped = llm.last_messages[-1]["content"]
        assert "[STATE=FOLLOW_UP]" in wrapped and "[QUESTION_ID=project_overview]" in wrapped

        ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
        _collect_until(ws, "session_ended")

    row = fetch_interview(container.settings.database_url, session_id)
    assert row is not None and row.status == "completed"
    turns = json.loads(row.transcript_json)
    assert [t["role"] for t in turns] == ["agent", "user", "agent"]
    assert turns[1]["state"] == "INTRO" and turns[1]["question_id"] == "project_overview"
    assert turns[2]["state"] == "FOLLOW_UP"
    metadata = json.loads(row.metadata_json)
    assert metadata["hard_violations"] == 0


def test_enforcer_blocks_coaching_in_live_turn(tmp_path: Path) -> None:
    llm = FakeLlm(["Why queues? ", "Great answer, well done! "])
    container = make_container(tmp_path, llm, FakeStt(LONG_ANSWER))
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        session_id = _drain_intro(ws)
        _send_utterance(ws)
        turn = _collect_until(ws, "state")
        while turn[-1]["payload"]["value"] != "listening":
            turn += _collect_until(ws, "state")
        agent = [m for m in turn if m["type"] == "transcript" and m["payload"]["role"] == "agent"]
        assert agent[0]["payload"]["text"] == "Why queues?"  # praise truncated before TTS
        ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
        _collect_until(ws, "session_ended")

    row = fetch_interview(container.settings.database_url, session_id)
    assert row is not None
    assert json.loads(row.metadata_json)["hard_violations"] == 1


def test_stt_empty_recoverable(tmp_path: Path) -> None:
    container = make_container(tmp_path, FakeLlm(["x? "]), FakeStt("[BLANK_AUDIO]"))
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        _drain_intro(ws)
        _send_utterance(ws)
        messages = _collect_until(ws, "error")
        assert messages[-1]["payload"]["code"] == "STT_EMPTY"
        assert messages[-1]["payload"]["recoverable"] is True
        assert ws.receive_json()["payload"]["value"] == "listening"


class _ExplodingDecoder:
    async def to_wav(self, data: bytes, out_path: Path) -> None:
        raise RuntimeError("ffmpeg blew up")


def test_decode_failure_is_recoverable(tmp_path: Path) -> None:
    container = make_container(tmp_path, FakeLlm(["Ok? "]), FakeStt())
    container.decoder = _ExplodingDecoder()
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        _drain_intro(ws)
        _send_utterance(ws, b"x")
        messages = _collect_until(ws, "error")
        assert messages[-1]["payload"]["code"] == "INTERNAL"
        assert messages[-1]["payload"]["recoverable"] is True
        assert ws.receive_json()["payload"]["value"] == "listening"
        ws.send_json({"type": "ping", "payload": {}})
        assert ws.receive_json()["type"] == "pong"


def test_utterance_without_session_errors(tmp_path: Path) -> None:
    container = make_container(tmp_path, FakeLlm(["x? "]), FakeStt())
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "utterance_end", "payload": {"audio_base64": ""}})
        assert ws.receive_json()["payload"]["code"] == "SESSION_NOT_FOUND"


def test_review_session_over_ws(tmp_path: Path) -> None:
    """Mode 2: start_review on a finished interview -> grounded walk -> summary scheduled."""
    llm = FakeLlm(["Q1 was strong. ", "You led with the metric. "])
    container = make_container(tmp_path, llm, FakeStt("okay makes sense"))
    seed_finished_interview(container.settings.database_url, "int-1")

    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_review", "payload": {"interview_id": "int-1"}})
        started = ws.receive_json()
        assert started["type"] == "session_started"
        assert started["payload"]["session_kind"] == "review"
        review_id = started["payload"]["session_id"]

        # LLM-driven intro turn
        intro = _collect_until(ws, "state")
        while intro[-1]["payload"]["value"] != "listening":
            intro += _collect_until(ws, "state")
        agent = [m for m in intro if m["type"] == "transcript"]
        assert agent[0]["payload"]["text"] == "Q1 was strong. You led with the metric."
        # review system prompt is grounded in segmented Q&A
        assert llm.last_messages is not None
        assert "Q1: Walk me through a tool." in llm.last_messages[0]["content"]

        # user ack -> advance to Q2; statement again -> WRAP_UP; reply -> END
        _send_utterance(ws)
        _collect_until(ws, "audio")
        turn = _collect_until(ws, "state")
        while turn[-1]["payload"]["value"] != "listening":
            turn += _collect_until(ws, "state")
        _send_utterance(ws)
        turn = _collect_until(ws, "state")
        while turn[-1]["payload"]["value"] != "listening":
            turn += _collect_until(ws, "state")
        _send_utterance(ws)
        ended = _collect_until(ws, "session_ended")[-1]
        assert ended["payload"]["session_kind"] == "review"
        assert ended["payload"]["next_action"] == "generate_summary"

    row = fetch_review(container.settings.database_url, review_id)
    assert row is not None and row.status == "completed"
    turns = json.loads(row.transcript_json)
    assert turns[0]["role"] == "agent" and turns[0]["state"] == "INTRO"
    interview = fetch_interview(container.settings.database_url, "int-1")
    assert interview is not None and interview.review_session_id == review_id


def test_start_review_unknown_interview_errors(tmp_path: Path) -> None:
    container = make_container(tmp_path, FakeLlm(["x. "]), FakeStt())
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_review", "payload": {"interview_id": "missing"}})
        reply = ws.receive_json()
        assert reply["payload"]["code"] == "SESSION_NOT_FOUND"


def test_disconnect_without_end_session_finishes_flow(tmp_path: Path) -> None:
    """Инвариант: отключение клиента ЗАВЕРШАЕТ сессию, а не бросает её на середине.

    Repro этой поставки. До фикса путь `WebSocketDisconnect -> flow.finish()`
    отменялся гашением приложения посередине записи: соединение оставалось вне
    пула, SQLAlchemy добивал его отдельной задачей, и закрытие цикла ждало её
    вечно — виснул ВЕСЬ прогон (замер: 6 из 10 на linux, 0 из 60 на macOS).

    Тест утверждает наблюдаемое следствие, а не внутренности: клиент ушёл молча,
    и в БД у сессии стоит `in_progress` со временем окончания. Если уборку снова
    оборвут, строка останется без статуса — и это упадёт как обычный красный
    тест, не как вис.
    """
    container = make_container(tmp_path, FakeLlm(["Ok? "]), FakeStt())
    with TestClient(create_app(container)) as client:
        with client.websocket_connect("/ws/session") as ws:
            ws.send_json({"type": "start_interview", "payload": {}})
            session_id = _drain_intro(ws)
            # выходим из ws-контекста БЕЗ end_session — браузер закрыли, сеть упала

    row = fetch_interview(container.settings.database_url, session_id)
    assert row is not None
    assert row.status == "in_progress"
    assert row.ended_at is not None
    # транскрипт интро уже на диске: flush per turn, а не в конце сессии
    assert json.loads(row.transcript_json)[0]["role"] == "agent"
