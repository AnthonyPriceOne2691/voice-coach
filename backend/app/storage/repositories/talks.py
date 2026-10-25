"""CRUD for talk_sessions (D3a): flush-first, checkpoint on every turn (NFR-4.2)."""

import json
from typing import Any

from sqlalchemy import select

from app.storage.db import Database, utcnow_iso
from app.storage.models import TalkSession


class TalkRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, talk_id: str, *, persona: str) -> None:
        async with self._db.session() as s:
            now = utcnow_iso()
            s.add(TalkSession(id=talk_id, started_at=now, persona=persona, created_at=now))
            await s.commit()

    async def checkpoint(
        self, talk_id: str, turns: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> None:
        await self._update(
            talk_id,
            transcript_json=json.dumps(turns, ensure_ascii=False),
            metadata_json=json.dumps(metadata, ensure_ascii=False),
        )

    async def finish(self, talk_id: str, *, status: str) -> None:
        await self._update(talk_id, ended_at=utcnow_iso(), status=status)

    async def get(self, talk_id: str) -> TalkSession | None:
        async with self._db.session() as s:
            return await s.get(TalkSession, talk_id)

    async def list_recent(self, *, limit: int, offset: int = 0) -> list[TalkSession]:
        """Страница History, новые первыми. Без умолчания у `limit`: граница — решение
        вызывающего, а разговоров с каждым днём только больше."""
        stmt = select(TalkSession).order_by(TalkSession.started_at.desc())
        async with self._db.session() as s:
            return list((await s.execute(stmt.limit(limit).offset(offset))).scalars())

    async def _update(self, talk_id: str, **fields: str) -> None:
        async with self._db.session() as s:
            row = await s.get(TalkSession, talk_id)
            if row is None:
                return
            for name, value in fields.items():
                setattr(row, name, value)
            await s.commit()
