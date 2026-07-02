#!/usr/bin/env python3
"""Phase 1 re-benchmark gate (docs/20-context-token-budget.md).

Closes Phase 0 limitations:
  A) Qwen Mode 1 latency on a PRODUCTION-SIZE prompt (system + profile + transcript tail),
     5 warm runs -> p50/p95 TTFT, first-sentence time, total.
  B) D-8: Mode 2 review turn -- R1 (num_predict 2048, strip_thinking) vs Qwen on the
     same review prompt: latency + non-empty output check.

Usage: backend/.venv/bin/python scripts/spike/benchmark_phase1.py
"""

from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
OLLAMA = "http://127.0.0.1:11434"
QWEN = "qwen2.5:14b-instruct"
R1 = "deepseek-r1:14b"

FAKE_ANSWER = (
    "So the main reason we split the queues was isolation. The inbound mail webhook "
    "can spike hard, and OpenAI calls have unpredictable latency, so if they shared a "
    "queue a burst of inbound would starve the classification jobs. We also run "
    "monitoring checks with a headless browser pool which is heavy, so that got its "
    "own queue too. The trade-off is more infrastructure to watch, but each queue can "
    "scale and fail independently, and we reduced the team from five people to one."
)


def build_interview_prompt() -> list[dict[str, str]]:
    system_tpl = (REPO_ROOT / "data/prompts/interviewer_system.txt").read_text()
    profile = (REPO_ROOT / "data/knowledge/profile_condensed.md").read_text()
    system = system_tpl.replace("{{profile_condensed}}", profile)
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for i in range(6):  # 12-turn tail per doc 20
        messages.append({"role": "assistant", "content": f"Question {i + 1}: tell me more about the architecture and trade-offs."})
        messages.append({"role": "user", "content": FAKE_ANSWER})
    return messages


def build_review_prompt() -> list[dict[str, str]]:
    system_tpl = (REPO_ROOT / "data/prompts/review_system.txt").read_text()
    profile = (REPO_ROOT / "data/knowledge/profile_condensed.md").read_text()
    segments = "\n".join(
        f"Q{i + 1}: Walk me through the system.\nA{i + 1}: {FAKE_ANSWER[:400]}" for i in range(5)
    )
    system = system_tpl.replace("{{interview_qa_segments}}", segments).replace(
        "{{profile_condensed}}", profile
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "What about my queue answer on question 2? Was it strong enough?"},
    ]


def approx_tokens(messages: list[dict[str, str]]) -> int:
    return sum(len(m["content"]) for m in messages) // 4


def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?(</think>|\Z)", "", text, flags=re.DOTALL).strip()


def run_chat(
    model: str, messages: list[dict[str, str]], *, num_predict: int, temperature: float
) -> dict[str, float | str]:
    t0 = time.perf_counter()
    ttft: float | None = None
    first_sentence: float | None = None
    chunks: list[str] = []
    with httpx.Client(timeout=600.0) as client, client.stream(
        "POST",
        f"{OLLAMA}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": num_predict, "num_ctx": 8192},
        },
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            token = data.get("message", {}).get("content", "")
            if token:
                if ttft is None:
                    ttft = time.perf_counter() - t0
                chunks.append(token)
                if first_sentence is None and re.search(r"[.?!]\s", "".join(chunks)):
                    first_sentence = time.perf_counter() - t0
            if data.get("done"):
                break
    total = time.perf_counter() - t0
    text = strip_thinking("".join(chunks))
    return {
        "ttft_s": round(ttft or total, 2),
        "first_sentence_s": round(first_sentence or total, 2),
        "total_s": round(total, 2),
        "output_chars": len(text),
        "output_head": text[:160],
    }


def pctl(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def main() -> None:
    results: dict[str, object] = {}

    print("=== A) Mode 1 (Qwen) on production-size prompt ===")
    interview = build_interview_prompt()
    print(f"prompt ~{approx_tokens(interview)} tokens")
    run_chat(QWEN, interview, num_predict=220, temperature=0.75)  # warmup (model load + prefill)
    runs = [run_chat(QWEN, interview, num_predict=220, temperature=0.75) for _ in range(5)]
    for i, r in enumerate(runs):
        print(f"  run {i + 1}: ttft={r['ttft_s']}s first_sentence={r['first_sentence_s']}s total={r['total_s']}s")
    totals = [float(r["total_s"]) for r in runs]
    firsts = [float(r["first_sentence_s"]) for r in runs]
    stt, tts = 0.73, 0.55  # Phase 0 warm measurements
    projected_full = pctl(totals, 95) + stt + tts
    projected_perceived = statistics.median(firsts) + stt + tts
    print(f"  LLM total p50={statistics.median(totals):.2f}s p95={pctl(totals, 95):.2f}s")
    print(f"  Projected full turn p95 (STT+LLM+TTS): {projected_full:.2f}s  (gate < 4 s)")
    print(f"  Projected perceived (STT+first sentence+TTS): {projected_perceived:.2f}s")
    print(f"  GATE: {'PASS' if projected_full < 4.0 else 'FAIL'}")
    results["mode1_prod_prompt"] = {
        "prompt_tokens_approx": approx_tokens(interview),
        "runs": runs,
        "llm_total_p95_s": round(pctl(totals, 95), 2),
        "projected_full_turn_p95_s": round(projected_full, 2),
        "projected_perceived_s": round(projected_perceived, 2),
        "gate_lt_4s": projected_full < 4.0,
    }

    print("\n=== B) D-8: Mode 2 review turn -- R1 vs Qwen ===")
    review = build_review_prompt()
    print(f"prompt ~{approx_tokens(review)} tokens")

    print("  R1 (num_predict=2048, strip_thinking):")
    r1_runs = [run_chat(R1, review, num_predict=2048, temperature=0.6) for _ in range(3)]
    for i, r in enumerate(r1_runs):
        print(f"    run {i + 1}: ttft={r['ttft_s']}s total={r['total_s']}s output_chars={r['output_chars']}")
        print(f"      head: {r['output_head']!r}")

    print("  Qwen (num_predict=300):")
    qwen_runs = [run_chat(QWEN, review, num_predict=300, temperature=0.6) for _ in range(3)]
    for i, r in enumerate(qwen_runs):
        print(f"    run {i + 1}: ttft={r['ttft_s']}s total={r['total_s']}s output_chars={r['output_chars']}")
        print(f"      head: {r['output_head']!r}")

    results["d8_review"] = {"r1": r1_runs, "qwen": qwen_runs}
    out = REPO_ROOT / "scripts/spike/results_phase1.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
