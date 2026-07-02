"""Voice turn pipeline: STT -> LLM (streaming) -> per-sentence TTS (docs 03, 13)."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from app.common.interfaces import ChatMessage, LlmClient, SpeechToText, TextToSpeech
from app.common.sentences import SentenceChunker


class SttEmptyError(RuntimeError):
    """User utterance produced no usable transcript (doc 15: STT_EMPTY)."""


@dataclass(frozen=True)
class UserTranscribed:
    text: str


@dataclass(frozen=True)
class AgentSentence:
    text: str
    wav: bytes
    index: int


@dataclass(frozen=True)
class AgentCompleted:
    text: str


TurnEvent = UserTranscribed | AgentSentence | AgentCompleted


@dataclass(frozen=True)
class LlmParams:
    model: str
    temperature: float
    max_tokens: int


class VoiceTurnPipeline:
    """One user turn end-to-end. Sentence-gated: TTS starts on the first full sentence."""

    def __init__(
        self,
        stt: SpeechToText,
        llm: LlmClient,
        tts: TextToSpeech,
        *,
        min_transcript_words: int = 2,
    ) -> None:
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._min_words = min_transcript_words

    async def run_turn(
        self,
        wav_path: Path,
        messages: list[ChatMessage],
        params: LlmParams,
    ) -> AsyncIterator[TurnEvent]:
        user_text = await self._stt.transcribe(wav_path)
        if len(user_text.split()) < self._min_words:
            raise SttEmptyError(f"transcript too short: {user_text!r}")
        yield UserTranscribed(text=user_text)

        chat = [*messages, {"role": "user", "content": user_text}]
        chunker = SentenceChunker()
        sentences: list[str] = []
        async for token in self._llm.stream_chat(
            chat,
            model=params.model,
            temperature=params.temperature,
            max_tokens=params.max_tokens,
        ):
            for sentence in chunker.push(token):
                sentences.append(sentence)
                yield AgentSentence(
                    text=sentence,
                    wav=await self._tts.synthesize(sentence),
                    index=len(sentences) - 1,
                )
        tail = chunker.flush()
        if tail is not None:
            sentences.append(tail)
            yield AgentSentence(
                text=tail,
                wav=await self._tts.synthesize(tail),
                index=len(sentences) - 1,
            )
        yield AgentCompleted(text=" ".join(sentences))
