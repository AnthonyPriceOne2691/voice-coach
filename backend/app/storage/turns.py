"""Transcript turn format (doc 12): role, text, timestamp_ms, turn_index, state, question_id."""

import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Turn:
    role: str  # agent | user
    text: str
    timestamp_ms: int
    turn_index: int
    state: str | None = None
    question_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TranscriptBuffer:
    """In-memory transcript for a live session; repositories persist it per turn."""

    _started: float = field(default_factory=time.monotonic)
    turns: list[Turn] = field(default_factory=list)

    def append(
        self, role: str, text: str, *, state: str | None = None, question_id: str | None = None
    ) -> Turn:
        turn = Turn(
            role=role,
            text=text,
            timestamp_ms=int((time.monotonic() - self._started) * 1000),
            turn_index=len(self.turns),
            state=state,
            question_id=question_id,
        )
        self.turns.append(turn)
        return turn

    def to_json_list(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.turns]
