"""Shared test container wiring (real contracts/questions/DB, fake AI)."""

import asyncio
import base64
import json
from pathlib import Path
from typing import Any

from starlette.testclient import WebSocketTestSession

from app.config import REPO_ROOT, Settings
from app.container import Container
from app.contracts.enforcer import ContractEnforcer
from app.contracts.spec import load_contract
from app.knowledge.prompts import PromptLibrary
from app.orchestrator.question_bank import load_bank
from app.orchestrator.talk import load_script
from app.storage.db import Database
from app.storage.models import InterviewSession, ReviewSession, TalkSession
from app.storage.repositories.interviews import InterviewRepository
from app.storage.repositories.reviews import ReviewRepository
from app.storage.repositories.settings_repo import SettingsRepository
from app.storage.repositories.talks import TalkRepository
from app.storage.repositories.vocabulary import VocabularyRepository
from app.summary.service import SummaryService
from tests.db_lifecycle import owned_database
from tests.fakes import FakeDecoder, FakeStt, FakeTts

#: Реплики подтверждения темпа. В тестовом контейнере они СВОИ, а не копия
#: настоящих: тест мета-хода проверяет механику, а не текст. Что настоящие
#: файлы существуют и не задевают запретов, сторожит test_prompts.py.
PACE_TEMPLATES = {
    "pace_slower": "Sure, slowing down. Here it is again.",
    "pace_faster": "Sure, speeding up. Here it is again.",
    "pace_slowest": "That's the slowest I can go, but let me repeat it.",
    "pace_fastest": "That's as fast as I can go, but let me repeat it.",
}

META_TEMPLATES = {
    "meta_score": "No scores until the review.",
    "meta_language": "Let's keep it in English.",
    "meta_where_to_start": "Lead with the result — go ahead.",
}

MINIMAL_SUMMARY = {
    "overall_summary": "Short but focused session.",
    "scores": {
        "clarity": 3,
        "structure": 3,
        "technical_depth": 3,
        "english_fluency": 3,
        "positioning": 3,
    },
    "strengths": [],
    "improvements": [],
    "weak_answers": [],
    "vocabulary": [],
    "consistency_flags": [],
    "next_session_focus": [],
}


def make_container(tmp_path: Path, llm: Any, stt: FakeStt) -> Container:
    prompts = tmp_path / "prompts"
    (prompts / "templates").mkdir(parents=True)
    (prompts / "interviewer_system.txt").write_text("system {{profile_condensed}}")
    (prompts / "review_system.txt").write_text(
        "review system\n{{interview_qa_segments}}\n{{profile_condensed}}"
    )
    (prompts / "talk_system.txt").write_text("talk system {{profile_condensed}}")
    (prompts / "summary_system.txt").write_text("summary system")
    (prompts / "minimal_summary_system.txt").write_text("minimal system")
    # Контейнер обязан быть ПОЛНЫМ: с 2026-08-15 суммаризация чинит негодный
    # перевод повторным запросом, и без этого файла первый же тест, дошедший до
    # починки, упал бы на отсутствующем промпте, а не на своём предмете.
    (prompts / "translate_term_system.txt").write_text("translate term")
    # Просьба о проверке речи (D3a.2) — настоящая: тесты сверяют подстановку реплики.
    (prompts / "language_check.txt").write_text(
        (REPO_ROOT / "data" / "prompts" / "language_check.txt").read_text(encoding="utf-8")
    )
    (prompts / "templates" / "interview_intro.txt").write_text(
        "Hi, I'm Henry. Walk me through an internal tool you built end-to-end."
    )
    (prompts / "templates" / "interview_wrap_up.txt").write_text(
        "That's all from my side. Do you have any questions for us?"
    )
    for name, line in {**PACE_TEMPLATES, **META_TEMPLATES}.items():
        (prompts / "templates" / f"{name}.txt").write_text(line)
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
    prompt_library = PromptLibrary(prompts, knowledge)
    return Container(
        settings=settings,
        stt=stt,
        tts=FakeTts(),
        llm=llm,
        decoder=FakeDecoder(),
        prompts=prompt_library,
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
        talks=TalkRepository(db),
        talk_enforcer=ContractEnforcer(
            load_contract(REPO_ROOT / "data" / "contracts" / "talk.contract.yaml")
        ),
        talk_script=load_script(REPO_ROOT / "data" / "talk" / "talk.yaml"),
        question_bank=load_bank(
            REPO_ROOT / "data" / "questions" / "technical_project_walkthrough.yaml"
        ),
        behavioral_bank=load_bank(REPO_ROOT / "data" / "questions" / "behavioral.yaml"),
        summaries=SummaryService(
            llm,
            prompt_library,
            InterviewRepository(db),
            ReviewRepository(db),
            VocabularyRepository(db),
            settings,
        ),
        ollama=None,
    )


def collect_until(ws: WebSocketTestSession, msg_type: str) -> list[dict[str, Any]]:
    messages = []
    while True:
        message = ws.receive_json()
        messages.append(message)
        if message["type"] == msg_type:
            return messages


def drain_until_listening(ws: WebSocketTestSession) -> list[dict[str, Any]]:
    messages = collect_until(ws, "state")
    while messages[-1]["payload"]["value"] != "listening":
        messages += collect_until(ws, "state")
    return messages


def drain_intro(ws: WebSocketTestSession) -> str:
    started = ws.receive_json()
    assert started["type"] == "session_started"
    drain_until_listening(ws)  # speaking ... listening
    return str(started["payload"]["session_id"])


def send_utterance(ws: WebSocketTestSession, payload: bytes = b"webm") -> None:
    ws.send_json(
        {
            "type": "utterance_end",
            "payload": {"audio_base64": base64.b64encode(payload).decode()},
        }
    )


async def load_interview(database_url: str, session_id: str) -> InterviewSession | None:
    """Прочитать сессию отдельным движком из async-теста — и погасить его."""
    async with owned_database(database_url) as db:
        return await InterviewRepository(db).get(session_id)


def fetch_interview(database_url: str, session_id: str) -> InterviewSession | None:
    return asyncio.run(load_interview(database_url, session_id))


def fetch_review(database_url: str, review_id: str) -> ReviewSession | None:
    async def go() -> ReviewSession | None:
        async with owned_database(database_url) as db:
            return await ReviewRepository(db).get(review_id)

    return asyncio.run(go())


def fetch_talk(database_url: str, talk_id: str) -> TalkSession | None:
    async def go() -> TalkSession | None:
        async with owned_database(database_url) as db:
            return await TalkRepository(db).get(talk_id)

    return asyncio.run(go())


def seed_finished_interview(database_url: str, interview_id: str = "int-1") -> None:
    turns = [
        {
            "role": "agent",
            "text": "Walk me through a tool.",
            "timestamp_ms": 0,
            "turn_index": 0,
            "state": "INTRO",
            "question_id": "project_overview",
        },
        {
            "role": "user",
            "text": "I built a CRM that cut the team from 5 to 1.",
            "timestamp_ms": 5000,
            "turn_index": 1,
            "state": "INTRO",
            "question_id": "project_overview",
        },
        {
            "role": "agent",
            "text": "What was the impact?",
            "timestamp_ms": 9000,
            "turn_index": 2,
            "state": "CORE_QUEST",
            "question_id": "impact",
        },
        {
            "role": "user",
            "text": "About 120 hours saved monthly.",
            "timestamp_ms": 15000,
            "turn_index": 3,
            "state": "CORE_QUEST",
            "question_id": "impact",
        },
    ]

    async def go() -> None:
        async with owned_database(database_url) as db:
            await db.create_all()
            repo = InterviewRepository(db)
            await repo.create(interview_id, interview_mode="m", persona="senior_colleague")
            await repo.checkpoint(interview_id, turns, {"duration_sec": 120})
            await repo.finish(interview_id, status="completed")

    asyncio.run(go())


def minimal_summary_tokens() -> list[str]:
    return [json.dumps(MINIMAL_SUMMARY)]
