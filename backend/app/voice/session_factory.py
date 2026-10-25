"""Сборка голосовых сессий: пул вопросов, оркестратор, поток.

Вынесено из `ws_voice`, когда тот перевалил за 500 строк (гейт §18). Граница
проведена по смыслу, а не по числу строк: здесь — что нужно, чтобы сессия
СУЩЕСТВОВАЛА, а в обработчике остаётся то, что происходит с ней дальше.
"""

import random
import uuid

from app.container import Container
from app.contracts.enforcer import ContractEnforcer
from app.orchestrator.interview import InterviewOrchestrator
from app.orchestrator.question_bank import pick_session_pool
from app.orchestrator.review import QASegment, ReviewOrchestrator, render_segments
from app.orchestrator.talk import TalkOrchestrator
from app.voice.interview_flow import InterviewFlow
from app.voice.review_flow import ReviewFlow
from app.voice.talk_checks import TalkChecks
from app.voice.talk_flow import TalkFlow
from app.voice.turn_runner import LlmParams

QUESTIONS_PER_SESSION = 6

#: Сессия перестала быть чисто технической: с 2026-08-13 она чередует технические
#: и behavioral вопросы (doc 04), и имя в записи обязано это называть — иначе
#: транскрипт врёт о том, чем была сессия.
INTERVIEW_MODE = "technical_and_behavioral"


def build_interview_flow(container: Container, *, duration_min: int) -> InterviewFlow:
    pool = pick_session_pool(
        container.question_bank,
        container.behavioral_bank,
        count=QUESTIONS_PER_SESSION,
        # Подавление стоит на строке, а не в ignore конфига: выбор вопросов
        # интервью — не крипто, и это видно на месте. Токены/соли брать
        # `secrets`, и тогда правило обязано краснеть.
        rng=random.Random(),  # noqa: S311 -- выбор вопросов, не крипто
    )
    orchestrator = InterviewOrchestrator(
        pool,
        duration_min=duration_min,
        wrap_up_seed=container.prompts.template("interview_wrap_up"),
    )
    return InterviewFlow(
        str(uuid.uuid4()),
        orchestrator,
        container.prompts.interviewer_system(),
        container.interviews,
        interview_mode=INTERVIEW_MODE,
    )


def build_review_flow(
    container: Container, *, interview_id: str, segments: list[QASegment]
) -> ReviewFlow:
    return ReviewFlow(
        str(uuid.uuid4()),
        interview_id,
        ReviewOrchestrator(segments),
        container.prompts.review_system(render_segments(segments)),
        container.reviews,
    )


def build_talk_flow(container: Container) -> TalkFlow:
    talk = TalkOrchestrator(container.talk_script, rng=random.Random())  # noqa: S311 -- тема, не крипто
    return TalkFlow(str(uuid.uuid4()), talk, container.prompts.talk_system(), container.talks)


def build_talk_checks(container: Container) -> TalkChecks:
    """Проверка речи (D3a.2): та же модель, что голос (D-8), детерминированная выборка."""
    s = container.settings
    return TalkChecks(
        container.llm,
        container.prompts,
        container.talk_enforcer,
        model=s.ollama_model_interview,
        temperature=s.talk_check_temperature,
        max_tokens=s.talk_check_max_tokens,
    )


def mode_params(container: Container, kind: str) -> tuple[LlmParams, ContractEnforcer]:
    """Параметры модели и контракт режима. D-8: весь голос — одна модель (qwen2.5)."""
    s = container.settings
    temperature, max_tokens, enforcer = {
        "interview": (
            s.interview_temperature,
            s.interview_max_tokens,
            container.interview_enforcer,
        ),
        "review": (s.review_temperature, s.review_max_tokens, container.review_enforcer),
        "talk": (s.talk_temperature, s.talk_max_tokens, container.talk_enforcer),
    }[kind]
    return LlmParams(s.ollama_model_interview, temperature, max_tokens), enforcer
