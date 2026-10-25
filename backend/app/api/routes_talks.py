"""REST: разговоры с Генри и их заметки «было → лучше» (doc 15; D3a.2, talk-notes).

Заметки пишет проверка речи (поставка talk-check) в `metadata_json["language_notes"]`
по контракту данных спеки D3a.2; здесь их только читают. Что считать заметкой, решил
код проверки, и экран это не пересматривает.

Модуль — часть поверхности модели (§14.1): он собирает, что видит перевод фразы
(термин — лучший вариант, Usage — фраза Антона с исправленным фрагментом).
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.api.routes_settings import PACE_SETTING
from app.container import Container
from app.llm.ollama_client import OllamaError
from app.orchestrator.pace import in_range
from app.storage.models import TalkSession
from app.summary.validate import translation_problem

logger = logging.getLogger(__name__)

router = APIRouter()

#: Страница History. Граница — не украшение: разговоров с каждым днём больше, а
#: эндпоинт, отдающий всё, ловит гейт unbounded-list.
TALKS_PAGE_MAX = 100

#: Категория банка слов (doc 10) для фраз из разговора: беглость повседневной речи,
#: а не архитектура и не импакт интервью.
NOTE_CATEGORY = "fluency"

_SENTENCE_END = re.compile(r"(?<=[.?!])\s+")


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_note(value: object) -> bool:
    return isinstance(value, dict) and _is_text(value.get("said")) and _is_text(value.get("better"))


def _notes(row: TalkSession) -> list[dict[str, Any]]:
    """Заметки по контракту; ключа нет — пусто (разговоры до talk-check).

    Заметка без строк `said` и `better` — нарушение контракта со стороны записи: она
    пропускается с записью в лог, а не роняет экран и не уезжает в банк слов.
    """
    raw = json.loads(row.metadata_json or "{}").get("language_notes") or []
    notes = [note for note in raw if _is_note(note)]
    if len(notes) != len(raw):
        logger.warning(
            "talk notes outside the contract skipped",
            extra={"talk_id": row.id, "skipped": len(raw) - len(notes)},
        )
    return notes


def _duration_sec(row: TalkSession) -> int | None:
    """По `ended_at`: в метаданных разговора длительности нет, а у брошенного без
    конца число не было бы итогом — History показывает «not finished» (L16)."""
    if not row.ended_at:
        return None
    span = datetime.fromisoformat(row.ended_at) - datetime.fromisoformat(row.started_at)
    return int(span.total_seconds())


def _talk_item(row: TalkSession, notes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": row.id,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "duration_sec": _duration_sec(row),
        "status": row.status,
        "notes_count": len(notes),
    }


async def _talk(request: Request, talk_id: str) -> TalkSession:
    row = await _container(request).talks.get(talk_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"talk {talk_id} not found")
    return row


async def _note(request: Request, talk_id: str, n: int) -> tuple[TalkSession, dict[str, Any]]:
    row = await _talk(request, talk_id)
    notes = _notes(row)
    if not 0 <= n < len(notes):  # -1 в Python — последняя заметка, а не «такой нет»
        raise HTTPException(status_code=404, detail=f"talk {talk_id} has no note {n}")
    return row, notes[n]


@router.get("/sessions/talks")
async def list_talks(
    request: Request,
    limit: int = Query(50, ge=1, le=TALKS_PAGE_MAX),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    rows = await _container(request).talks.list_recent(limit=limit, offset=offset)
    return {"items": [_talk_item(row, _notes(row)) for row in rows]}


@router.get("/sessions/talks/{talk_id}")
async def get_talk(request: Request, talk_id: str) -> dict[str, Any]:
    row = await _talk(request, talk_id)
    notes = _notes(row)
    return {
        **_talk_item(row, notes),
        "transcript": json.loads(row.transcript_json),
        "language_notes": notes,
    }


def _example(said: str, better: str, utterance: str) -> str:
    """Предложение реплики, где стоял фрагмент, — уже с лучшим вариантом.

    Фрагмент дословно стоит в распознанном тексте (инвариант проверки речи); нет его
    там — пример сам лучший вариант, а не чужая фраза.
    """
    sentence = next((s for s in _SENTENCE_END.split(utterance) if said in s), utterance)
    return sentence.replace(said, better, 1) if said in sentence else better


def _word(note: dict[str, Any], transcript: list[dict[str, Any]]) -> dict[str, str]:
    """Запись банка слов (doc 10): своя мысль Антона, лучшими словами."""
    said, better, why = note["said"], note["better"].strip(), note.get("why")
    utterance = next(
        (
            str(t.get("text", ""))
            for t in transcript
            if t.get("turn_index") == note.get("turn_index")
        ),
        "",
    )
    return {
        "term_en": better,
        "example_en": _example(said, better, utterance),
        "context_note_en": f"You said: “{said}”" + (f" — {why}" if _is_text(why) else ""),
        "type": "phrase" if " " in better else "word",
        "category": NOTE_CATEGORY,
    }


async def _translate(container: Container, word: dict[str, str]) -> str:
    """Перевод на голосовой модели тем же путём, что чинит банк (L57), под судом S-H6."""
    term = word["term_en"]
    try:
        translation = await container.summaries.translate_term(term, example=word["example_en"])
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=f"translation failed: {exc}") from exc
    problem = translation_problem(translation)
    if problem is not None:
        logger.warning(
            "talk note translation rejected",
            extra={"term": term, "translation": translation, "problem": problem},
        )
        raise HTTPException(status_code=502, detail=f"translation failed: {problem}")
    return translation


def _outcome(status: str, term: str, translation: str) -> dict[str, str]:
    return {"status": status, "term_en": term, "translation_ru": translation}


@router.post("/sessions/talks/{talk_id}/notes/{n}/vocabulary")
async def add_note_to_vocabulary(request: Request, talk_id: str, n: int) -> dict[str, str]:
    """Лучший вариант → Useful Words (C12). Повтор не дублирует и модель не зовёт."""
    container = _container(request)
    row, note = await _note(request, talk_id, n)
    existing = await container.vocabulary.find_term(note["better"])
    if existing is not None and existing.status != "deleted":
        return _outcome("exists", existing.term_en, existing.translation_ru)
    if existing is not None:  # удалён человеком — и им же попрошен назад
        await container.vocabulary.restore(existing.id)
        return _outcome("added", existing.term_en, existing.translation_ru)
    word = _word(note, json.loads(row.transcript_json))
    word["translation_ru"] = await _translate(container, word)
    added = await container.vocabulary.merge([word], session_id=talk_id)
    return _outcome("added" if added else "exists", word["term_en"], word["translation_ru"])


@router.get("/sessions/talks/{talk_id}/notes/{n}/audio")
async def note_audio(request: Request, talk_id: str, n: int) -> Response:
    """Лучший вариант голосом Генри в темпе пользователя (C11).

    Коридор тот же, что у голосовой сессии: сохранённый темп — если это число в
    коридоре, иначе темп по умолчанию из конфига. Темп — аргумент вызова синтеза.
    """
    container = _container(request)
    _, note = await _note(request, talk_id, n)
    stored = (await container.user_settings.get_all()).get(PACE_SETTING)
    scale = container.settings.piper_length_scale
    if isinstance(stored, int | float) and in_range(float(stored)):
        scale = float(stored)
    wav = await container.tts.synthesize(note["better"], length_scale=scale)
    return Response(content=wav, media_type="audio/wav")
