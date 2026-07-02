"""whisper.cpp subprocess STT (doc 07: subprocess CLI, zero binding pain)."""

import asyncio
from pathlib import Path


class SttError(RuntimeError):
    """whisper.cpp failed to transcribe."""


class WhisperCppStt:
    """Implements SpeechToText over the whisper-cli binary (Metal build)."""

    def __init__(self, binary: Path, model: Path) -> None:
        self._binary = binary
        self._model = model

    async def transcribe(self, wav_path: Path) -> str:
        out_prefix = wav_path.with_suffix("")
        process = await asyncio.create_subprocess_exec(
            str(self._binary),
            "-m",
            str(self._model),
            "-f",
            str(wav_path),
            "-l",
            "en",
            "-otxt",
            "-of",
            str(out_prefix),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise SttError(f"whisper-cli exited {process.returncode}: {stderr[-300:]!r}")
        txt_path = Path(f"{out_prefix}.txt")
        try:
            text = txt_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise SttError("whisper-cli produced no transcript file") from exc
        txt_path.unlink(missing_ok=True)
        return " ".join(text.split())
