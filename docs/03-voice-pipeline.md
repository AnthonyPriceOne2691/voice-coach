# 03 — Voice Pipeline

> Voice Interview Coach · Design doc · **v0.3** · 2026-07-02  
> Benchmark: ✅ см. [19-phase0-benchmark-results.md](19-phase0-benchmark-results.md) (+ Limitations)  
> Token/context budget: [20-context-token-budget.md](20-context-token-budget.md)

## Цель

Описать локальный **voice loop** на MacBook Air M5 (32 GB): микрофон → STT → LLM → TTS → динамики, с приемлемой latency для mock interview.

## Voice turn timeline

```
User speaks ──▶ [VAD: end detected] ──▶ STT ──▶ LLM ──▶ TTS ──▶ Agent speaks
     │                                      │       │       │
     │◀────────── target < 4 s total ──────┴───────┴───────┘
```

| Этап | Target | Notes |
|------|--------|-------|
| VAD tail / silence detection | 300–800 ms | Trade-off: ранний cut vs длинные паузы в ответе |
| STT (Whisper) | 0.5–1.5 s | Зависит от длины utterance; `large-v3-turbo` или `small`/`medium` |
| LLM time-to-first-token | < 1 s | Streaming обязателен |
| TTS first chunk | < 0.5 s | Начинать озвучку по первому предложению, не ждать полный ответ |

### Perceived latency (что реально слышит пользователь)

Пользователь ждёт с момента, когда **замолчал**, — т.е. VAD threshold входит в паузу:

```
silence threshold (1.2 s) + STT (0.73) + LLM TTFT (0.2) + first sentence (~0.4) + TTS chunk (0.55)
≈ 3.1 s до первого звука агента (с sentence-streaming TTS)
```

Без sentence-streaming (ждать полный ответ, как мерил Phase 0): 1.2 + 3.05 ≈ **4.2 s** — на границе NFR-1.1. Выводы:
- **Sentence-streaming TTS — обязателен в Phase 1**, не оптимизация «потом»
- Silence threshold — настройка 0.8–2.0 s (см. doc 17 Settings); default 1.2 s, при жалобе на «тормозит» первым крутить его

## STT — Speech-to-Text

### Кандидаты (локально, Apple Silicon)

| Вариант | Pros | Cons | MVP fit |
|---------|------|------|---------|
| **whisper.cpp** (Metal) | Быстро на M-series, offline, зрелый | Batch-oriented | ✅ primary |
| **faster-whisper** | Хорошая скорость, Python-friendly | Отдельная установка | ✅ alternative |
| **mlx-whisper** | Нативно под MLX | Меньше примеров в проде | 🔲 benchmark |
| Browser Web Speech API | Zero setup | Cloud-dependent, quality | ❌ против privacy goal |

### Рекомендация MVP

**whisper.cpp** с моделью **`medium.en`** или **`small.en`**:
- `small.en` — быстрее, достаточно для interview English
- `medium.en` — точнее на акценте / tech terms, +latency

Для technical vocabulary (queues, HITL, pipeline) — post-MVP: **initial prompt / hotwords** или fine-tune не нужен на старте.

### STT mode для MVP

**Batch после end-of-utterance** (не streaming STT):
- Проще интеграция с orchestrator
- Меньше false partial transcripts
- Streaming STT — Phase 2 для снижения perceived latency

## VAD — Voice Activity Detection

| Вариант | Notes |
|---------|-------|
| **silero-vad** | Лёгкий, Python, хорош для end-of-turn |
| **WebRTC VAD** | В браузере, можно детектить на клиенте |
| **Fixed silence threshold** | MVP fallback: 1.2 s silence → end turn |

**Рекомендация:** клиент шлёт «utterance complete» по silence; сервер дублирует VAD для надёжности.

## LLM — Dialog engine

### Правила ≠ intelligence

Contracts (doc 13) — **границы**. Качество follow-up, разбор и rephrases — от **модели**. 7B для этого продукта недостаточно.

### Two-model split (see [14-llm-model-split.md](14-llm-model-split.md))

| Mode | Model |
|------|-------|
| **Mode 1 Live Interview** | `qwen2.5:14b-instruct` |
| **Mode 2 Review + summary** | `deepseek-r1:14b` |

| Model | Live interview | Review / reasoning |
|-------|----------------|------------------|
| Qwen2.5 14B instruct | ✅ **Optimal** | ✅ OK |
| DeepSeek R1 14B | ❌ thinking latency | ✅ **Best** |
| llama3.1:8b | ✅ faster fallback | OK |

**Phase 0:** Qwen 14B instruct — ✅ warm full turn ~3.0 s (короткий промпт). Re-benchmark с продовым промптом 4–5K токенов — gate Phase 1 ([20-context-token-budget.md](20-context-token-budget.md)). If fail → `llama3.1:8b` for Mode 1.

⚠️ Mode 2 на R1: ~18–21 s **на каждый ход** — модель для голосового review под вопросом (**D-8**, [14-llm-model-split.md](14-llm-model-split.md)).

## TTS — Text-to-Speech

### Кандидаты (локально)

| Вариант | Voice quality | Latency | Notes |
|---------|---------------|---------|-------|
| **Piper** | Good, robotic-neutral | Low | Stable, many voices |
| **Kokoro** (82M) | More natural | Medium | Worth benchmarking on M5 |
| **MLX-Audio / similar** | TBD | TBD | Apple Silicon native |
| **macOS `say`** | Robotic | Instant | Emergency fallback only |

**Рекомендация MVP:** **Piper** с английским voice «interviewer-neutral» (US/UK — выбрать один, не смешивать mid-session).

### TTS streaming strategy

1. LLM streams tokens
2. Buffer до конца первого предложения (`. ` / `? `)
3. Отправить chunk в TTS → начать playback
4. Очередь следующих предложений

## Memory budget (32 GB)

Одновременно loaded (оценка):

| Component | RAM |
|-----------|-----|
| macOS + apps | ~5 GB |
| Whisper small.en | ~0.5 GB |
| **LLM 14B Q4** (one at a time) | **~9 GB** |
| TTS | ~0.5 GB |
| Backend + frontend | ~1 GB |
| **Headroom** | **~16 GB** ✅ |

Summary pass: тот же **R1 14B** (~9 GB), но с `num_ctx: 16384` → +2–3 GB KV cache — укладывается (см. [20-context-token-budget.md](20-context-token-budget.md)). Обе 14B одновременно **не грузить** (swap rule, doc 07).

## Disk budget (512 GB)

| Asset | Size ~ |
|-------|--------|
| Whisper models | 0.5–3 GB |
| LLM 14B ×2 (Qwen + R1) | ~18 GB on disk |
| TTS voices | < 0.5 GB |
| Sessions (1 year, 3×/week) | < 1 GB |
| **Total models** | **~20–22 GB** ✅ (с запасом в 512 GB) |

## Audio format

| Direction | Format |
|-----------|--------|
| Client → Server | PCM 16 kHz mono или Opus chunks |
| STT input | WAV 16 kHz mono (whisper native) |
| TTS output | WAV/MP3 stream to client |

## Failure modes

| Problem | Mitigation |
|---------|------------|
| STT hallucination on silence | Min utterance duration; reject empty/low-confidence |
| LLM too slow | Smaller model; shorter max_tokens; pre-warm on Start |
| **Long utterance (60–90 s)** → STT растёт кратно (0.73 s @ 12 s → оценочно 3–5 s) | Замер в Phase 1 (gate, doc 20); при провале — chunked STT по VAD-паузам внутри ответа (P2) |
| **Prefill 4–5K-токенного промпта** не замерен в Phase 0 | Стабильный prompt prefix → KV cache reuse; re-benchmark Phase 1 (doc 20) |
| **R1: пустой output после strip_thinking** | `num_predict` ≥ 2048; enforcer: пустой текст = hard fail → recovery |
| TTS blocks | Sentence-chunk streaming |
| User long pause mid-answer | Extend VAD threshold; optional «Take your time» from agent |
| User говорит, пока агент говорит (barge-in нет в MVP) | Client **не пишет микрофон** в состоянии `speaking` — вход отбрасывается; barge-in P1 (doc 15) |
| Accent / misheard terms | Show live transcript; debrief flags unclear segments |

## Benchmark results

> **Полный отчёт:** [19-phase0-benchmark-results.md](19-phase0-benchmark-results.md) · raw: `scripts/spike/results.jsonl`

### Summary (MacBook Air M5, 2026-06-26)

**Prod stack (зафиксировано):** whisper.cpp `small.en` · Qwen2.5 14B instruct · piper-tts lessac

| Metric | Warm p50 | Warm p95 | Gate |
|--------|----------|----------|------|
| STT | 734 ms | 738 ms | < 1500 ms ✅ |
| LLM total | 1767 ms | 1812 ms | — |
| TTS | 547 ms | 552 ms | ~500 ms ✅ |
| **Full turn** | **3052 ms** | **3095 ms** | < 5000 ms ✅ |

**Phase 0:** ✅ **PASS** (steady-state turns). Cold STT load ~11 s → pre-load на session Start.

| Decision | Result |
|----------|--------|
| D-1 STT | ✅ **small.en** + **whisper.cpp** Metal |
| D-3 TTS | ✅ **Piper lessac** via **piper-tts** |
| D-2 Qwen | ✅ warm TTFT ~200 ms |
| D-2b R1 | ✅ Mode 2 only; pre-load (~18 s cold) |

## Benchmark checklist (Phase 0)

- [x] LLM: Qwen + R1 latency
- [x] Full loop: warm p95 **~3.1 s**
- [x] TTS: Piper lessac via piper-tts
- [x] STT: whisper.cpp Metal (warm ~735 ms)
- [x] Results documented in doc 19

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial voice pipeline for local M5 |
| 2026-06-26 | LLM split: qwen2.5:14b-instruct + deepseek-r1:14b |
| 2026-06-26 | Partial LLM benchmark results (Qwen warm TTFT ~180ms) |
| 2026-06-26 | v0.2: Phase 0 complete — full results in doc 19 |
| 2026-07-02 | v0.3: perceived latency (VAD tail); убран 32B-остаток (summary = R1 14B @ 16K ctx); disk budget исправлен (~20–22 GB); failure modes: long utterance, prefill, R1 empty output, mic-during-speaking; fallback `llama3.1:8b` |
