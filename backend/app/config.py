"""Application settings — single config source (doc 18: no scattered env reads)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8000

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model_interview: str = "qwen2.5:14b-instruct"
    ollama_model_review: str = "deepseek-r1:14b"
    ollama_num_ctx: int = 8192
    interview_temperature: float = 0.75
    interview_max_tokens: int = 220
    review_temperature: float = 0.6
    review_max_tokens: int = 300
    summary_temperature: float = 0.3
    summary_max_tokens: int = 4096  # R1: thinking included (doc 20)
    summary_num_ctx: int = 16384  # two full transcripts don't fit 8192 (doc 20)
    minimal_summary_max_tokens: int = 800

    whisper_cpp_bin: Path = Path("/opt/homebrew/bin/whisper-cli")
    whisper_model_path: Path = REPO_ROOT / "data" / "models" / "whisper" / "ggml-small.en.bin"
    # Henry's voice: hfc_male-medium — самый естественный из быстрых (~0.12 s/предложение);
    # максимум качества: en_US-ryan-high (~0.81 s/предложение) через PIPER_VOICE_PATH в .env
    piper_voice_path: Path = REPO_ROOT / "data" / "models" / "piper" / "en_US-hfc_male-medium.onnx"
    piper_length_scale: float = 1.15  # темп речи: 1.0 = нативный, больше = медленнее
    # Просодия. У hfc_male в паспорте `noise_scale: 0.333` — ВДВОЕ ниже, чем у
    # остальных голосов репозитория, и это главная причина, по которой Генри
    # звучал ровно. Значения выбраны на слух по образцам спайка (2026-08-13);
    # они привязаны к этому голосу — меняя PIPER_VOICE_PATH, переслушай.
    piper_noise_scale: float = 0.667  # вариативность интонации
    piper_noise_w: float = 1.0  # вариативность длительностей = живость ритма
    sentence_pause_ms: int = 350  # дыхание МЕЖДУ предложениями (не после последнего)

    database_url: str = f"sqlite+aiosqlite:///{REPO_ROOT / 'data' / 'sessions' / 'app.db'}"

    prompts_dir: Path = REPO_ROOT / "data" / "prompts"
    knowledge_dir: Path = REPO_ROOT / "data" / "knowledge"
    sessions_dir: Path = REPO_ROOT / "data" / "sessions"
    contracts_dir: Path = REPO_ROOT / "data" / "contracts"
    questions_dir: Path = REPO_ROOT / "data" / "questions"

    min_transcript_words: int = 1  # после junk-фильтра; «Hello» — валидная реплика


@lru_cache
def get_settings() -> Settings:
    return Settings()
