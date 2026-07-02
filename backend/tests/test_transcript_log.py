import json
from pathlib import Path

from app.storage.transcript_log import TranscriptLog


def test_appends_turns_with_indices(tmp_path: Path) -> None:
    log = TranscriptLog(tmp_path, "session-1")
    log.append("agent", "Hello.")
    log.append("user", "Hi there.")

    turns = json.loads(log.path.read_text())
    assert [t["turn_index"] for t in turns] == [0, 1]
    assert turns[0] == {
        "role": "agent",
        "text": "Hello.",
        "timestamp_ms": turns[0]["timestamp_ms"],
        "turn_index": 0,
    }
    assert turns[1]["role"] == "user"


def test_flushes_on_every_append(tmp_path: Path) -> None:
    log = TranscriptLog(tmp_path, "session-2")
    assert json.loads(log.path.read_text()) == []  # file exists immediately
    log.append("agent", "One.")
    assert len(json.loads(log.path.read_text())) == 1


def test_creates_sessions_dir(tmp_path: Path) -> None:
    nested = tmp_path / "does" / "not" / "exist"
    log = TranscriptLog(nested, "s")
    assert log.path.exists()
