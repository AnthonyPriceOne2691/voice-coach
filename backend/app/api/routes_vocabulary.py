"""REST: Vocabulary Bank tab (doc 10/15)."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from app.container import Container

router = APIRouter()


@router.get("/vocabulary")
async def list_vocabulary(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    sort: str = "recent",
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]:
    container: Container = request.app.state.container
    entries = await container.vocabulary.list(
        query=q, category=category, sort=sort, limit=limit, offset=offset
    )
    return {
        "items": [
            {
                "id": e.id,
                "term_en": e.term_en,
                "translation_ru": e.translation_ru,
                "type": e.type,
                "example_en": e.example_en,
                "context_note_en": e.context_note_en,
                "category": e.category,
                "status": e.status,
                "times_seen": e.times_seen,
                "added_at": e.added_at,
                "session_id": e.session_id,
            }
            for e in entries
        ],
        "total": len(entries),
    }


@router.delete("/vocabulary/{entry_id}", status_code=204)
async def delete_entry(request: Request, entry_id: str) -> Response:
    container: Container = request.app.state.container
    if not await container.vocabulary.soft_delete(entry_id):
        raise HTTPException(status_code=404, detail="entry not found")
    return Response(status_code=204)
