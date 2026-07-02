#!/usr/bin/env python3
"""
Phase 0 voice pipeline benchmark.

Measures STT → LLM → TTS latency on local Mac (Apple Silicon).

Usage:
    ollama serve   # separate terminal
    python scripts/spike/benchmark_turn.py --all
    python scripts/spike/benchmark_turn.py --stage llm
    python scripts/spike/benchmark_turn.py --stage full --runs 5

Results append to scripts/spike/results.jsonl and print summary table.
Fill docs/03-voice-pipeline.md benchmark table from output.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
SPIKE_DIR = Path(__file__).resolve().parent
RESULTS_PATH = SPIKE_DIR / "results.jsonl"

DEFAULT_OLLAMA = "http://127.0.0.1:11434"
DEFAULT_INTERVIEW_MODEL = "qwen2.5:14b-instruct"
DEFAULT_REVIEW_MODEL = "deepseek-r1:14b"

SAMPLE_USER_TEXT = (
    "I built an internal inbound reply pipeline for our link-building team. "
    "It uses separate queues for inbound messages and OpenAI API calls, "
    "with a human-in-the-loop step before anything gets sent automatically. "
    "We reduced the team from five people to one and cut the cycle time significantly."
)

SAMPLE_INTERVIEWER_PROMPT = """You are a supportive senior colleague running a mock technical interview.
The candidate just answered about their project. Ask ONE short follow-up question (max 2 sentences).
English only. No coaching or praise.

Candidate answer:
{transcript}

Your follow-up:"""


@dataclass
class TurnMetrics:
    run_id: int
    stage: str
    stt_ms: float | None = None
    llm_ttft_ms: float | None = None
    llm_total_ms: float | None = None
    tts_first_ms: float | None = None
    total_ms: float | None = None
    stt_backend: str | None = None
    tts_backend: str | None = None
    llm_model: str | None = None
    transcript: str | None = None
    llm_output: str | None = None
    notes: str | None = None


_FASTER_WHISPER_MODEL: Any = None
_PIPER_VOICE: Any = None


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


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

        _FASTER_WHISPER_MODEL = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _FASTER_WHISPER_MODEL


def stt_faster_whisper(wav: Path, model_size: str = "small.en") -> tuple[str, float]:
    t0 = time.perf_counter()
    model = get_faster_whisper_model(model_size)
    segments, _ = model.transcribe(str(wav), language="en")
    text = " ".join(seg.text.strip() for seg in segments).strip()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return text, elapsed_ms


def warmup_pipeline(wav: Path, *, prefer_cpp: bool, base_url: str, model: str) -> None:
    """Load STT/TTS/LLM weights before timed runs (cold start not measured)."""
    print("  Warmup: STT + LLM + TTS (untimed)...")
    transcribe(wav, prefer_cpp=prefer_cpp)
    ollama_chat_stream(
        base_url=base_url,
        model=model,
        prompt=SAMPLE_INTERVIEWER_PROMPT.format(transcript=SAMPLE_USER_TEXT),
        max_tokens=60,
    )
    voice = repo_path("data/models/piper/en_US-lessac-medium.onnx")
    if voice.exists():
        try:
            synthesize_piper_python("Warmup.", voice, wav.with_name("_warmup_tts.wav"))
        except Exception:  # noqa: BLE001
            pass


def transcribe(wav: Path, *, prefer_cpp: bool) -> tuple[str, float, str]:
    whisper_model = repo_path("data/models/whisper/ggml-small.en.bin")
    cpp_bin = find_whisper_cpp()
    if prefer_cpp and cpp_bin and whisper_model.exists():
        text, ms = stt_whisper_cpp(wav, whisper_model, cpp_bin)
        return text, ms, "whisper.cpp"
    text, ms = stt_faster_whisper(wav)
    return text, ms, "faster-whisper"


def strip_thinking(text: str) -> str:
    """Remove DeepSeek R1 reasoning blocks before TTS/display."""
    open_tag = "<" + "think" + ">"
    close_tag = "</" + "think" + ">"
    pattern = re.escape(open_tag) + r".*?" + re.escape(close_tag)
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def ollama_chat_stream(
    *,
    base_url: str,
    model: str,
    prompt: str,
    temperature: float = 0.75,
    max_tokens: int = 220,
) -> tuple[str, float, float]:
    """Returns (full_text, ttft_ms, total_ms)."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": 8192,
        },
    }
    t0 = time.perf_counter()
    ttft_ms: float | None = None
    chunks: list[str] = []

    with httpx.Client(timeout=120.0) as client:
        with client.stream("POST", f"{base_url}/api/generate", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("response", "")
                if token and ttft_ms is None:
                    ttft_ms = (time.perf_counter() - t0) * 1000
                if token:
                    chunks.append(token)
                if data.get("done"):
                    break

    total_ms = (time.perf_counter() - t0) * 1000
    text = strip_thinking("".join(chunks))
    return text, ttft_ms or total_ms, total_ms


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


def synthesize_piper_cli(text: str, piper_bin: Path, voice: Path, out_wav: Path) -> float:
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


def check_ollama(base_url: str) -> None:
    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"ERROR: Ollama not reachable at {base_url}. Run: ollama serve\n  {exc}")
        sys.exit(1)


def append_result(metrics: TurnMetrics) -> None:
    with RESULTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(metrics), ensure_ascii=False) + "\n")


def run_llm_benchmark(
    *,
    base_url: str,
    model: str,
    runs: int,
) -> list[TurnMetrics]:
    results: list[TurnMetrics] = []
    prompt = SAMPLE_INTERVIEWER_PROMPT.format(transcript=SAMPLE_USER_TEXT)
    for i in range(1, runs + 1):
        print(f"  LLM run {i}/{runs} ({model})...")
        text, ttft, total = ollama_chat_stream(
            base_url=base_url,
            model=model,
            prompt=prompt,
        )
        m = TurnMetrics(
            run_id=i,
            stage="llm",
            llm_ttft_ms=round(ttft, 1),
            llm_total_ms=round(total, 1),
            llm_model=model,
            llm_output=text[:200],
        )
        results.append(m)
        append_result(m)
        print(f"    ttft={ttft:.0f}ms total={total:.0f}ms")
    return results


def run_full_turn(
    *,
    base_url: str,
    model: str,
    run_id: int,
    prefer_cpp: bool,
    work_dir: Path,
) -> TurnMetrics:
    wav_in = work_dir / "sample_user.wav"
    wav_out = work_dir / "agent_reply.wav"
    ensure_sample_wav(wav_in)

    t_total = time.perf_counter()

    transcript, stt_ms, stt_backend = transcribe(wav_in, prefer_cpp=prefer_cpp)
    prompt = SAMPLE_INTERVIEWER_PROMPT.format(transcript=transcript or SAMPLE_USER_TEXT)
    llm_text, ttft, llm_total = ollama_chat_stream(
        base_url=base_url,
        model=model,
        prompt=prompt,
    )
    tts_ms, tts_backend = synthesize(llm_text, wav_out)

    total_ms = (time.perf_counter() - t_total) * 1000
    notes = None
    if tts_backend == "say-fallback":
        notes = "TTS used macOS say — run download_models.sh for Piper benchmark"

    m = TurnMetrics(
        run_id=run_id,
        stage="full",
        stt_ms=round(stt_ms, 1),
        llm_ttft_ms=round(ttft, 1),
        llm_total_ms=round(llm_total, 1),
        tts_first_ms=round(tts_ms, 1),
        total_ms=round(total_ms, 1),
        stt_backend=stt_backend,
        tts_backend=tts_backend,
        llm_model=model,
        transcript=transcript[:200],
        llm_output=llm_text[:200],
        notes=notes,
    )
    append_result(m)
    return m


def summarize(rows: list[TurnMetrics], *, label: str = "Summary") -> None:
    if not rows:
        return

    def col(values: list[float | None]) -> str:
        nums = [v for v in values if v is not None]
        if not nums:
            return "—"
        if len(nums) == 1:
            return f"{nums[0]:.0f}"
        return f"p50={statistics.median(nums):.0f} p95={percentile(nums, 95):.0f}"

    print(f"\n=== {label} ===")
    print(f"  stage:     {rows[0].stage}")
    print(f"  llm_model: {rows[0].llm_model}")
    print(f"  runs:      {len(rows)}")
    print(f"  stt_ms:    {col([r.stt_ms for r in rows])}")
    print(f"  llm_ttft:  {col([r.llm_ttft_ms for r in rows])}")
    print(f"  llm_total: {col([r.llm_total_ms for r in rows])}")
    print(f"  tts_ms:    {col([r.tts_first_ms for r in rows])}")
    print(f"  total_ms:  {col([r.total_ms for r in rows])}")

    totals = [r.total_ms for r in rows if r.total_ms is not None]
    if totals:
        p95 = percentile(totals, 95)
        verdict = "PASS" if p95 < 5000 else "FAIL"
        print(f"\n  Phase 0 gate (p95 total < 5000ms): {verdict} ({p95:.0f}ms)")
        if p95 < 3500:
            print("  Quality tier: GOOD (< 3.5s)")
        elif p95 < 5000:
            print("  Quality tier: ACCEPTABLE (< 5s)")
        else:
            print("  Action: consider llama3.3:8b for Mode 1 or whisper.cpp Metal STT")


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 0 voice pipeline benchmark")
    p.add_argument("--stage", choices=("llm", "full", "all"), default="all")
    p.add_argument(
        "--all",
        action="store_const",
        const="all",
        dest="stage",
        help="Shorthand for --stage all (LLM + full turn)",
    )
    p.add_argument("--runs", type=int, default=3, help="Number of full-turn runs")
    p.add_argument("--ollama", default=os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA))
    p.add_argument("--interview-model", default=DEFAULT_INTERVIEW_MODEL)
    p.add_argument("--review-model", default=DEFAULT_REVIEW_MODEL)
    p.add_argument("--prefer-whisper-cpp", action="store_true", default=True)
    p.add_argument("--no-prefer-whisper-cpp", action="store_false", dest="prefer_whisper_cpp")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    check_ollama(args.ollama)

    print("Voice Interview Coach — Phase 0 benchmark")
    print(f"  ollama: {args.ollama}")
    print(f"  results: {RESULTS_PATH}")
    print()

    all_rows: list[TurnMetrics] = []

    if args.stage in ("llm", "all"):
        print(">> Stage: LLM (interview model)")
        all_rows.extend(
            run_llm_benchmark(
                base_url=args.ollama,
                model=args.interview_model,
                runs=max(3, args.runs),
            )
        )
        summarize(all_rows)

        print("\n>> Stage: LLM (review model — R1)")
        review_rows = run_llm_benchmark(
            base_url=args.ollama,
            model=args.review_model,
            runs=2,
        )
        summarize(review_rows)

    if args.stage in ("full", "all"):
        print("\n>> Stage: FULL turn (STT → LLM → TTS)")
        whisper_model = repo_path("data/models/whisper/ggml-small.en.bin")
        if not whisper_model.exists():
            print("  NOTE: run scripts/download_models.sh for whisper.cpp model")
            print("  Using faster-whisper for STT in the meantime")

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            sample_wav = work / "sample_user.wav"
            ensure_sample_wav(sample_wav)
            warmup_pipeline(
                sample_wav,
                prefer_cpp=args.prefer_whisper_cpp,
                base_url=args.ollama,
                model=args.interview_model,
            )
            full_rows: list[TurnMetrics] = []
            for i in range(1, args.runs + 1):
                print(f"  Full turn {i}/{args.runs}...")
                m = run_full_turn(
                    base_url=args.ollama,
                    model=args.interview_model,
                    run_id=i,
                    prefer_cpp=args.prefer_whisper_cpp,
                    work_dir=work,
                )
                full_rows.append(m)
                print(
                    f"    stt={m.stt_ms:.0f}ms llm={m.llm_total_ms:.0f}ms "
                    f"tts={m.tts_first_ms:.0f}ms total={m.total_ms:.0f}ms"
                )
                if m.notes:
                    print(f"    NOTE: {m.notes}")
            summarize(full_rows)

    print(f"\nResults appended to {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
