"""Vocabulary Bank persistence with the dedup/merge rules from doc 10."""

# Отложенные аннотации — ради мутационного гейта: под копией mutmut метод `list`
# ниже прячет встроенный `list` из собственной аннотации, и модуль не импортируется
# (сторож — tests/test_mutation_copy.py).
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.db import Database, utcnow_iso
from app.storage.models import VocabularyEntry


async def _by_term(s: AsyncSession, term: str) -> VocabularyEntry | None:
    """Запись с этим термином в ЛЮБОМ статусе: dedup по `term_en` без регистра (doc 10)."""
    stmt = select(VocabularyEntry).where(func.lower(VocabularyEntry.term_en) == term.lower())
    return (await s.execute(stmt)).scalar_one_or_none()


class VocabularyRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def merge(self, items: list[dict[str, Any]], *, session_id: str) -> int:
        """Merge extracted items; returns number of NEW entries added.

        Rules (doc 10): exact term exists -> times_seen += 1; deleted (soft) -> never re-add.
        """
        added = 0
        async with self._db.session() as s:
            for item in items:
                term = str(item.get("term_en", "")).strip()
                translation = str(item.get("translation_ru", "")).strip()
                example = str(item.get("example_en", "")).strip()
                if not term or not translation or not example:
                    continue  # S-H4: incomplete items are dropped, not stored
                existing = await _by_term(s, term)
                if existing is not None:
                    if existing.status != "deleted":
                        existing.times_seen += 1
                    continue
                s.add(
                    VocabularyEntry(
                        id=str(uuid.uuid4()),
                        term_en=term,
                        translation_ru=translation,
                        type=str(item.get("type", "word")),
                        example_en=example,
                        context_note_en=item.get("context_note_en"),
                        session_id=session_id,
                        added_at=utcnow_iso(),
                        category=str(item.get("category", "technical")),
                    )
                )
                added += 1
            await s.commit()
        return added

    async def find_term(self, term: str) -> VocabularyEntry | None:
        """Есть ли термин в банке — включая удалённый человеком (`status='deleted'`)."""
        async with self._db.session() as s:
            return await _by_term(s, term.strip())

    async def restore(self, entry_id: str) -> None:
        """Вернуть удалённую запись наверх списка — по явной просьбе человека.

        Правило doc 10 «удалённое не добавлять снова» защищает банк от экстрактора,
        который предложил бы то же слово после следующей сессии, а не от самого
        человека: нажав «Add to Useful Words», он просит ровно этого.
        """
        async with self._db.session() as s:
            entry = await s.get(VocabularyEntry, entry_id)
            if entry is not None and entry.status == "deleted":
                entry.status = "new"
                entry.added_at = utcnow_iso()
                await s.commit()

    async def set_translation(self, entry_id: str, translation: str) -> bool:
        """Переписать перевод существующей записи (S-H6: починка банка).

        Возвращает `False`, если записи нет: разовый скрипт чистки должен уметь
        сказать «не нашёл», а не молча отчитаться об успехе.
        """
        async with self._db.session() as s:
            entry = await s.get(VocabularyEntry, entry_id)
            if entry is None:
                return False
            entry.translation_ru = translation
            await s.commit()
        return True

    async def list(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        sort: str = "recent",
        limit: int = 200,
        offset: int = 0,
    ) -> list[VocabularyEntry]:
        stmt = select(VocabularyEntry).where(VocabularyEntry.status != "deleted")
        if query:
            stmt = stmt.where(VocabularyEntry.term_en.ilike(f"%{query}%"))
        if category:
            stmt = stmt.where(VocabularyEntry.category == category)
        order = VocabularyEntry.term_en if sort == "alpha" else VocabularyEntry.added_at.desc()
        stmt = stmt.order_by(order).limit(limit).offset(offset)
        async with self._db.session() as s:
            return list((await s.execute(stmt)).scalars())

    async def soft_delete(self, entry_id: str) -> bool:
        async with self._db.session() as s:
            row = await s.get(VocabularyEntry, entry_id)
            if row is None or row.status == "deleted":
                return False
            row.status = "deleted"
            await s.commit()
            return True
