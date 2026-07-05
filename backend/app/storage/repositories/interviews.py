"""CRUD for interview_sessions. Flush-first: checkpoint on every turn (NFR-4.2)."""

import json
from typing import Any

from sqlalchemy import delete, select

from app.storage.db import Database, utcnow_iso
from app.storage.models import InterviewSession, ReviewSession


class InterviewRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, session_id: str, *, interview_mode: str, persona: str) -> None:
        async with self._db.session() as s:
            s.add(
                InterviewSession(
                    id=session_id,
                    started_at=utcnow_iso(),
                    interview_mode=interview_mode,
                    persona=persona,
                    created_at=utcnow_iso(),
                )
            )
            await s.commit()

    async def checkpoint(
        self, session_id: str, turns: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> None:
        async with self._db.session() as s:
            row = await s.get(InterviewSession, session_id)
            if row is None:
                return
            row.transcript_json = json.dumps(turns, ensure_ascii=False)
            row.metadata_json = json.dumps(metadata, ensure_ascii=False)
            await s.commit()

    async def finish(self, session_id: str, *, status: str) -> None:
        async with self._db.session() as s:
            row = await s.get(InterviewSession, session_id)
            if row is None:
                return
            row.ended_at = utcnow_iso()
            row.status = status
            await s.commit()

    async def set_debrief(self, session_id: str, debrief: dict[str, Any], kind: str) -> None:
        async with self._db.session() as s:
            row = await s.get(InterviewSession, session_id)
            if row is None:
                return
            row.debrief_json = json.dumps(debrief, ensure_ascii=False)
            row.summary_kind = kind
            await s.commit()

    async def link_review(self, session_id: str, review_id: str) -> None:
        async with self._db.session() as s:
            row = await s.get(InterviewSession, session_id)
            if row is None:
                return
            row.review_session_id = review_id
            await s.commit()

    async def get(self, session_id: str) -> InterviewSession | None:
        async with self._db.session() as s:
            return await s.get(InterviewSession, session_id)

    async def list_recent(self, *, limit: int = 50, offset: int = 0) -> list[InterviewSession]:
        async with self._db.session() as s:
            result = await s.execute(
                select(InterviewSession)
                .order_by(InterviewSession.started_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars())

    async def delete_cascade(self, session_id: str) -> bool:
        """Delete interview + linked reviews (doc 15 DELETE semantics)."""
        async with self._db.session() as s:
            row = await s.get(InterviewSession, session_id)
            if row is None:
                return False
            await s.execute(
                delete(ReviewSession).where(ReviewSession.source_interview_id == session_id)
            )
            await s.delete(row)
            await s.commit()
            return True
