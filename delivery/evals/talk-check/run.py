"""Eval проверки речи (D3a.2, C9) и замер её цены (C8) на ЖИВОЙ модели.

Запуск — только по «запускай» человека, после прогона модель выгружается и
`ollama ps` обязан быть пустым:

    cd backend && uv run python ../delivery/evals/talk-check/run.py [--latency]

Путь тот же, что в продукте: системный промпт разговора с профилем, вопрос Генри,
реплика Антона, ответ Генри (живой, сгенерирован этой же моделью — он и есть
префикс, который видит проверка), затем просьба из `data/prompts/language_check.txt`
со схемой ответа. Решает настоящий `orchestrator.tips` с контрактом разговора.

`--latency` (C8): первый звук хода разговора, длительность проверки и первый звук
СЛЕДУЮЩЕГО хода — тот должен остаться ≤ 3 s, если проверка не выбила префикс из
KV-кэша Ollama.
"""

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend"))

from app.config import Settings  # noqa: E402
from app.contracts.enforcer import ContractEnforcer  # noqa: E402
from app.contracts.spec import load_contract  # noqa: E402
from app.knowledge.prompts import PromptLibrary  # noqa: E402
from app.llm.ollama_client import OllamaClient  # noqa: E402
from app.orchestrator.tips import Rejection, contract_gate, decide, parse_candidate  # noqa: E402
from app.voice.language_check import ask_candidate, check_messages  # noqa: E402

THRESHOLDS = {"quiet": 0.90, "error": 0.80, "poor": 0.70, "mixed": 0.75, "garbled": 0.75}


async def _reply(llm: OllamaClient, s: Settings, messages: list[dict[str, str]]) -> str:
    chunks = [
        t
        async for t in llm.stream_chat(
            messages, model=s.ollama_model_interview, temperature=s.talk_temperature,
            max_tokens=s.talk_max_tokens,
        )
    ]
    return "".join(chunks).strip()


def _passed(kind: str, case: dict[str, Any], note: dict[str, Any] | None) -> bool:
    if kind in ("natural", "casual", "garbled"):
        return note is None
    if note is None:
        return False
    if kind == "poor":
        plain = str(case["plain"]).lower()
        return plain in str(note["said"]).lower() and plain not in str(note["better"]).lower()
    return any(fix in str(note["better"]).lower() for fix in case["better_has_any"])


async def evaluate(llm: OllamaClient, s: Settings, system: str, prompts: PromptLibrary) -> int:
    cases = yaml.safe_load((Path(__file__).parent / "cases.yaml").read_text(encoding="utf-8"))
    passes = contract_gate(ContractEnforcer(load_contract(s.contracts_dir / "talk.contract.yaml")))
    rows: list[tuple[str, str, bool, str]] = []
    timings: list[float] = []
    for kind, items in cases.items():
        for case in items:
            history = [
                {"role": "system", "content": system},
                {"role": "assistant", "content": case["ask"]},
                {"role": "user", "content": case["said"]},
            ]
            history.append({"role": "assistant", "content": await _reply(llm, s, history)})
            started = time.perf_counter()
            raw = await ask_candidate(
                llm, check_messages(history, prompts.language_check(case["said"])),
                model=s.ollama_model_interview, temperature=s.talk_check_temperature,
                max_tokens=s.talk_check_max_tokens,
            )
            timings.append((time.perf_counter() - started) * 1000)
            candidate = parse_candidate(raw)
            verdict = candidate if isinstance(candidate, Rejection) else decide(
                candidate, case["said"], seen=[], passes_contract=passes
            )
            note = None if isinstance(verdict, Rejection) else verdict
            shown = (f"{verdict.value}" if note is None
                     else f"[{note['kind']}] {note['said']!r} -> {note['better']!r} ({note['why']})")
            rows.append((case["id"], kind, _passed(kind, case, note), shown))
            print(f"{case['id']:3} {kind:8} {'PASS' if rows[-1][2] else 'FAIL'}  {shown}")
    return _summary(rows, timings)


def _summary(rows: list[tuple[str, str, bool, str]], timings: list[float]) -> int:
    groups = {"quiet": ("natural", "casual"), "error": ("error",), "poor": ("poor",),
              "mixed": ("mixed",), "garbled": ("garbled",)}
    failed = 0
    for name, kinds in groups.items():
        picked = [ok for _, kind, ok, _ in rows if kind in kinds]
        rate = sum(picked) / len(picked)
        verdict = "OK" if rate >= THRESHOLDS[name] else "BELOW"
        failed += verdict == "BELOW"
        print(f"{name:8} {sum(picked)}/{len(picked)} = {rate:.0%} (threshold {THRESHOLDS[name]:.0%}) {verdict}")
    print(f"check: median {statistics.median(timings):.0f} ms, worst {max(timings):.0f} ms")
    return 1 if failed else 0


async def latency(llm: OllamaClient, s: Settings, system: str, prompts: PromptLibrary) -> None:
    """C8: первый токен хода → проверка → первый токен следующего хода."""
    history = [{"role": "system", "content": system},
               {"role": "assistant", "content": "Hi Anton, it's Henry. How's your day going?"},
               {"role": "user", "content": "Yesterday I go to the office and meet my client."}]
    await _reply(llm, s, history[:2])  # прогрев префикса, как у приложения
    for turn in (1, 2, 3):
        started = time.perf_counter()
        stream = llm.stream_chat(history, model=s.ollama_model_interview,
                                 temperature=s.talk_temperature, max_tokens=s.talk_max_tokens)
        first = await anext(stream)
        ttft = (time.perf_counter() - started) * 1000
        reply = first + "".join([t async for t in stream])
        history.append({"role": "assistant", "content": reply.strip()})
        started = time.perf_counter()
        await ask_candidate(llm, check_messages(history, prompts.language_check(history[-2]["content"])),
                            model=s.ollama_model_interview, temperature=s.talk_check_temperature,
                            max_tokens=s.talk_check_max_tokens)
        check_ms = (time.perf_counter() - started) * 1000
        print(f"turn {turn}: model first token {ttft:.0f} ms · check {check_ms:.0f} ms")
        history.append({"role": "user", "content": "It went well, they liked the demo a lot."})


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latency", action="store_true")
    args = parser.parse_args()
    s = Settings()
    llm = OllamaClient(s.ollama_base_url, num_ctx=s.ollama_num_ctx)
    prompts = PromptLibrary(s.prompts_dir, s.knowledge_dir)
    system = prompts.talk_system()
    try:
        if args.latency:
            await latency(llm, s, system, prompts)
            return 0
        return await evaluate(llm, s, system, prompts)
    finally:
        await llm.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
