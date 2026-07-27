---
type: ADR
title: "D-8: qwen2.5:14b в голосовом цикле, deepseek-r1 только offline"
description: Reasoning-модель в voice-цикле даёт 31–52 s на ход и физически несовместима с latency-бюджетом; R1 остаётся только для offline-summary.
status: accepted
tags: [llm, latency, adr]
implementation:
  - backend/app/llm/ollama_client.py
  - backend/app/llm/strip_thinking.py
  - backend/app/summary/service.py
  - backend/app/config.py
---

# Purpose

Решение D-8 закрыто, но предложение «а давай в интервью тоже R1, он же умнее»
возвращается каждый раз, когда качество формулировок кажется низким. Concept
существует, чтобы спор не начинался с нуля.

# Decision

- **Весь голосовой цикл** (интервью, review-диалог) — `qwen2.5:14b-instruct`.
- **`deepseek-r1:14b` — только offline**: post-session summary, где задержка не видна
  пользователю.
- Вернуть R1 в voice-цикл = смена инварианта: нужна spec + human OK, а не правка конфига.

# Rationale

Замерено: R1 даёт **31–52 s на ход**. Бюджет тёплого хода — **~3.0 s** (p95 ~3.1 s).
Разрыв на порядок; никакой промпт-инжиниринг его не закрывает. R1 тратит время на
thinking-блок, который в диалоге целиком выбрасывается — платим за то, что не звучит.

# Canonical rules

- Модели задаются только через типизированный конфиг
  (`ollama_model_interview` / `ollama_model_review`), не строками по коду.
- Вывод R1 проходит через `strip_thinking` — thinking-блок не попадает ни в
  транскрипт, ни в summary.
- Токен-бюджеты для summary отдельные (`summary_num_ctx`, `summary_max_tokens`):
  два транскрипта не влезают в 8192 (doc 20).

# Related

- [Sentence streaming](sentence-streaming.md) — из того же latency-бюджета.

# Implementation map

| Area | Path |
|---|---|
| Клиент Ollama | `backend/app/llm/ollama_client.py` |
| Вырезание thinking | `backend/app/llm/strip_thinking.py` |
| Offline summary | `backend/app/summary/service.py` |
| Параметры моделей | `backend/app/config.py` |

# Sources

- `docs/14-llm-model-split.md`, `docs/16-prompts-library.md`, `docs/20-context-token-budget.md`
- Замеры: `docs/19-phase0-benchmark-results.md`
