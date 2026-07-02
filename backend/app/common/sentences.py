"""Incremental sentence chunker for streaming LLM -> TTS (doc 03, doc 13 sentence-gating)."""

import re

# Split on whitespace after ./?/! (optionally followed by ONE closing quote/bracket,
# kept with the sentence — lookbehind must be fixed-width).
_BOUNDARY = re.compile(r"(?<=[.?!][\"')\]])\s+|(?<=[.?!])\s+")


class SentenceChunker:
    """Accumulates streamed tokens and releases complete sentences."""

    def __init__(self) -> None:
        self._buffer = ""

    def push(self, token: str) -> list[str]:
        """Add a token; return any sentences completed by it."""
        self._buffer += token
        parts = _BOUNDARY.split(self._buffer)
        if len(parts) <= 1:
            return []
        self._buffer = parts[-1]
        return [p.strip() for p in parts[:-1] if p.strip()]

    def flush(self) -> str | None:
        """Return the trailing partial sentence at end of stream, if any."""
        tail = self._buffer.strip()
        self._buffer = ""
        return tail or None
