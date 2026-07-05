"""Enforced agent generation: LLM stream -> sentence gate -> TTS (doc 13 runtime pipeline).

Recovery ladder:
  * violation on sentence 1 (nothing spoken yet) -> regenerate once with a strict
    hint -> template fallback (the orchestrator seed line, always safe to speak)
  * violation on sentence i>1 -> truncate: the offending sentence never reaches TTS
  * empty stream (e.g. thinking model ate the budget, I2-H5) -> same ladder
  * turn-level question_or_ack failure -> additively append the seed question
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.common.interfaces import ChatMessage, LlmClient, TextToSpeech
from app.common.sentences import SentenceChunker
from app.contracts.enforcer import ContractEnforcer, TurnContext, TurnEnforcer, Violation


@dataclass(frozen=True)
class AgentSentence:
    text: str
    wav: bytes
    index: int


@dataclass(frozen=True)
class AgentCompleted:
    text: str
    fallback_used: bool = False
    violations: list[dict[str, Any]] = field(default_factory=list)


TurnEvent = AgentSentence | AgentCompleted


@dataclass(frozen=True)
class LlmParams:
    model: str
    temperature: float
    max_tokens: int


STRICT_REGENERATE = (
    "Your previous reply violated interview rules: {violation}. "
    "Rewrite in English only. Max 3 sentences. One question OR a short acknowledgment. "
    "No coaching, praise, or scoring. Original intent: {intent}"
)


class TurnRunner:
    def __init__(self, llm: LlmClient, tts: TextToSpeech) -> None:
        self._llm = llm
        self._tts = tts

    async def run(
        self,
        messages: list[ChatMessage],
        params: LlmParams,
        *,
        enforcer: ContractEnforcer | None = None,
        ctx: TurnContext | None = None,
        seed: str = "",
        intent: str = "",
        turn_index: int = 0,
    ) -> AsyncIterator[TurnEvent]:
        context = ctx or TurnContext()
        events: list[dict[str, Any]] = []
        attempts = (enforcer.spec.max_retries if enforcer else 0) + 1
        chat = list(messages)

        for attempt in range(attempts):
            turn = enforcer.start_turn(context) if enforcer else None
            spoken: list[str] = []
            need_regenerate = False

            async for sentence in self._sentences(chat, params):
                verdict = self._gate(turn, sentence, events, context, turn_index)
                if verdict == "speak":
                    spoken.append(sentence)
                    yield AgentSentence(
                        text=sentence,
                        wav=await self._tts.synthesize(sentence),
                        index=len(spoken) - 1,
                    )
                elif verdict == "truncate":
                    break  # spoken prefix is compliant; drop the rest of the stream
                else:  # regenerate — nothing spoken yet
                    need_regenerate = True
                    break

            if spoken:
                # turn-level check: additively recoverable, nothing spoken is retracted
                violation = turn.finish() if turn else None
                if violation is not None:
                    events.append(
                        self._event(violation, context, "append_seed_question", turn_index)
                    )
                    spoken.append(seed)
                    yield AgentSentence(
                        text=seed, wav=await self._tts.synthesize(seed), index=len(spoken) - 1
                    )
                yield AgentCompleted(text=" ".join(spoken), violations=events)
                return

            # nothing spoken: contract violation on sentence 1 or an empty stream
            if not need_regenerate:
                events.append(self._empty_stream_event(context, turn_index))
            if attempt + 1 < attempts:
                hint = events[-1]["constraint_id"] if events else "contract violation"
                chat = [
                    *messages,
                    {
                        "role": "user",
                        "content": STRICT_REGENERATE.format(violation=hint, intent=intent),
                    },
                ]

        yield AgentSentence(text=seed, wav=await self._tts.synthesize(seed), index=0)
        yield AgentCompleted(text=seed, fallback_used=True, violations=events)

    async def _sentences(self, chat: list[ChatMessage], params: LlmParams) -> AsyncIterator[str]:
        chunker = SentenceChunker()
        async for token in self._llm.stream_chat(
            chat, model=params.model, temperature=params.temperature, max_tokens=params.max_tokens
        ):
            for sentence in chunker.push(token):
                yield sentence
        tail = chunker.flush()
        if tail is not None:
            yield tail

    def _gate(
        self,
        turn: TurnEnforcer | None,
        sentence: str,
        events: list[dict[str, Any]],
        ctx: TurnContext,
        turn_index: int,
    ) -> str:
        if turn is None:
            return "speak"
        violation = turn.feed(sentence)
        if violation is None:
            return "speak"
        recovery = "truncate" if turn.sentences else "regenerate"
        events.append(self._event(violation, ctx, recovery, turn_index))
        return recovery

    @staticmethod
    def _event(
        violation: Violation, ctx: TurnContext, recovery: str, turn_index: int
    ) -> dict[str, Any]:
        return {
            "turn_index": turn_index,
            "state": ctx.state,
            "constraint_id": violation.rule_id,
            "severity": violation.severity,
            "sentence_index": violation.sentence_index,
            "matched": violation.matched,
            "recovery": recovery,
            "recovered": True,
        }

    @staticmethod
    def _empty_stream_event(ctx: TurnContext, turn_index: int) -> dict[str, Any]:
        return {
            "turn_index": turn_index,
            "state": ctx.state,
            "constraint_id": "EMPTY_STREAM",
            "severity": "hard",
            "sentence_index": 0,
            "matched": "",
            "recovery": "regenerate",
            "recovered": True,
        }
