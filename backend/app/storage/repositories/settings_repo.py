"""Key-value user settings in the same app.db (doc 12)."""

import json
from typing import Any

from app.storage.db import Database, utcnow_iso
from app.storage.models import Setting

DEFAULTS: dict[str, Any] = {
    "show_live_transcript": True,
    "interview_duration_min": 15,
    "silence_threshold_ms": 1200,
    # Темп речи. Значение здесь перекрывается контейнером из
    # `Settings.piper_length_scale` — литерал оставлен, чтобы репозиторий был
    # самодостаточен вне приложения, и сторожится тестом на совпадение с
    # конфигом: два файла, каждый со своей половиной правды, — это L11.
    "speech_length_scale": 1.15,
    # Микрофонный вход. `None` = системный по умолчанию, то есть поведение до
    # появления настройки. Значение браузерное (`MediaDeviceInfo.deviceId`) и
    # протухает при очистке данных сайта — потерю обязан ЗАМЕТИТЬ клиент, здесь
    # это просто строка.
    "mic_device_id": None,
}


class SettingsRepository:
    def __init__(self, db: Database, *, defaults: dict[str, Any] | None = None) -> None:
        self._db = db
        self._defaults = {**DEFAULTS, **(defaults or {})}

    async def get_all(self) -> dict[str, Any]:
        values = dict(self._defaults)
        async with self._db.session() as s:
            for row in (await s.execute(Setting.__table__.select())).all():
                # DEFAULTS — пять ключей, выборка ограничена ими же: это не
                # растущая коллекция, а фиксированный набор настроек.
                values[row.key] = json.loads(row.value_json)  # cpu-ok: 5 ключей настроек
        return values

    async def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        async with self._db.session() as s:
            for key, value in patch.items():
                if key not in self._defaults:
                    continue
                row = await s.get(Setting, key)
                if row is None:
                    payload = json.dumps(value)  # cpu-ok: цикл по patch ⊆ DEFAULTS (5 ключей)
                    s.add(Setting(key=key, value_json=payload, updated_at=utcnow_iso()))
                else:
                    row.value_json = json.dumps(value)  # cpu-ok: тот же цикл на 5 ключей
                    row.updated_at = utcnow_iso()
            await s.commit()
        return await self.get_all()
