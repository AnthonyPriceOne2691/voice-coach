"""Dependency container — orchestration code depends on interfaces, wiring lives here."""

from dataclasses import dataclass

from app.common.interfaces import AudioDecoder, LlmClient, SpeechToText, TextToSpeech
from app.config import Settings
from app.contracts.enforcer import ContractEnforcer
from app.contracts.spec import load_contract
from app.knowledge.prompts import PromptLibrary
from app.llm.ollama_client import OllamaClient
from app.orchestrator.question_bank import Question, load_bank
from app.storage.db import Database
from app.storage.repositories.interviews import InterviewRepository
from app.storage.repositories.reviews import ReviewRepository
from app.storage.repositories.settings_repo import SettingsRepository
from app.storage.repositories.vocabulary import VocabularyRepository
from app.summary.service import SummaryService
from app.voice.audio import FfmpegDecoder
from app.voice.stt_whisper import WhisperCppStt
from app.voice.tts_piper import PiperTts


@dataclass
class Container:
    settings: Settings
    stt: SpeechToText
    tts: TextToSpeech
    llm: LlmClient
    decoder: AudioDecoder
    prompts: PromptLibrary
    db: Database
    interviews: InterviewRepository
    reviews: ReviewRepository
    vocabulary: VocabularyRepository
    user_settings: SettingsRepository
    interview_enforcer: ContractEnforcer
    review_enforcer: ContractEnforcer
    question_bank: list[Question]
    summaries: SummaryService
    ollama: OllamaClient | None = None  # concrete handle for health probe / shutdown


def build_container(settings: Settings) -> Container:
    ollama = OllamaClient(settings.ollama_base_url, num_ctx=settings.ollama_num_ctx)
    db = Database(settings.database_url)
    return Container(
        settings=settings,
        stt=WhisperCppStt(settings.whisper_cpp_bin, settings.whisper_model_path),
        tts=PiperTts(settings.piper_voice_path, length_scale=settings.piper_length_scale),
        llm=ollama,
        decoder=FfmpegDecoder(),
        prompts=PromptLibrary(settings.prompts_dir, settings.knowledge_dir),
        db=db,
        interviews=InterviewRepository(db),
        reviews=ReviewRepository(db),
        vocabulary=VocabularyRepository(db),
        user_settings=SettingsRepository(
            db, defaults={"speech_length_scale": settings.piper_length_scale}
        ),
        interview_enforcer=ContractEnforcer(
            load_contract(settings.contracts_dir / "interview.contract.yaml")
        ),
        review_enforcer=ContractEnforcer(
            load_contract(settings.contracts_dir / "review.contract.yaml")
        ),
        question_bank=load_bank(settings.questions_dir / "technical_project_walkthrough.yaml"),
        summaries=SummaryService(
            ollama,
            PromptLibrary(settings.prompts_dir, settings.knowledge_dir),
            InterviewRepository(db),
            ReviewRepository(db),
            VocabularyRepository(db),
            settings,
        ),
        ollama=ollama,
    )
