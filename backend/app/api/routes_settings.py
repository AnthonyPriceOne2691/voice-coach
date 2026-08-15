"""REST: user settings (kv in app.db, doc 12/15)."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.container import Container
from app.orchestrator.pace import PACE_FASTEST, PACE_SLOWEST, in_range

router = APIRouter()

PACE_SETTING = "speech_length_scale"
MIC_SETTING = "mic_device_id"
# Ограничение от мусора, а не от злоумышленника: `deviceId` у Chromium — 44
# символа base64, у Firefox короче. Локальный инструмент на одного человека.
MIC_ID_MAX_LEN = 256


def _validate_pace(patch: dict[str, Any]) -> None:
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


def _validate_mic(patch: dict[str, Any]) -> None:
    """Идентификатор входа — строка или `null` (системный по умолчанию).

    Сервер не знает и не может знать, существует ли такое устройство: `deviceId`
    выдаёт браузер, и он же его «солит» под origin. Поэтому здесь проверяется
    только форма, а живучесть выбора — забота клиента, который при пропаже входа
    обязан сказать об этом вслух, а не тихо переехать на другой микрофон.
    """
    if MIC_SETTING not in patch:
        return
    value = patch[MIC_SETTING]
    if value is not None and (not isinstance(value, str) or len(value) > MIC_ID_MAX_LEN):
        raise HTTPException(
            status_code=422,
            detail=(
                f"{MIC_SETTING} must be a string of at most {MIC_ID_MAX_LEN} chars or null, "
                f"got {value!r}"
            ),
        )


def _validate(patch: dict[str, Any]) -> None:
    _validate_pace(patch)
    _validate_mic(patch)


@router.get("/settings")
async def get_settings(request: Request) -> dict[str, Any]:
    container: Container = request.app.state.container
    return await container.user_settings.get_all()


@router.patch("/settings")
async def patch_settings(request: Request, patch: dict[str, Any]) -> dict[str, Any]:
    container: Container = request.app.state.container
    _validate(patch)
    return await container.user_settings.update(patch)
