"""WebSocket contract tests (doc 15) — full turn happy path with mocked pipeline parts."""

import base64
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient, WebSocketTestSession

from app.config import Settings
from app.container import Container
from app.knowledge.prompts import PromptLibrary
from app.main import create_app
from tests.fakes import FakeDecoder, FakeLlm, FakeStt, FakeTts


def _make_container(tmp_path: Path, llm: FakeLlm, stt: FakeStt) -> Container:
    prompts = tmp_path / "prompts"
    (prompts / "templates").mkdir(parents=True)
    (prompts / "interviewer_system.txt").write_text("system {{profile_condensed}}")
    (prompts / "templates" / "interview_intro.txt").write_text("Welcome to the mock interview.")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "profile_condensed.md").write_text("profile")
    settings = Settings(
        prompts_dir=prompts,
        knowledge_dir=knowledge,
        sessions_dir=tmp_path / "sessions",
    )
    return Container(
        settings=settings,
        stt=stt,
        tts=FakeTts(),
        llm=llm,
        decoder=FakeDecoder(),
        prompts=PromptLibrary(prompts, knowledge),
        ollama=None,
    )


@pytest.fixture
def ws(tmp_path: Path) -> Iterator[tuple[WebSocketTestSession, Container]]:
    llm = FakeLlm(["Thanks. ", "What did you build? "])
    container = _make_container(tmp_path, llm, FakeStt("I built an internal CRM tool"))
    client = TestClient(create_app(container))
    with client.websocket_connect("/ws/session") as websocket:
        yield websocket, container


def _collect_until(ws: WebSocketTestSession, msg_type: str) -> list[dict[str, Any]]:
    messages = []
    while True:
        message = ws.receive_json()
        messages.append(message)
        if message["type"] == msg_type:
            return messages


def test_hello_ready(ws: tuple[WebSocketTestSession, Container]) -> None:
    websocket, _ = ws
    websocket.send_json({"type": "hello", "payload": {}})
    reply = websocket.receive_json()
    assert reply["type"] == "ready"
    assert reply["payload"]["ollama_ok"] is True


def test_full_interview_turn(ws: tuple[WebSocketTestSession, Container]) -> None:
    websocket, container = ws
    websocket.send_json({"type": "start_interview", "payload": {}})
    started = websocket.receive_json()
    assert started["type"] == "session_started"
    session_id = started["payload"]["session_id"]

    intro_messages = _collect_until(websocket, "state")  # speaking
    intro_rest = _collect_until(websocket, "state")  # ... listening
    types = [m["type"] for m in intro_messages + intro_rest]
    assert "audio" in types and "transcript" in types

    websocket.send_json(
        {
            "type": "utterance_end",
            "payload": {"audio_base64": base64.b64encode(b"webm-bytes").decode()},
        }
    )
    turn = _collect_until(websocket, "audio")
    while not turn[-1]["payload"].get("final", False):
        turn.extend(_collect_until(websocket, "audio"))
    transcripts = [m for m in turn if m["type"] == "transcript"]
    assert transcripts[0]["payload"]["role"] == "user"
    assert transcripts[0]["payload"]["text"] == "I built an internal CRM tool"
    agent = [m for m in transcripts if m["payload"]["role"] == "agent"]
    assert agent and agent[0]["payload"]["text"] == "Thanks. What did you build?"
    audio_chunks = [m for m in turn if m["type"] == "audio" and m["payload"]["chunk_base64"]]
    assert len(audio_chunks) == 2  # one per sentence — sentence streaming works

    # transcript persisted to JSON file (Phase 1 exit criterion)
    log_path = container.settings.sessions_dir / f"{session_id}.json"
    turns = json.loads(log_path.read_text())
    assert [t["role"] for t in turns] == ["agent", "user", "agent"]

    websocket.send_json({"type": "end_session", "payload": {"reason": "user"}})
    ended = _collect_until(websocket, "session_ended")[-1]
    assert ended["payload"]["session_id"] == session_id


def test_utterance_without_session_errors(ws: tuple[WebSocketTestSession, Container]) -> None:
    websocket, _ = ws
    websocket.send_json({"type": "utterance_end", "payload": {"audio_base64": ""}})
    reply = websocket.receive_json()
    assert reply["type"] == "error"
    assert reply["payload"]["code"] == "SESSION_NOT_FOUND"


def test_stt_empty_recoverable(tmp_path: Path) -> None:
    container = _make_container(tmp_path, FakeLlm(["x"]), FakeStt("uh"))
    client = TestClient(create_app(container))
    with client.websocket_connect("/ws/session") as websocket:
        websocket.send_json({"type": "start_interview", "payload": {}})
        _collect_until(websocket, "state")
        _collect_until(websocket, "state")
        websocket.send_json(
            {
                "type": "utterance_end",
                "payload": {"audio_base64": base64.b64encode(b"x").decode()},
            }
        )
        messages = _collect_until(websocket, "error")
        assert messages[-1]["payload"]["code"] == "STT_EMPTY"
        assert messages[-1]["payload"]["recoverable"] is True
        state = websocket.receive_json()
        assert state["payload"]["value"] == "listening"


def test_ping_pong(ws: tuple[WebSocketTestSession, Container]) -> None:
    websocket, _ = ws
    websocket.send_json({"type": "ping", "payload": {}})
    assert websocket.receive_json()["type"] == "pong"
