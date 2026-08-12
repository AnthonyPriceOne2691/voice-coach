"""Стадия STT: whisper.cpp или faster-whisper, плюс образец wav."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import SAMPLE_USER_TEXT, repo_path

_FASTER_WHISPER_MODEL: Any = None


def ensure_sample_wav(path: Path, *, duration_hint_s: float = 12.0) -> None:
    """Create a spoken English sample via macOS say + ffmpeg."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    aiff = path.with_suffix(".aiff")
    subprocess.run(
        ["say", "-v", "Samantha", "-o", str(aiff), SAMPLE_USER_TEXT],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(aiff),
            "-ar",
            "16000",
            "-ac",
            "1",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    aiff.unlink(missing_ok=True)


def find_whisper_cpp() -> Path | None:
    for name in ("whisper-cli", "whisper-cpp", "main"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def stt_whisper_cpp(wav: Path, model: Path, binary: Path) -> tuple[str, float]:
    t0 = time.perf_counter()
    out_prefix = wav.with_suffix("")
    subprocess.run(
        [
            str(binary),
            "-m",
            str(model),
            "-f",
            str(wav),
            "-l",
            "en",
            "-otxt",
            "-of",
            str(out_prefix),
        ],
        check=True,
        capture_output=True,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    txt_path = Path(f"{out_prefix}.txt")
    text = txt_path.read_text(encoding="utf-8").strip()
    txt_path.unlink(missing_ok=True)
    return text, elapsed_ms


def get_faster_whisper_model(model_size: str = "small.en") -> Any:
    global _FASTER_WHISPER_MODEL  # noqa: PLW0603
    if _FASTER_WHISPER_MODEL is None:
        from faster_whisper import WhisperModel  # noqa: PLC0415

        _FASTER_WHISPER_MODEL = WhisperModel(
            model_size, device="cpu", compute_type="int8"
        )
    return _FASTER_WHISPER_MODEL


def stt_faster_whisper(wav: Path, model_size: str = "small.en") -> tuple[str, float]:
    t0 = time.perf_counter()
    model = get_faster_whisper_model(model_size)
    segments, _ = model.transcribe(str(wav), language="en")
    text = " ".join(seg.text.strip() for seg in segments).strip()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return text, elapsed_ms


def transcribe(wav: Path, *, prefer_cpp: bool) -> tuple[str, float, str]:
    whisper_model = repo_path("data/models/whisper/ggml-small.en.bin")
    cpp_bin = find_whisper_cpp()
    if prefer_cpp and cpp_bin and whisper_model.exists():
        text, ms = stt_whisper_cpp(wav, whisper_model, cpp_bin)
        return text, ms, "whisper.cpp"
    text, ms = stt_faster_whisper(wav)
    return text, ms, "faster-whisper"
