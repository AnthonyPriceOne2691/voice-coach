"""REST API tests (doc 15): history, minimal summary, vocabulary, settings."""

import asyncio
from pathlib import Path

from starlette.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.orchestrator.pace import in_range
from app.storage.db import Database
from app.storage.repositories.settings_repo import DEFAULTS
from app.storage.repositories.vocabulary import VocabularyRepository
from tests.fakes import FakeLlm, FakeStt, ScriptedLlm
from tests.helpers import make_container, minimal_summary_tokens, seed_finished_interview


def test_interviews_list_and_detail(tmp_path: Path) -> None:
    container = make_container(tmp_path, FakeLlm(["x. "]), FakeStt())
    seed_finished_interview(container.settings.database_url, "int-1")
    with TestClient(create_app(container)) as client:
        listed = client.get("/sessions/interviews").json()
        assert listed["items"][0]["id"] == "int-1"
        assert listed["items"][0]["has_review"] is False
        assert listed["items"][0]["has_debrief"] is False

        detail = client.get("/sessions/interviews/int-1").json()
        assert detail["status"] == "completed"
        assert detail["transcript"][1]["question_id"] == "project_overview"
        assert detail["debrief"] is None

        assert client.get("/sessions/interviews/missing").status_code == 404
        assert client.get("/sessions/reviews/missing").status_code == 404


def test_minimal_summary_endpoint(tmp_path: Path) -> None:
    llm = ScriptedLlm([minimal_summary_tokens()])
    container = make_container(tmp_path, llm, FakeStt())
    seed_finished_interview(container.settings.database_url, "int-1")
    with TestClient(create_app(container)) as client:
        response = client.post("/sessions/interviews/int-1/minimal-summary")
        assert response.status_code == 200
        assert response.json()["debrief"]["scores"]["clarity"] == 3
        # Skip path runs on Qwen — the already-loaded model, no swap (doc 07)
        detail = client.get("/sessions/interviews/int-1").json()
        assert detail["summary_kind"] == "minimal"

        assert client.post("/sessions/interviews/missing/minimal-summary").status_code == 404


def test_minimal_summary_failure_returns_502(tmp_path: Path) -> None:
    container = make_container(tmp_path, ScriptedLlm([["junk"], ["junk"]]), FakeStt())
    seed_finished_interview(container.settings.database_url, "int-1")
    with TestClient(create_app(container)) as client:
        assert client.post("/sessions/interviews/int-1/minimal-summary").status_code == 502


def test_delete_interview_cascade(tmp_path: Path) -> None:
    container = make_container(tmp_path, FakeLlm(["x. "]), FakeStt())
    seed_finished_interview(container.settings.database_url, "int-1")
    with TestClient(create_app(container)) as client:
        assert client.delete("/sessions/interviews/int-1").status_code == 204
        assert client.get("/sessions/interviews/int-1").status_code == 404
        assert client.delete("/sessions/interviews/int-1").status_code == 404


def test_vocabulary_list_and_soft_delete(tmp_path: Path) -> None:
    container = make_container(tmp_path, FakeLlm(["x. "]), FakeStt())

    async def seed() -> None:
        db = Database(container.settings.database_url)
        await db.create_all()
        await VocabularyRepository(db).merge(
            [
                {
                    "term_en": "trade-off",
                    "translation_ru": "компромисс",
                    "example_en": "The trade-off was X.",
                    "category": "architecture",
                }
            ],
            session_id="s1",
        )
        await db.dispose()

    asyncio.run(seed())
    with TestClient(create_app(container)) as client:
        items = client.get("/vocabulary").json()["items"]
        assert items[0]["term_en"] == "trade-off"
        assert items[0]["translation_ru"] == "компромисс"

        filtered = client.get("/vocabulary", params={"q": "nope"}).json()
        assert filtered["items"] == []

        assert client.delete(f"/vocabulary/{items[0]['id']}").status_code == 204
        assert client.get("/vocabulary").json()["items"] == []
        assert client.delete(f"/vocabulary/{items[0]['id']}").status_code == 404


def test_settings_roundtrip(tmp_path: Path) -> None:
    container = make_container(tmp_path, FakeLlm(["x. "]), FakeStt())
    with TestClient(create_app(container)) as client:
        assert client.get("/settings").json()["interview_duration_min"] == 15
        updated = client.patch("/settings", json={"interview_duration_min": 30}).json()
        assert updated["interview_duration_min"] == 30
        assert client.get("/settings").json()["interview_duration_min"] == 30


def test_speech_pace_setting_is_exposed_and_validated(tmp_path: Path) -> None:
    """P5 + P6: темп виден в настройках, значение вне коридора ОТВЕРГАЕТСЯ."""
    container = make_container(tmp_path, FakeLlm(["x. "]), FakeStt())
    with TestClient(create_app(container)) as client:
        assert client.get("/settings").json()["speech_length_scale"] == 1.15

        assert client.patch("/settings", json={"speech_length_scale": 1.45}).status_code == 200
        assert client.get("/settings").json()["speech_length_scale"] == 1.45

        # P6: молчаливый зажим неотличим от принятого значения — поэтому 422
        for bad in (2.5, 0.1, "fast", True, None):
            assert client.patch("/settings", json={"speech_length_scale": bad}).status_code == 422
        assert client.get("/settings").json()["speech_length_scale"] == 1.45  # не тронуто


def test_settings_defaults_agree_with_the_config() -> None:
    """L11: два файла, каждый со своей половиной правды, — уже случившийся дефект.

    `DEFAULTS` и `Settings.piper_length_scale` описывают ОДНО значение. Разъезд
    ничего не сломает громко: Генри просто заговорит не тем темпом, с которого
    начинается коридор, и понять это можно будет только на слух.
    """
    assert DEFAULTS["speech_length_scale"] == Settings().piper_length_scale
    assert in_range(DEFAULTS["speech_length_scale"])
