"""Per-session speaking tempo on top of a shared TTS voice.

Why an adapter and not a parameter threaded through every call: synthesis is
invoked from four places, and `TurnRunner` is one of them. Passing the tempo
through `run()` would hand the runner a decision it does not own (I1-H6) —
the wrapper keeps that signature untouched.

Why per session and not per process: the voice model is expensive and stays
shared (doc 19 note 4), but the tempo is one user's request inside one session
and must not leak into another.
"""

from app.common.interfaces import TextToSpeech


class PacedTts:
    """Implements TextToSpeech; holds the mutable tempo the session speaks at."""

    def __init__(self, inner: TextToSpeech, *, scale: float) -> None:
        self._inner = inner
        self._scale = scale

    @property
    def scale(self) -> float:
        return self._scale

    def set_scale(self, scale: float) -> None:
        """Takes effect from the next synthesis — callers set it BEFORE speaking."""
        self._scale = scale

    async def synthesize(self, text: str, *, length_scale: float | None = None) -> bytes:
        return await self._inner.synthesize(
            text, length_scale=self._scale if length_scale is None else length_scale
        )
