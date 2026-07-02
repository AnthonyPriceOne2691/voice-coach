# 14 — LLM Model Split

> Voice Interview Coach · Design doc · v0.3 · 2026-07-03

## Decision ✅ (D-8 закрыт 2026-07-03)

Split по **латентности взаимодействия**, не по режиму: всё голосовое — instruct, всё офлайновое — reasoning.

```
Mode 1 Live Interview     ──▶  qwen2.5:14b-instruct   ✅ (Phase 0)
Mode 2 Review (voice)     ──▶  qwen2.5:14b-instruct   ✅ D-8 → вариант B (Phase 1 benchmark)
Summary JSON (offline)    ──▶  deepseek-r1:14b        ✅ (latency некритична)
Minimal summary (offline) ──▶  qwen2.5:14b-instruct   ✅ (без model swap при Skip)
```

**Бонус варианта B:** model swap при входе в Mode 2 исчезает полностью — R1 грузится один раз, в фоне, только для summary-pass.

## Rationale

| Requirement | Best model type |
|-------------|-----------------|
| Low latency, short spoken turns | **Instruct** (Qwen) |
| Deep reasoning, critique, JSON | **Reasoning** (R1) |

DeepSeek R1 **не оптимальна для live interview** — thinking-chain добавляет секунды до первого слова.

Qwen2.5 14B Instruct **оптимальна для live** на 32 GB M5: follow-ups, EN dialog, instruction-following для behavioral contracts.

## D-8 (CLOSED → вариант B): модель для Mode 2 voice review

**Phase 0 показал** ([19](19-phase0-benchmark-results.md)): R1 ~18–21 s/ход и пустой output при малом `num_predict`.

**Phase 1 re-benchmark (2026-07-03, реальный review-промпт ~1.8K токенов, raw: `scripts/spike/results_phase1.json`):**

| Модель | TTFT | Total/ход | Output |
|--------|------|-----------|--------|
| R1, `num_predict: 2048`, strip_thinking | **24.5–39.1 s** | **31.4–52.0 s** | непустой, качество разбора нормальное |
| Qwen, `num_predict: 300` | **0.19 s** warm | 12–16 s (полная генерация; первое предложение ~2 s) | внятный review: конкретика, rephrase, positioning-фиксы |

**Вердикт:** 30–50 секунд тишины на каждую реплику — голосовой диалог с R1 невозможен, никакой UI-индикатор это не спасает. Qwen отвечает через ~2 s и качества для conversational review достаточно (вся глубина R1 сохраняется в offline summary). **Принят вариант B.** Отражено в docs 07/16.

## Ollama commands

```bash
ollama pull qwen2.5:14b-instruct   # required
# deepseek-r1:14b                 # already local
```

## Config (`app/config.py` concept)

```python
OLLAMA_MODEL_INTERVIEW = "qwen2.5:14b-instruct"
OLLAMA_MODEL_REVIEW = "deepseek-r1:14b"
OLLAMA_MODEL_SUMMARY = "deepseek-r1:14b"
```

## Model swap

Before Mode 2: ensure interview model unloaded (Ollama auto-evicts on new model request, or explicit `keep_alive: 0`).

## Phase 0 benchmark — результат

1. **Qwen 14B instruct** — ✅ warm TTFT ~200 ms, total ~1.8 s → закрыто
2. **R1 14B** — ⚠️ latency замерена (~18–21 s/ход), quality check **не выполнен** (пустой output) → перенесён в Phase 1, см. D-8
3. Fallback-сравнение с 8B не понадобилось

## Fallback

| Condition | Action |
|-----------|--------|
| Qwen p95 > 4 s на реальном промпте (Phase 1) | Try `llama3.1:8b` for Mode 1 |
| R1 unavailable | Mode 2 + summary on Qwen (degraded reasoning) |
| Only one model allowed | Qwen solo > R1 solo for this product |

## Related

- [07-tech-stack.md](07-tech-stack.md)
- [03-voice-pipeline.md](03-voice-pipeline.md)
- [13-behavioral-contracts.md](13-behavioral-contracts.md)
- [20-context-token-budget.md](20-context-token-budget.md) — num_predict для R1, re-benchmark gate

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial: Qwen instruct + DeepSeek R1 split |
| 2026-07-02 | v0.2: D-8 open — Mode 2 voice model под вопросом (R1 ~18–21 s/ход, quality не проверен); fallback `llama3.3:8b` → `llama3.1:8b` (3.3 существует только в 70B) |
| 2026-07-03 | v0.3: **D-8 закрыт — вариант B** по Phase 1 benchmark (R1 31–52 s/ход vs Qwen TTFT 0.2 s); Qwen для всего голосового, R1 только offline summary |
