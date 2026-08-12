"""Key-value user settings in the same app.db (doc 12)."""

import json
from typing import Any

from app.storage.db import Database, utcnow_iso
from app.storage.models import Setting

DEFAULTS: dict[str, Any] = {
    "show_live_transcript": True,
    "interview_duration_min": 15,
    "silence_threshold_ms": 1200,
}


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_all(self) -> dict[str, Any]:
        values = dict(DEFAULTS)
        async with self._db.session() as s:
            for row in (await s.execute(Setting.__table__.select())).all():
                # DEFAULTS — три ключа, выборка ограничена ими же: это не
                # растущая коллекция, а фиксированный набор настроек.
                values[row.key] = json.loads(row.value_json)  # cpu-ok: 3 ключа настроек
        return values

    async def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        async with self._db.session() as s:
            for key, value in patch.items():
                if key not in DEFAULTS:
                    continue
                row = await s.get(Setting, key)
                if row is None:
                    payload = json.dumps(value)  # cpu-ok: цикл по patch ⊆ DEFAULTS (3 ключа)
                    s.add(Setting(key=key, value_json=payload, updated_at=utcnow_iso()))
                else:
                    row.value_json = json.dumps(value)  # cpu-ok: тот же цикл на 3 ключа
                    row.updated_at = utcnow_iso()
            await s.commit()
        return await self.get_all()
