# 19 — Phase 0 Benchmark Results

> Voice Interview Coach · Design doc · v0.2 · 2026-07-02  
> **Status: ✅ Phase 0 COMPLETE** — с оговорками, см. [Limitations](#limitations--что-benchmark-не-показывает)

## Environment

| Parameter | Value |
|-----------|-------|
| Machine | MacBook Air 13 **M5**, 32 GB RAM |
| OS | macOS (darwin 25.5) |
| Ollama | `qwen2.5:14b-instruct`, `deepseek-r1:14b` |
| Script | `scripts/spike/benchmark_turn.py` |
| Raw log | `scripts/spike/results.jsonl` |
| Date | 2026-06-26 |

## Verdict

| Gate | Target | Result | Status |
|------|--------|--------|--------|
| Full turn p95 (warm) | < 5000 ms | **~3100 ms** | ✅ PASS |
| Full turn p50 (warm) | < 4000 ms ideal | **~3050 ms** | ✅ GOOD |
| Qwen TTFT (warm) | < 1000 ms | **~200 ms** | ✅ PASS |
| TTS acceptable | 15 min listening | Piper lessac OK | ✅ PASS |

**Phase 0 закрыта.** Можно начинать Phase 1 (код приложения).

### Implementation notes (из benchmark)

1. **Pre-load models** на `Start Interview` — cold STT ~11 s, cold Qwen ~3 s (не считать в turn latency).
2. **R1 медленный на каждый ход, не только первый** — оба warm-прогона ~18–21 s (thinking model). Pre-load не решает проблему паузы в диалоге → открыто решение **D-8** ([14-llm-model-split.md](14-llm-model-split.md)).
3. **R1 с `num_predict: 220` возвращает пустой ответ** — thinking съедает весь token budget, после `strip_thinking()` текст пустой. В prod для R1 `num_predict` ≥ 2048 (см. [20-context-token-budget.md](20-context-token-budget.md)).
4. **TTS в prod:** `piper-tts` Python package (CLI tarball на macOS без dylibs). В spike `PiperVoice.load()` вызывался на каждый synth — prod держит voice загруженным, per-sentence latency будет ниже ~550 ms.
5. **STT в prod:** `whisper.cpp` Metal + `ggml-small.en.bin` (лучше, чем faster-whisper CPU).

---

## Final full turn (authoritative)

**Stack:** whisper.cpp `small.en` · Qwen2.5 14B instruct · piper-tts `en_US-lessac-medium`

3 прогона, пользовательский запуск (2026-06-26):

| Run | STT | LLM TTFT | LLM total | TTS | **Total** | Notes |
|-----|-----|----------|-----------|-----|-----------|-------|
| 1 | 11355 ms | 470 ms | 2152 ms | 526 ms | **14100 ms** | cold STT load |
| 2 | 731 ms | 202 ms | 1814 ms | 552 ms | **3099 ms** | warm ✅ |
| 3 | 738 ms | 203 ms | 1721 ms | 543 ms | **3004 ms** | warm ✅ |

**Warm runs only (2–3):**

| Metric | p50 | p95 |
|--------|-----|-----|
| STT | 734 ms | 738 ms |
| LLM total | 1767 ms | 1812 ms |
| TTS | 547 ms | 552 ms |
| **Total turn** | **3052 ms** | **3095 ms** |

STT transcript quality: технические термины распознаны корректно (queues, human-in-the-loop, OpenAI API).

---

## LLM-only benchmarks

### Mode 1 — `qwen2.5:14b-instruct`

| Run | TTFT | Total | Notes |
|-----|------|-------|-------|
| 1 | 3381 ms | 4985 ms | cold model load |
| 2 | 198 ms | 2073 ms | warm |
| 3 | 175 ms | 1858 ms | warm |

**Warm:** TTFT p50 **~190 ms**, total p50 **~1.9 s** → подходит для live interview.

### Mode 2 — `deepseek-r1:14b`

| Run | TTFT | Total | Notes |
|-----|------|-------|-------|
| 1 | 21474 ms | 21474 ms | thinking chain, **llm_output пустой** |
| 2 | 18037 ms | 18037 ms | thinking chain, **llm_output пустой** |

**Не для live turns.** Оба прогона — уже warm (модель была загружена ранними runs в этой же сессии), т.е. ~18–21 s — это **стоимость каждого review-хода**, а не только первого.

⚠️ **Качество review-ответов R1 не проверено:** из-за `num_predict: 220` (default скрипта) thinking израсходовал лимит и видимый ответ пуст. Запланированный doc 14 quality check «depth of critique» фактически **не выполнен**. Повторить в Phase 1 с `num_predict: 2048` — входит в re-benchmark gate ([20-context-token-budget.md](20-context-token-budget.md)).

---

## Earlier spike runs (reference)

### faster-whisper + piper-tts (без whisper.cpp)

| Run | STT | Total | TTS backend |
|-----|-----|-------|-------------|
| 1 | 3174 ms | 5629 ms | piper-tts |
| 2 | 2320 ms | 4813 ms | piper-tts |
| 3 | 2249 ms | 5132 ms | piper-tts |

STT медленнее whisper.cpp Metal (~2.3 s vs ~0.73 s warm). **Prod: whisper.cpp.**

### say-fallback TTS (до piper-tts fix)

Runs с `tts_backend: say-fallback` — не использовать для финальных решений; заменены на piper-tts.

---

## Limitations — что benchmark НЕ показывает

Gate < 5 s пройден честно, но замер имеет ограничения. Они не отменяют Phase 0, но обязательны к закрытию в Phase 1 (re-benchmark gate: [20-context-token-budget.md](20-context-token-budget.md)).

| # | Ограничение | Риск | Закрытие |
|---|-------------|------|----------|
| 1 | **n=2 warm runs** — p50/p95 по двум точкам статистически не значимы | Реальный p95 может быть выше | Phase 1: ≥ 5 warm runs |
| 2 | **Промпт ~120 токенов** вместо продовых 4–5K (system + profile + tail) | Prefill на длинном промпте добавит ~1–3 s на первый turn | Phase 1 re-benchmark с реальным prompt assembly; KV-prefix cache |
| 3 | **Синтетическое аудио** (`say -v Samantha`) — чистая дикторская речь | WER/latency на реальной речи с RU-акцентом не проверены | Phase 1: manual runs с реальным микрофоном (уже в exit criteria) |
| 4 | **Utterance 12 s**, реальные ответы — 60–90 s | STT время растёт с длиной аудио: warm 0.73 s @ 12 s → оценочно 3–5 s @ 90 s | Phase 1: замер на 60–90 s WAV; mitigation — chunked STT (P2) |
| 5 | **R1 output пустой** (num_predict 220) — latency замерена, качество нет | Mode 2 UX-решение принято вслепую | Phase 1: R1 с num_predict 2048 → решить D-8 |
| 6 | **Perceived latency не включает VAD tail** — пользователь ждёт silence threshold 1.2 s + turn 3.0 s ≈ **4.2 s** тишины | Выше NFR-1.1 «< 4 s acceptable» | Sentence-streaming TTS (audio start ~2 s после EOU) + возможное снижение threshold до 1.0 s — см. [03-voice-pipeline.md](03-voice-pipeline.md) |

---

## Decisions closed by benchmark

| ID | Decision | Result |
|----|----------|--------|
| D-1 | STT size | ✅ **small.en** |
| D-1b | STT runtime | ✅ **whisper.cpp** (Metal); spike: faster-whisper |
| D-2 | LLM Mode 1 | ✅ **qwen2.5:14b-instruct** (без downgrade на 8B) |
| D-2b | LLM Mode 2 | ⚠️ **deepseek-r1:14b** — под вопросом: ~18–21 s/ход, качество не проверено → **D-8 open** ([14-llm-model-split.md](14-llm-model-split.md)) |
| D-3 | TTS | ✅ **Piper lessac** via **piper-tts** |
| D-3b | Kokoro | ❌ не нужен — Piper OK |

---

## How to reproduce

```bash
ollama serve   # terminal 1

cd voice-interview-coach
bash scripts/download_models.sh
brew install whisper-cpp   # recommended for prod STT path

python3 -m venv /tmp/vic-spike-venv
source /tmp/vic-spike-venv/bin/activate
pip install -r scripts/spike/requirements.txt
python scripts/spike/benchmark_turn.py --stage full --runs 3
```

> Историческая заметка (актуально на момент замеров): репозиторий лежал в пути с `:`
> (`Other:Another`), из-за чего venv внутри репо не работал — отсюда `/tmp/vic-spike-venv`.
> С 2026-07-27 репо переехал, ограничение снято; spike-venv оставлен вне репо намеренно.

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Phase 0 complete; full results from MacBook Air M5 |
| 2026-07-02 | v0.2: Limitations section (n=2, short prompt, synthetic audio, R1 empty output, VAD tail); D-2b → D-8 open |
