"""Summary generation service: full (R1, after review) and minimal (Qwen, on skip).

Recovery per summary.contract.yaml: invalid JSON -> 1 retry with the validator
error appended -> degrade full to minimal -> leave debrief empty (transcripts
are never at risk).
"""

import asyncio
import json
import logging
from typing import Any

from app.common.interfaces import ChatMessage, LlmClient
from app.config import Settings
from app.knowledge.prompts import PromptLibrary
from app.llm.strip_thinking import strip_thinking
from app.storage.repositories.interviews import InterviewRepository
from app.storage.repositories.reviews import ReviewRepository
from app.storage.repositories.vocabulary import VocabularyRepository
from app.summary.validate import SummaryInvalid, extract_json, validate_summary

logger = logging.getLogger(__name__)

SCHEMA_HINT = (
    "Output a single JSON object with fields: overall_summary (string), "
    "scores {clarity, structure, technical_depth, english_fluency, positioning: int 1-5}, "
    "strengths [{text, reference}], "
    "improvements [{category, problem, evidence, impact, fix}], "
    "weak_answers [{question, user_answer_summary, suggested_rephrase, issue}], "
    "vocabulary [{term_en, translation_ru, example_en, category}], "
    "consistency_flags [string], next_session_focus [string]."
)


def _render_transcript(turns: list[dict[str, Any]]) -> str:
    return "\n".join(f"{t['role']}: {t['text']}" for t in turns)


class SummaryService:
    def __init__(
        self,
        llm: LlmClient,
        prompts: PromptLibrary,
        interviews: InterviewRepository,
        reviews: ReviewRepository,
        vocabulary: VocabularyRepository,
        settings: Settings,
    ) -> None:
        self._llm = llm
        self._prompts = prompts
        self._interviews = interviews
        self._reviews = reviews
        self._vocabulary = vocabulary
        self._settings = settings
        self._tasks: set[asyncio.Task[None]] = set()

    def schedule_full(self, interview_id: str, review_id: str) -> None:
        """Fire-and-forget after Mode 2 — latency does not matter offline (D-8)."""
        task = asyncio.create_task(self._safe_full(interview_id, review_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _safe_full(self, interview_id: str, review_id: str) -> None:
        try:
            await self.generate_full(interview_id, review_id)
        except Exception:
            logger.exception("full summary generation failed for %s", interview_id)

    async def generate_full(self, interview_id: str, review_id: str) -> dict[str, Any] | None:
        interview = await self._interviews.get(interview_id)
        review = await self._reviews.get(review_id)
        if interview is None or review is None:
            return None
        interview_text = _render_transcript(json.loads(interview.transcript_json))
        review_text = _render_transcript(json.loads(review.transcript_json))
        user_content = (
            f"{SCHEMA_HINT}\n\n"
            f"INTERVIEW TRANSCRIPT:\n{interview_text}\n\n"
            f"REVIEW TRANSCRIPT:\n{review_text}"
        )
        try:
            data = await self._generate_validated(
                system=self._prompts.system("summary_system"),
                user_content=user_content,
                model=self._settings.ollama_model_review,
                max_tokens=self._settings.summary_max_tokens,
                num_ctx=self._settings.summary_num_ctx,
                require_vocabulary=True,
            )
        except SummaryInvalid:
            logger.warning("full summary invalid twice — degrading to minimal", exc_info=True)
            return await self.generate_minimal(interview_id)
        await self._interviews.set_debrief(interview_id, data, "full")
        added = await self._vocabulary.merge(data["vocabulary"], session_id=interview_id)
        data["vocabulary_added"] = added
        logger.info("full summary stored for %s (%d new vocabulary items)", interview_id, added)
        return data

    async def generate_minimal(self, interview_id: str) -> dict[str, Any] | None:
        interview = await self._interviews.get(interview_id)
        if interview is None:
            return None
        user_content = (
            f"{SCHEMA_HINT}\n\n"
            f"INTERVIEW TRANSCRIPT:\n{_render_transcript(json.loads(interview.transcript_json))}"
        )
        try:
            data = await self._generate_validated(
                system=self._prompts.system("minimal_summary_system"),
                # minimal summary runs on Qwen — already loaded on Skip, no model swap
                user_content=user_content,
                model=self._settings.ollama_model_interview,
                max_tokens=self._settings.minimal_summary_max_tokens,
                num_ctx=self._settings.ollama_num_ctx,
                require_vocabulary=False,
            )
        except SummaryInvalid:
            logger.error("minimal summary invalid twice — leaving debrief empty", exc_info=True)
            return None
        await self._interviews.set_debrief(interview_id, data, "minimal")
        return data

    async def _generate_validated(
        self,
        *,
        system: str,
        user_content: str,
        model: str,
        max_tokens: int,
        num_ctx: int,
        require_vocabulary: bool,
    ) -> dict[str, Any]:
        messages: list[ChatMessage] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        last_error = "invalid output"
        for _ in range(2):  # 1 retry with the validator error appended (S recovery)
            raw = await self._complete(
                messages, model=model, max_tokens=max_tokens, num_ctx=num_ctx
            )
            try:
                return validate_summary(
                    extract_json(strip_thinking(raw)), require_vocabulary=require_vocabulary
                )
            except SummaryInvalid as exc:
                last_error = str(exc)
                messages = [
                    *messages,
                    {"role": "assistant", "content": raw[-2000:]},
                    {
                        "role": "user",
                        "content": f"Your JSON was invalid: {last_error}. "
                        "Return ONLY the corrected JSON object.",
                    },
                ]
        raise SummaryInvalid(last_error)

    async def _complete(
        self, messages: list[ChatMessage], *, model: str, max_tokens: int, num_ctx: int
    ) -> str:
        chunks: list[str] = []
        async for token in self._llm.stream_chat(
            messages,
            model=model,
            temperature=self._settings.summary_temperature,
            max_tokens=max_tokens,
            num_ctx=num_ctx,
        ):
            chunks.append(token)
        return "".join(chunks)
