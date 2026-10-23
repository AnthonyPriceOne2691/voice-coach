"""REST разговоров и их заметок «было → лучше» (doc 15; D3a.2, поставка talk-notes).

Заметки пишет проверка речи (поставка talk-check) в `metadata_json["language_notes"]`.
Здесь строки разговора создаются напрямую — по контракту данных из спеки, без
проверки речи: предмет — что REST отдаёт, озвучивает и кладёт в банк слов.
"""

import asyncio
import io
import json
import wave
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.container import Container
from app.llm.ollama_client import OllamaError
from app.main import create_app
from app.storage.db import Database
from app.storage.models import TalkSession
from app.storage.repositories.settings_repo import SettingsRepository
from tests.fakes import FakeLlm, FakeStt, FakeTts, ScriptedLlm
from tests.helpers import make_container

SAID = "I go to the office and meet my client"
BETTER = "I went to the office and met my client"
NOTE = {
    "turn_index": 1,
    "kind": "error",
    "said": SAID,
    "better": BETTER,
    "why": "past tense",
    "spoken": False,
}
STYLE = {
    "turn_index": 1,
    "kind": "style",
    "said": "It was a long day",
    "better": "It was an exhausting day",
    "why": "",
    "spoken": False,
}
TRANSCRIPT = [
    {"role": "agent", "text": "How was your day?", "timestamp_ms": 0, "turn_index": 0},
    {
        "role": "user",
        "text": f"Yesterday {SAID}. It was a long day.",
        "timestamp_ms": 5000,
        "turn_index": 1,
    },
]
RUSSIAN = "Я пошёл в офис и встретился с клиентом"
ADD = "/sessions/talks/t1/notes/{n}/vocabulary"


def talk(
    talk_id: str,
    started: str,
    *,
    ended: str | None = None,
    notes: list[Any] | None = None,
    status: str = "completed",
) -> TalkSession:
    metadata: dict[str, Any] = {"phase": "CHAT", "topics": ["weekend"]}
    if notes is not None:  # разговор до talk-check — ключа нет вовсе
        metadata["language_notes"] = notes
    return TalkSession(
        id=talk_id,
        started_at=started,
        ended_at=ended,
        persona="friend_mentor",
        transcript_json=json.dumps(TRANSCRIPT),
        metadata_json=json.dumps(metadata),
        status=status,
        created_at=started,
    )


def seed(container: Container, *rows: TalkSession, settings: dict[str, Any] | None = None) -> None:
    async def go() -> None:
        db = Database(container.settings.database_url)
        await db.create_all()
        async with db.session() as s:
            s.add_all(rows)
            await s.commit()
        if settings:
            await SettingsRepository(db).update(settings)
        await db.dispose()

    asyncio.run(go())


def one_talk(tmp_path: Path, llm: Any, **settings: Any) -> Container:
    container = make_container(tmp_path, llm, FakeStt())
    ended = "2026-10-23T18:10:00+00:00"
    seed(
        container,
        talk("t1", "2026-10-23T18:00:00+00:00", ended=ended, notes=[NOTE, STYLE]),
        settings=settings,
    )
    return container


def test_talk_list_is_a_bounded_page_newest_first(tmp_path: Path) -> None:
    """C13: строка разговора — дата, длительность, число заметок; страница ограничена."""
    container = make_container(tmp_path, FakeLlm([]), FakeStt())
    seed(
        container,
        talk("old", "2026-10-20T10:00:00+00:00", ended="2026-10-20T10:12:30+00:00", notes=[NOTE]),
        talk("legacy", "2026-10-21T10:00:00+00:00", ended="2026-10-21T10:05:00+00:00"),
        talk("left", "2026-10-22T10:00:00+00:00", notes=[NOTE, STYLE], status="in_progress"),
    )
    with TestClient(create_app(container)) as client:
        items = client.get("/sessions/talks").json()["items"]
        page = client.get("/sessions/talks", params={"limit": 1, "offset": 1}).json()["items"]
        rejected = [
            client.get("/sessions/talks", params=bad).status_code
            for bad in ({"limit": 0}, {"limit": 101}, {"offset": -1})
        ]
    assert [i["id"] for i in items] == ["left", "legacy", "old"]  # C13: новые первыми
    by_id = {i["id"]: i for i in items}
    assert by_id["old"]["duration_sec"] == 750 and by_id["old"]["notes_count"] == 1  # C13
    assert by_id["legacy"]["notes_count"] == 0  # C13: до talk-check заметок нет
    left = by_id["left"]
    assert (left["ended_at"], left["duration_sec"], left["notes_count"]) == (None, None, 2)  # C13
    assert [i["id"] for i in page] == ["legacy"]
    assert rejected == [422, 422, 422]  # страница ограничена: выборка растёт с каждым днём


def test_talk_detail_has_notes_in_order_and_the_transcript(tmp_path: Path) -> None:
    """C10, C13: открыв разговор, видишь заметки по порядку и транскрипт."""
    container = make_container(tmp_path, FakeLlm([]), FakeStt())
    broken = [NOTE, {"said": 1, "better": None}, "junk", STYLE]  # нарушение контракта
    seed(
        container,
        talk("t1", "2026-10-20T10:00:00+00:00", ended="2026-10-20T10:12:30+00:00", notes=broken),
        talk("legacy", "2026-10-21T10:00:00+00:00"),
    )
    with TestClient(create_app(container)) as client:
        detail = client.get("/sessions/talks/t1").json()
        legacy = client.get("/sessions/talks/legacy").json()
        missing = client.get("/sessions/talks/missing").status_code
    assert detail["language_notes"] == [NOTE, STYLE]  # C10: экран не падает на чужой ошибке
    assert detail["notes_count"] == 2
    assert detail["transcript"] == TRANSCRIPT  # C13
    assert legacy["language_notes"] == [] and legacy["duration_sec"] is None
    assert missing == 404


def test_add_to_useful_words_translates_once_and_never_duplicates(tmp_path: Path) -> None:
    """C12: фраза ложится в Useful Words с русским переводом; повтор не дублирует."""
    llm = ScriptedLlm([[RUSSIAN]])
    container = one_talk(tmp_path, llm)
    with TestClient(create_app(container)) as client:
        first = client.post(ADD.format(n=0))
        again = client.post(ADD.format(n=0)).json()
        words = client.get("/vocabulary").json()["items"]
    assert first.status_code == 200
    assert first.json() == {"status": "added", "term_en": BETTER, "translation_ru": RUSSIAN}  # C12
    assert again["status"] == "exists" and len(words) == 1  # C12: повтор не дублирует
    word = words[0]
    assert (word["term_en"], word["translation_ru"]) == (BETTER, RUSSIAN)  # C12
    assert word["times_seen"] == 1  # повторный клик — не «встретилось снова»
    # Пример — своя фраза Антона, уже исправленная; контекст — что он сказал и почему.
    assert word["example_en"] == f"Yesterday {BETTER}."
    assert word["context_note_en"] == f"You said: “{SAID}” — past tense"
    assert (word["type"], word["category"], word["session_id"]) == ("phrase", "fluency", "t1")
    # Перевод — один вызов голосовой модели, не R1 (D-8, L57); повтор её не зовёт.
    assert llm.models == [container.settings.ollama_model_interview]
    assert llm.calls[0][-1]["content"] == f"{BETTER}\n\nUsage: Yesterday {BETTER}."


class DownLlm:
    """Ollama не отвечает: клиент бросает `OllamaError` на первом же токене."""

    async def stream_chat(self, messages: Any, **_: Any) -> AsyncIterator[str]:
        raise OllamaError("connection refused")
        yield ""  # делает метод асинхронным генератором, как у настоящего клиента


@pytest.mark.parametrize(
    "llm",
    [ScriptedLlm([["an exhausting day"]]), ScriptedLlm([["утомительный日"]]), DownLlm()],
    ids=["no-cyrillic", "cjk", "ollama-down"],
)
def test_failed_translation_adds_nothing(tmp_path: Path, llm: Any) -> None:
    """C12: перевод судит S-H6, а молчащая модель — не перевод; в банк ничего не идёт."""
    container = one_talk(tmp_path, llm)
    with TestClient(create_app(container)) as client:
        response = client.post(ADD.format(n=1))
        words = client.get("/vocabulary").json()["items"]
    assert response.status_code == 502  # C12
    assert "translation failed" in response.json()["detail"]
    assert words == []  # C12: ни записи с негодным переводом, ни пустой


def test_add_brings_back_a_word_deleted_earlier(tmp_path: Path) -> None:
    """C12: явная просьба сильнее правила «удалённое не добавлять» (doc 10)."""
    llm = ScriptedLlm([["утомительный день"]])
    container = one_talk(tmp_path, llm)
    with TestClient(create_app(container)) as client:
        client.post(ADD.format(n=1))
        word = client.get("/vocabulary").json()["items"][0]
        assert client.delete(f"/vocabulary/{word['id']}").status_code == 204
        back = client.post(ADD.format(n=1)).json()
        words = client.get("/vocabulary").json()["items"]
    assert back["status"] == "added"  # C12: экран не скажет «уже там» про невидимое
    assert [w["id"] for w in words] == [word["id"]]
    assert word["context_note_en"] == "You said: “It was a long day”"  # причины нет — нет и тире
    assert len(llm.calls) == 1  # возврат — без модели


def test_unknown_talk_or_note_is_404(tmp_path: Path) -> None:
    """C12, C11: чужой разговор и номер вне списка — 404, а не чужая заметка."""
    container = one_talk(tmp_path, FakeLlm([]))
    with TestClient(create_app(container)) as client:
        # Контроль: та же заметка по верному адресу находится. Без него тест был бы
        # зелёным и там, где маршрута нет вовсе, — 404 отдал бы сам роутер.
        found = client.get("/sessions/talks/t1/notes/1/audio").status_code
        codes = [
            client.post("/sessions/talks/missing/notes/0/vocabulary").status_code,
            client.post(ADD.format(n=2)).status_code,
            # -1 в Python — последняя заметка: адрес обязан её НЕ найти.
            client.post(ADD.format(n=-1)).status_code,
            client.get("/sessions/talks/missing/notes/0/audio").status_code,
            client.get("/sessions/talks/t1/notes/2/audio").status_code,
        ]
    assert found == 200
    assert codes == [404] * 5


@pytest.mark.parametrize(("stored", "expected"), [(1.45, 1.45), ("fast", 1.15), (9.0, 1.15)])
def test_listen_speaks_the_better_phrase_at_the_stored_pace(
    tmp_path: Path, stored: Any, expected: float
) -> None:
    """C11: WAV лучшего варианта темпом из настроек; вне коридора — темп по умолчанию.

    Проверяется значение КАЖДОГО вызова синтеза, а не записанная настройка (L29).
    """
    container = one_talk(tmp_path, FakeLlm([]), speech_length_scale=stored)
    tts = container.tts
    assert isinstance(tts, FakeTts)
    with TestClient(create_app(container)) as client:
        response = client.get("/sessions/talks/t1/notes/0/audio")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    with wave.open(io.BytesIO(response.content)) as audio:  # настоящий WAV, не байты-заглушка
        assert audio.getnframes() > 0
    assert tts.synthesized == [BETTER]  # C11: звучит лучший вариант, а не сказанное
    assert tts.scales == [expected]  # C11
    assert container.settings.piper_length_scale == 1.15
