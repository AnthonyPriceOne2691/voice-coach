"""Замер одного хода, запись в results.jsonl и сводная таблица."""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass

from .config import RESULTS_PATH


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


def append_result(metrics: TurnMetrics) -> None:
    with RESULTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(metrics), ensure_ascii=False) + "\n")


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
