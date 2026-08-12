"""REST: user settings (kv in app.db, doc 12/15)."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.container import Container
from app.orchestrator.pace import PACE_FASTEST, PACE_SLOWEST, in_range

router = APIRouter()

PACE_SETTING = "speech_length_scale"


def _validate(patch: dict[str, Any]) -> None:
    """Темп вне коридора отвергается, а не зажимается молча.

    Молчаливый зажим неотличим от принятого значения: клиент получил бы 200 и
    решил, что настройка применена. Это тот же класс, что «данные доехали, а
    поведение другое» (L20) — только со стороны API.
    """
    if PACE_SETTING not in patch:
        return
    value = patch[PACE_SETTING]
    if isinstance(value, bool) or not isinstance(value, int | float) or not in_range(float(value)):
        raise HTTPException(
            status_code=422,
            detail=(
                f"{PACE_SETTING} must be a number in [{PACE_FASTEST}, {PACE_SLOWEST}], "
                f"got {value!r}"
            ),
        )


@router.get("/settings")
async def get_settings(request: Request) -> dict[str, Any]:
    container: Container = request.app.state.container
    return await container.user_settings.get_all()


@router.patch("/settings")
async def patch_settings(request: Request, patch: dict[str, Any]) -> dict[str, Any]:
    container: Container = request.app.state.container
    _validate(patch)
    return await container.user_settings.update(patch)
