# 20 — Context Window & Token Budget

> Voice Interview Coach · Design doc · v0.1 · 2026-07-02

## Зачем этот документ

Phase 0 benchmark замерял latency на промпте **~120 токенов**. Продовые промпты — **3–4K токенов** (system + condensed profile + transcript). Prefill на Apple Silicon растёт с длиной промпта, а `num_ctx: 8192` — жёсткий потолок, в который summary-pass **не помещается** без стратегии. Этот док фиксирует бюджеты, стратегию усечения и gate на пере-замер в Phase 1.

## Token budget per call

Оценки: 1 токен ≈ 0.75 англ. слова; 15-min интервью ≈ 2000–2500 токенов transcript; 15-min review ≈ 2000–3000 токенов.

### Mode 1 — Interview turn (`qwen2.5:14b-instruct`, num_ctx 8192)

| Блок | Токены ~ |
|------|----------|
| System prompt (interviewer) | 300 |
| Condensed profile (`profile_condensed.md`) | ≤ 1500 |
| Case study summary | ≤ 1000 |
| Orchestrator wrapper (state, question seed) | 100 |
| Transcript tail (последние **12 turns**) | ≤ 2500 |
| **Prompt total** | **≤ 5400** |
| Generation (`num_predict`) | 220 |
| **Headroom к 8192** | **~2500** ✅ |

**Truncation rule:** transcript tail — скользящее окно последних 12 turns; более ранние turns отбрасываются (orchestrator и так владеет структурой — терять их безопасно). Полный transcript живёт в SQLite, не в промпте.

### Mode 2 — Review turn (`deepseek-r1:14b`, num_ctx 8192)

| Блок | Токены ~ |
|------|----------|
| System prompt (review) | 350 |
| Condensed profile | ≤ 1500 |
| **Segmented interview Q&A** (сжатый, см. ниже) | ≤ 2000 |
| Review dialogue tail (последние 8 turns) | ≤ 1500 |
| **Prompt total** | **≤ 5350** |
| Generation `num_predict` (**включая thinking!**) | 2048 |
| **Headroom** | **~800** ⚠️ tight |

**Segmented Q&A:** не сырой transcript, а компрессия: per-question блок `Qn: <вопрос> / A: <ответ, усечён до ~150 токенов> / [flags]`. Готовится один раз при старте Mode 2, стабилен весь review → работает KV-prefix cache.

### Summary pass (`deepseek-r1:14b`, **num_ctx 16384**)

| Блок | Токены ~ |
|------|----------|
| System + JSON schema | 800 |
| Condensed profile | 1500 |
| Interview transcript (полный) | 2500 |
| Review transcript (полный) | 3000 |
| **Prompt total** | **~8000** |
| Generation (thinking + JSON ~2500) | 4096 |
| **Итого** | **~12K** → не влезает в 8192 ❌ |

**Решение:** summary-pass запускается с **`num_ctx: 16384`**. Это не live-turn — latency некритична; KV cache 14B Q4 на 16K ≈ +2–3 GB RAM, в 32 GB укладывается (см. [03-voice-pipeline.md](03-voice-pipeline.md) memory budget). Fallback: компрессия транскриптов до segmented Q&A.

## R1 thinking budget — жёсткое правило

**Урок Phase 0:** оба прогона R1 со стандартным `num_predict: 220` вернули **пустой ответ** — thinking-цепочка израсходовала весь лимит, после `strip_thinking()` не осталось ничего (см. [19-phase0-benchmark-results.md](19-phase0-benchmark-results.md) → Limitations).

| Правило | Значение |
|---------|----------|
| `num_predict` для R1 считает **thinking + ответ** | всегда ≫ видимого output |
| Mode 2 review turn | ≥ **2048** |
| Summary JSON | ≥ **4096** |
| Enforcer check | если после `strip_thinking()` текст пустой → treat as hard fail → recovery ([13-behavioral-contracts.md](13-behavioral-contracts.md)) |

## Prefill latency & KV-prefix cache

Ollama переиспользует KV cache по **стабильному префиксу** промпта. Правила сборки промпта:

1. **Стабильная часть первой:** system → profile → case (не меняются в сессии).
2. Переменная часть (state wrapper, transcript tail) — **в конце**.
3. Не пересобирать/не переформатировать стабильный префикс между turns (любое изменение байта = full prefill).

**Ожидание:** первый turn сессии платит полный prefill ~4–5K токенов (оценочно +1–3 s на M5 — **не замерено в Phase 0**); последующие turns — только инкремент. Это и есть главный незакрытый риск latency.

## Phase 1 re-benchmark gate (обязательный)

Phase 0 gate пройден на нерепрезентативном промпте. В Phase 1, как только собран реальный prompt assembly:

- [ ] Замерить full turn с промптом **4–5K токенов** (реальный system + profile + tail), 5+ warm runs
- [ ] Gate: p95 full turn **< 4 s** (warm, после первого turn сессии)
- [ ] Замерить first-turn-of-session отдельно (full prefill) — допустимо до ~6 s, маскируется intro-репликой агента
- [ ] Замерить R1 review turn c `num_predict: 2048` — зафиксировать реальную паузу для D-8 ([14-llm-model-split.md](14-llm-model-split.md))
- [ ] STT на utterance 60–90 s (реальная длина ответа) — см. риск в [03-voice-pipeline.md](03-voice-pipeline.md)

Если gate провален → mitigations по порядку: сократить profile до 1000 токенов → tail до 8 turns → `llama3.1:8b` для Mode 1.

## Связанные документы

- [03-voice-pipeline.md](03-voice-pipeline.md) — latency targets, memory budget
- [07-tech-stack.md](07-tech-stack.md) — model settings (канонические значения — в [16-prompts-library.md](16-prompts-library.md))
- [14-llm-model-split.md](14-llm-model-split.md) — D-8: Mode 2 model
- [19-phase0-benchmark-results.md](19-phase0-benchmark-results.md) — limitations

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-07-02 | Initial: token budgets, R1 thinking rule, num_ctx 16384 for summary, Phase 1 re-benchmark gate |
