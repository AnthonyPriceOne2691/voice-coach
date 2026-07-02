"""JSON-file transcript log — Phase 1 exit criterion "transcript logged to JSON file".

Turn format follows doc 12 (role, text, timestamp_ms, turn_index); flushed on every
append so a crash never loses more than the in-flight turn (NFR-4.2).
"""

import json
import time
from pathlib import Path
from typing import Any


class TranscriptLog:
    def __init__(self, sessions_dir: Path, session_id: str) -> None:
        sessions_dir.mkdir(parents=True, exist_ok=True)
        self._path = sessions_dir / f"{session_id}.json"
        self._started = time.monotonic()
        self._turns: list[dict[str, Any]] = []
        self._flush()

    @property
    def path(self) -> Path:
        return self._path

    def append(self, role: str, text: str) -> None:
        self._turns.append(
            {
                "role": role,
                "text": text,
                "timestamp_ms": int((time.monotonic() - self._started) * 1000),
                "turn_index": len(self._turns),
            }
        )
        self._flush()

    def _flush(self) -> None:
        self._path.write_text(
            json.dumps(self._turns, ensure_ascii=False, indent=2), encoding="utf-8"
        )
