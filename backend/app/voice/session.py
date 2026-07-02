"""In-memory voice session state for the Phase 1 echo interviewer (no orchestrator yet)."""

from app.common.interfaces import ChatMessage
from app.storage.transcript_log import TranscriptLog


class VoiceSession:
    """Holds chat history (system prompt stable prefix first — doc 20 KV-cache rule)."""

    def __init__(self, session_id: str, system_prompt: str, log: TranscriptLog) -> None:
        self.session_id = session_id
        self._system_prompt = system_prompt
        self._history: list[ChatMessage] = []
        self.log = log

    @property
    def messages(self) -> list[ChatMessage]:
        return [{"role": "system", "content": self._system_prompt}, *self._history]

    def add_user(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})
        self.log.append("user", text)

    def add_agent(self, text: str) -> None:
        self._history.append({"role": "assistant", "content": text})
        self.log.append("agent", text)
