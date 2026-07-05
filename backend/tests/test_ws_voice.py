"""WebSocket contract tests (doc 15) — orchestrated Mode 1 with mocked AI."""

import asyncio
import base64
import json
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient, WebSocketTestSession

from app.config import Settings
from app.container import Container
from app.contracts.enforcer import ContractEnforcer
from app.contracts.spec import load_contract
from app.knowledge.prompts import PromptLibrary
from app.main import create_app
from app.orchestrator.question_bank import load_bank
from app.storage.db import Database
from app.storage.models import InterviewSession
from app.storage.repositories.interviews import InterviewRepository
from app.storage.repositories.reviews import ReviewRepository
from app.storage.repositories.settings_repo import SettingsRepository
from app.storage.repositories.vocabulary import VocabularyRepository
from tests.fakes import FakeDecoder, FakeLlm, FakeStt, FakeTts

REPO_ROOT = Path(__file__).resolve().parents[2]
LONG_ANSWER = "I built an internal CRM tool with separate queues and cut the team from 5 to 1"


def make_container(tmp_path: Path, llm: Any, stt: FakeStt) -> Container:
    prompts = tmp_path / "prompts"
    (prompts / "templates").mkdir(parents=True)
    (prompts / "interviewer_system.txt").write_text("system {{profile_condensed}}")
    (prompts / "templates" / "interview_intro.txt").write_text(
        "Hi, I'm Henry. Walk me through an internal tool you built end-to-end."
    )
    (prompts / "templates" / "interview_wrap_up.txt").write_text(
        "That's all from my side. Do you have any questions for us?"
    )
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "profile_condensed.md").write_text("profile")
    settings = Settings(
        prompts_dir=prompts,
        knowledge_dir=knowledge,
        sessions_dir=tmp_path / "sessions",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
    )
    db = Database(settings.database_url)
    return Container(
        settings=settings,
        stt=stt,
        tts=FakeTts(),
        llm=llm,
        decoder=FakeDecoder(),
        prompts=PromptLibrary(prompts, knowledge),
        db=db,
        interviews=InterviewRepository(db),
        reviews=ReviewRepository(db),
        vocabulary=VocabularyRepository(db),
        user_settings=SettingsRepository(db),
        interview_enforcer=ContractEnforcer(
            load_contract(REPO_ROOT / "data" / "contracts" / "interview.contract.yaml")
        ),
        review_enforcer=ContractEnforcer(
            load_contract(REPO_ROOT / "data" / "contracts" / "review.contract.yaml")
        ),
        question_bank=load_bank(
            REPO_ROOT / "data" / "questions" / "technical_project_walkthrough.yaml"
        ),
        ollama=None,
    )


def fetch_interview(database_url: str, session_id: str) -> InterviewSession | None:
    async def go() -> InterviewSession | None:
        db = Database(database_url)
        row = await InterviewRepository(db).get(session_id)
        await db.dispose()
        return row

    return asyncio.run(go())


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
