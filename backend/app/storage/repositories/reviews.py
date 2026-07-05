"""CRUD for review_sessions (Mode 2)."""

import json
from typing import Any

from sqlalchemy import select

from app.storage.db import Database, utcnow_iso
from app.storage.models import ReviewSession


class ReviewRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, review_id: str, *, source_interview_id: str, persona: str) -> None:
        async with self._db.session() as s:
            s.add(
                ReviewSession(
                    id=review_id,
                    source_interview_id=source_interview_id,
                    started_at=utcnow_iso(),
                    persona=persona,
                    created_at=utcnow_iso(),
                )
            )
            await s.commit()

    async def checkpoint(
        self, review_id: str, turns: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> None:
        async with self._db.session() as s:
            row = await s.get(ReviewSession, review_id)
            if row is None:
                return
            row.transcript_json = json.dumps(turns, ensure_ascii=False)
            row.metadata_json = json.dumps(metadata, ensure_ascii=False)
            await s.commit()

    async def finish(self, review_id: str, *, status: str) -> None:
        async with self._db.session() as s:
            row = await s.get(ReviewSession, review_id)
            if row is None:
                return
            row.ended_at = utcnow_iso()
            row.status = status
            await s.commit()

    async def get(self, review_id: str) -> ReviewSession | None:
        async with self._db.session() as s:
            return await s.get(ReviewSession, review_id)

    async def for_interview(self, interview_id: str) -> list[ReviewSession]:
        async with self._db.session() as s:
            result = await s.execute(
                select(ReviewSession)
                .where(ReviewSession.source_interview_id == interview_id)
                .order_by(ReviewSession.started_at.desc())
            )
            return list(result.scalars())
