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
from app.storage.turns import is_meta
from app.summary.validate import (
    SummaryInvalidError,
    extract_json,
    translation_problem,
    validate_summary,
)

logger = logging.getLogger(__name__)

#: Сколько гашение приложения ждёт фоновые суммаризации. Порядок тот же, что у
#: слива ws-сессий: секунды. Дольше — значит LLM висит, и держать ради этого
#: закрытие процесса нельзя.
SHUTDOWN_SUMMARY_TIMEOUT_S = 10.0

#: Перевод одного термина — это строка, а не текст. Потолок держит модель от
#: рассуждений вслух, которые всё равно пришлось бы отрезать.
TERM_TRANSLATION_MAX_TOKENS = 64

#: Поля-списки записаны массивом С ПРИМЕРОМ элемента. До 2026-09-29 здесь стояло
#: `next_session_focus [string]`, и R1 прочёл это как «строка». Форму всё равно
#: приводит валидатор (`validate.py`), а сторож в `test_summary.py` выводит
#: поля-списки из ЭТОЙ строки: новое поле `[...]` без приведения — красный тест.
SCHEMA_HINT = (
    "Output a single JSON object with fields: overall_summary (string), "
    "scores {clarity, structure, technical_depth, english_fluency, positioning: int 1-5}, "
    "strengths [{text, reference}], "
    "improvements [{category, problem, evidence, impact, fix}], "
    "weak_answers [{question, user_answer_summary, suggested_rephrase, issue}], "
    "vocabulary [{term_en, translation_ru, example_en, category}], "
    'consistency_flags ["...", "..."], next_session_focus ["...", "..."]. '
    "Every field shown with [ ] is a JSON array, even when it holds one item: "
    "consistency_flags and next_session_focus are arrays of strings, never a single string."
)


def _render_transcript(turns: list[dict[str, Any]]) -> str:
    """Мета-ходы отброшены: просьба «speak slower» — не реплика кандидата.

    Она произошла и осталась в транскрипте, но в разборе выглядела бы ответом
    и попала бы в оценку словарного запаса и в evidence.
    """
    return "\n".join(f"{t['role']}: {t['text']}" for t in turns if not is_meta(t))


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

    async def aclose(self) -> None:
        """Дождаться фоновых суммаризаций перед гашением приложения.

        «Fire-and-forget» отвечает за латентность, а не за живучесть: задача всё
        равно пишет в БД, и оборванная на середине запись оставляет соединение
        вне пула. Ровно этот класс подвесил прогон в ws-сессии (diagnosis.md той
        же поставки), просто там сирота была видимее. Здесь — та же дверь.

        Не уложилась в срок — ОТМЕНИТЬ и ДОЖДАТЬСЯ отмены: это два шага (L90).
        Отмена без ожидания только помечена, а выход из `async with db.session()`
        сам требует `await` (rollback и возврат соединения): `dispose()` движка
        прошёл бы раньше, и соединение осталось бы вне пула (поставка
        shutdown-leaks, E1). Второй шаг — без срока: выход процесса этих задач
        всё равно дождётся (`asyncio.run` ждёт отменённые задачи без срока),
        так что срок здесь ничего бы не ограничил, а только пустил бы `dispose()`
        вперёд размотки.

        Срок ожидания — константа модуля, а не параметр (ASYNC109): у гашения он
        один на всё приложение, и прятать его в аргумент по умолчанию значит
        разрешить двум вызывающим ждать по-разному без причины.
        """
        if not self._tasks:
            return
        _, pending = await asyncio.wait(set(self._tasks), timeout=SHUTDOWN_SUMMARY_TIMEOUT_S)
        if not pending:
            return
        logger.warning("shutdown: %d summary task(s) cancelled by timeout", len(pending))
        for task in pending:
            task.cancel()
        await asyncio.wait(pending)

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
        except SummaryInvalidError:
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
        except SummaryInvalidError:
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
                data = validate_summary(
                    extract_json(strip_thinking(raw)), require_vocabulary=require_vocabulary
                )
                # Одно место на ОБА пути (full на R1 и minimal на qwen): второй
                # сайт вставки разъехался бы с первым, как уже бывало (L11/L39).
                data["vocabulary"] = await self._repair_vocabulary(data["vocabulary"])
                return data
            except SummaryInvalidError as exc:
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
        raise SummaryInvalidError(last_error)

    async def _repair_vocabulary(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """S-H6: перевод обязан быть русским — испорченный чинится, потеря звучит.

        Порядок именно такой: сначала попытка вернуть слово, и только потом
        отказ. `impact statement` — полезный термин, и терять его из-за двух
        иероглифов жалко, когда повторный перевод стоит одного офлайн-вызова.

        Отброшенная запись ПИШЕТСЯ В ЛОГ с термином: молчаливая пропажа
        неотличима от «модель не предложила слово», а это разные события.
        """
        kept: list[dict[str, Any]] = []
        for item in items:
            translation = str(item.get("translation_ru", ""))
            problem = translation_problem(translation)  # cpu-ok: 5–12 записей (S-H4)
            if problem is None:
                kept.append(item)
                continue
            term = str(item.get("term_en", ""))
            # Пример употребления идёт вместе с термином: перевод вслепую
            # даёт «заявление об impactе» — замерено живым прогоном на банке.
            fixed = await self.translate_term(term, example=str(item.get("example_en", "")))
            if translation_problem(fixed) is None:  # cpu-ok: тот же цикл на 5–12 записей
                logger.info(
                    "vocabulary: перевод термина %r починен (%r -> %r)", term, translation, fixed
                )
                kept.append({**item, "translation_ru": fixed})
            else:
                logger.warning(
                    "vocabulary: запись %r отброшена — перевод %r (%s), починка вернула %r",
                    term,
                    translation,
                    problem,
                    fixed,
                )
        return kept

    async def translate_term(self, term: str, *, example: str = "") -> str:
        """Один термин на голосовой модели (qwen2.5), а НЕ на R1.

        Публичный не ради красоты: разовый скрипт чистки банка
        (`scripts/repair_vocabulary.py`) чинит записи ТОЙ ЖЕ функцией, что
        продуктовый путь. Второй перевод «почти так же» разъехался бы с первым.

        D-8: R1 живёт только в офлайн-разборе, и он же — источник утечки
        китайского, которую мы чиним. Просить починку у того, кто сломал, —
        худший из возможных выборов.
        """
        user = f"{term}\n\nUsage: {example}" if example.strip() else term
        raw = await self._complete(
            [
                {"role": "system", "content": self._prompts.system("translate_term_system")},
                {"role": "user", "content": user},
            ],
            model=self._settings.ollama_model_interview,
            max_tokens=TERM_TRANSLATION_MAX_TOKENS,
            num_ctx=self._settings.ollama_num_ctx,
        )
        text = strip_thinking(raw).strip().strip('"').strip()
        # Модель иногда добавляет пояснение со второй строки — берём перевод.
        return text.splitlines()[0].strip() if text else ""

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
