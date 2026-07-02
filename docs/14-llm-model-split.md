# 14 — LLM Model Split

> Voice Interview Coach · Design doc · v0.2 · 2026-07-02

## Decision

Две модели под две задачи — не one-size-fits-all.

```
Mode 1 Live Interview     ──▶  qwen2.5:14b-instruct   ✅ закрыто (Phase 0)
Mode 2 Review (voice)     ──▶  ⚠️ D-8 OPEN — см. ниже
Summary + Vocabulary JSON ──▶  deepseek-r1:14b        ✅ (latency некритична)
```

## Rationale

| Requirement | Best model type |
|-------------|-----------------|
| Low latency, short spoken turns | **Instruct** (Qwen) |
| Deep reasoning, critique, JSON | **Reasoning** (R1) |

DeepSeek R1 **не оптимальна для live interview** — thinking-chain добавляет секунды до первого слова.

Qwen2.5 14B Instruct **оптимальна для live** на 32 GB M5: follow-ups, EN dialog, instruction-following для behavioral contracts.

## D-8 (OPEN): модель для Mode 2 voice review

**Что показал Phase 0** ([19-phase0-benchmark-results.md](19-phase0-benchmark-results.md)):

1. R1 warm — **~18–21 s на каждый ход**, не только первый. В голосовом диалоге это означает: пользователь спросил «What about my queue answer?» → 20 секунд тишины. «Review tolerates longer pauses» — не проверенное допущение при такой величине паузы.
2. Оба прогона R1 вернули **пустой ответ** (`num_predict: 220` съеден thinking-цепочкой) → запланированный quality check «depth of critique» **не выполнен**. Правило num_predict для R1 — [20-context-token-budget.md](20-context-token-budget.md).

**Варианты:**

| # | Вариант | Плюсы | Минусы |
|---|---------|-------|--------|
| A | R1 для Mode 2 voice (как задумано) + UI «thinking…» + `num_predict: 2048` | Глубина разбора | ~20+ s пауза на каждый ход; качество ещё не подтверждено |
| B | **Qwen для Mode 2 voice**, R1 только для offline summary+vocabulary JSON | Живой диалог (~2 s/ход); ноль model swap до конца review | Разбор чуть менее глубокий; смягчается тем, что structured summary всё равно делает R1 |
| C | Гибрид: Qwen ведёт диалог, R1 асинхронно готовит «notes» перед стартом review | Скорость + глубина | Сложность (2 модели в RAM или предрасчёт) — против minimal moving parts |

**Рекомендация:** **B** — для conversational review инструкционной 14B достаточно, а вся глубина R1 сохраняется в summary pass, где latency не важна. Плюс исчезает model swap (~18 s) на входе в Mode 2.

**Как закрыть:** Phase 1 re-benchmark ([20-context-token-budget.md](20-context-token-budget.md)) — R1 c `num_predict: 2048` на реальном review-промпте: замерить паузу и оценить качество против Qwen на том же промпте. Решение зафиксировать здесь и в docs 07/16 до начала Phase 2 (Review orchestrator).

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
