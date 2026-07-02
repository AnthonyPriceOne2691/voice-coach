"""Client audio (webm/opus) -> 16 kHz mono WAV via ffmpeg (doc 03 audio format)."""

import asyncio
from pathlib import Path


class AudioDecodeError(RuntimeError):
    """ffmpeg failed to decode client audio."""


class FfmpegDecoder:
    """Implements AudioDecoder via an ffmpeg subprocess reading stdin."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg") -> None:
        self._ffmpeg_bin = ffmpeg_bin

    async def to_wav(self, data: bytes, out_path: Path) -> None:
        process = await asyncio.create_subprocess_exec(
            self._ffmpeg_bin,
            "-y",
            "-i",
            "pipe:0",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(out_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate(input=data)
        if process.returncode != 0:
            raise AudioDecodeError(f"ffmpeg exited {process.returncode}: {stderr[-300:]!r}")
