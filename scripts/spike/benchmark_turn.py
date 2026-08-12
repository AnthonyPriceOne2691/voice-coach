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

Стадии живут в пакете `benchmark/` рядом: файл был на 573 строки при пороге
500 и держался снимком гейта пять поставок подряд.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

from benchmark.config import (
    DEFAULT_INTERVIEW_MODEL,
    RESULTS_PATH,
    DEFAULT_OLLAMA,
    DEFAULT_REVIEW_MODEL,
    SAMPLE_INTERVIEWER_PROMPT,
    SAMPLE_USER_TEXT,
    repo_path,
)
from benchmark.llm import check_ollama, ollama_chat_stream
from benchmark.metrics import TurnMetrics, append_result, summarize
from benchmark.stt import ensure_sample_wav, transcribe
from benchmark.tts import synthesize, synthesize_piper_python


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
    p.add_argument(
        "--ollama", default=os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA)
    )
    p.add_argument("--interview-model", default=DEFAULT_INTERVIEW_MODEL)
    p.add_argument("--review-model", default=DEFAULT_REVIEW_MODEL)
    p.add_argument("--prefer-whisper-cpp", action="store_true", default=True)
    p.add_argument(
        "--no-prefer-whisper-cpp", action="store_false", dest="prefer_whisper_cpp"
    )
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
