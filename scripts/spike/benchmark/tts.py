"""Стадия TTS: Piper (CLI или python) с откатом на `say`."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import repo_path

_PIPER_VOICE: Any = None


def find_piper_paths() -> tuple[Path, Path] | None:
    """Return (piper_binary, voice_model) if Piper is installed."""
    piper_dir = repo_path("data/models/piper")
    voice = piper_dir / "en_US-lessac-medium.onnx"
    if not voice.exists():
        return None

    candidates = [
        piper_dir / "piper" / "piper",  # official tarball layout
        piper_dir / "piper",  # flat install / symlink
    ]
    system_bin = shutil.which("piper")
    if system_bin:
        candidates.append(Path(system_bin))

    for piper_bin in candidates:
        if piper_bin.is_file() and os.access(piper_bin, os.X_OK):
            return piper_bin, voice
    return None


def synthesize_piper_cli(
    text: str, piper_bin: Path, voice: Path, out_wav: Path
) -> float:
    t0 = time.perf_counter()
    env = os.environ.copy()
    env["DYLD_LIBRARY_PATH"] = str(piper_bin.parent)
    subprocess.run(
        [
            str(piper_bin),
            "--model",
            str(voice),
            "--output_file",
            str(out_wav),
        ],
        input=text,
        text=True,
        capture_output=True,
        check=True,
        cwd=str(piper_bin.parent),
        env=env,
    )
    return (time.perf_counter() - t0) * 1000


def synthesize_piper_python(text: str, voice: Path, out_wav: Path) -> float:
    import wave  # noqa: PLC0415

    from piper import PiperVoice  # noqa: PLC0415

    t0 = time.perf_counter()
    piper_voice = PiperVoice.load(
        str(voice),
        config_path=str(voice.with_suffix(".onnx.json")),
    )
    with wave.open(str(out_wav), "wb") as wav_file:
        piper_voice.synthesize_wav(text, wav_file)
    return (time.perf_counter() - t0) * 1000


def synthesize_piper(text: str, piper_bin: Path, voice: Path, out_wav: Path) -> float:
    return synthesize_piper_cli(text, piper_bin, voice, out_wav)


def synthesize_say(text: str, out_wav: Path) -> float:
    """Emergency fallback — not for production quality benchmark."""
    t0 = time.perf_counter()
    aiff = out_wav.with_suffix(".aiff")
    subprocess.run(["say", "-v", "Samantha", "-o", str(aiff), text], check=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(aiff), str(out_wav)],
        check=True,
        capture_output=True,
    )
    aiff.unlink(missing_ok=True)
    return (time.perf_counter() - t0) * 1000


def synthesize(text: str, out_wav: Path) -> tuple[float, str]:
    voice = repo_path("data/models/piper/en_US-lessac-medium.onnx")
    if voice.exists():
        try:
            from piper import PiperVoice  # noqa: F401, PLC0415

            _ = PiperVoice
            ms = synthesize_piper_python(text, voice, out_wav)
            return ms, "piper-tts"
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN: piper-tts failed ({exc}), trying CLI")

    piper_paths = find_piper_paths()
    if piper_paths:
        piper_bin, voice = piper_paths
        try:
            ms = synthesize_piper_cli(text, piper_bin, voice, out_wav)
            return ms, "piper-cli"
        except (subprocess.CalledProcessError, PermissionError, OSError) as exc:
            print(f"  WARN: Piper CLI failed ({exc}), falling back to say")

    ms = synthesize_say(text, out_wav)
    return ms, "say-fallback"
