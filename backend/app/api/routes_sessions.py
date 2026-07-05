"""REST: sessions history + summaries (doc 15)."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from app.container import Container
from app.storage.models import InterviewSession

router = APIRouter()


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def _interview_item(row: InterviewSession) -> dict[str, Any]:
    metadata = json.loads(row.metadata_json or "{}")
    return {
        "id": row.id,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "interview_mode": row.interview_mode,
        "duration_sec": metadata.get("duration_sec"),
        "status": row.status,
        "has_review": row.review_session_id is not None,
        "review_session_id": row.review_session_id,
        "has_debrief": row.debrief_json is not None,
        "summary_kind": row.summary_kind,
    }


@router.get("/sessions/interviews")
async def list_interviews(request: Request, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    rows = await _container(request).interviews.list_recent(limit=limit, offset=offset)
    return {"items": [_interview_item(r) for r in rows], "total": len(rows)}


@router.get("/sessions/interviews/{interview_id}")
async def get_interview(request: Request, interview_id: str) -> dict[str, Any]:
    row = await _container(request).interviews.get(interview_id)
    if row is None:
        raise HTTPException(status_code=404, detail="interview not found")
    return {
        **_interview_item(row),
        "transcript": json.loads(row.transcript_json),
        "metadata": json.loads(row.metadata_json or "{}"),
        "debrief": json.loads(row.debrief_json) if row.debrief_json else None,
    }


@router.get("/sessions/reviews/{review_id}")
async def get_review(request: Request, review_id: str) -> dict[str, Any]:
    row = await _container(request).reviews.get(review_id)
    if row is None:
        raise HTTPException(status_code=404, detail="review not found")
    return {
        "id": row.id,
        "source_interview_id": row.source_interview_id,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "status": row.status,
        "transcript": json.loads(row.transcript_json),
        "metadata": json.loads(row.metadata_json or "{}"),
    }


@router.post("/sessions/interviews/{interview_id}/minimal-summary")
async def minimal_summary(request: Request, interview_id: str) -> dict[str, Any]:
    container = _container(request)
    if await container.interviews.get(interview_id) is None:
        raise HTTPException(status_code=404, detail="interview not found")
    debrief = await container.summaries.generate_minimal(interview_id)
    if debrief is None:
        raise HTTPException(status_code=502, detail="summary generation failed")
    return {"interview_id": interview_id, "debrief": debrief, "summary_kind": "minimal"}


@router.delete("/sessions/interviews/{interview_id}", status_code=204)
async def delete_interview(request: Request, interview_id: str) -> Response:
    deleted = await _container(request).interviews.delete_cascade(interview_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="interview not found")
    return Response(status_code=204)
