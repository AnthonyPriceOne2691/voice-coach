"""Dependency container — orchestration code depends on interfaces, wiring lives here."""

from dataclasses import dataclass

from app.common.interfaces import AudioDecoder, LlmClient, SpeechToText, TextToSpeech
from app.config import Settings
from app.knowledge.prompts import PromptLibrary
from app.llm.ollama_client import OllamaClient
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
    ollama: OllamaClient | None = None  # concrete handle for health probe / shutdown


def build_container(settings: Settings) -> Container:
    ollama = OllamaClient(settings.ollama_base_url, num_ctx=settings.ollama_num_ctx)
    return Container(
        settings=settings,
        stt=WhisperCppStt(settings.whisper_cpp_bin, settings.whisper_model_path),
        tts=PiperTts(settings.piper_voice_path, length_scale=settings.piper_length_scale),
        llm=ollama,
        decoder=FfmpegDecoder(),
        prompts=PromptLibrary(settings.prompts_dir, settings.knowledge_dir),
        ollama=ollama,
    )
