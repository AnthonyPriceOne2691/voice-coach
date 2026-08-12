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


#: Значение `state` для мета-ходов — просьб о темпе речи и ответа на них (doc 12).
#: Такой ход попадает в транскрипт (он был, и пользователь его слышал), но не
#: относится ни к какому вопросу: `question_id=None` уже исключает его из
#: `build_segments`, а `is_meta` — из промпта суммаризации.
META_STATE = "PACE_REQUEST"


def append_meta(buffer: TranscriptBuffer, user_text: str, agent_text: str) -> None:
    """Record a meta exchange: it happened, but it answers no question."""
    buffer.append("user", user_text, state=META_STATE)
    buffer.append("agent", agent_text, state=META_STATE)


def is_meta(turn: dict[str, Any]) -> bool:
    return turn.get("state") == META_STATE


def last_agent_text(buffer: TranscriptBuffer) -> str:
    """The agent's last spoken line — what "say that again" has to repeat."""
    for turn in reversed(buffer.turns):
        if turn.role == "agent":
            return turn.text
    return ""
