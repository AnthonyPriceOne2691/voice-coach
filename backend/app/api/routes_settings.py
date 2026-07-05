"""REST: user settings (kv in app.db, doc 12/15)."""

from typing import Any

from fastapi import APIRouter, Request

from app.container import Container

router = APIRouter()


@router.get("/settings")
async def get_settings(request: Request) -> dict[str, Any]:
    container: Container = request.app.state.container
    return await container.user_settings.get_all()


@router.patch("/settings")
async def patch_settings(request: Request, patch: dict[str, Any]) -> dict[str, Any]:
    container: Container = request.app.state.container
    return await container.user_settings.update(patch)
