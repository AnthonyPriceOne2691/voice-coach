---
type: Design
title: Оркестратор владеет структурой интервью, LLM — только формулировками
description: Ход интервью, выбор вопроса и решение о follow-up — детерминированная политика в коде; модель отвечает лишь за то, как это звучит.
status: accepted
tags: [orchestrator, llm, determinism]
implementation:
  - backend/app/orchestrator/interview.py
  - backend/app/orchestrator/review.py
  - backend/app/orchestrator/question_bank.py
  - data/prompts/
  - data/questions/
---

# Purpose

Соблазн отдать модели «саму вести интервью» велик и даёт быстрый прототип, но
делает поведение невоспроизводимым: одна и та же сессия каждый раз идёт иначе,
а тесты становятся невозможны. Инвариант I1-H6 фиксирует границу.

# Canonical rules

- **Структуру владеет код**: какой вопрос следующий, сколько их осталось, когда
  переходить к wrap-up — решает оркестратор, а не модель.
- **Follow-up — детерминированная политика** (doc 04), не «модель решила спросить ещё».
- **LLM отвечает только за формулировку** уже принятого решения.
- Промпты и банк вопросов живут в `data/`, не в коде: перечитываются на каждой
  сессии, рестарт не нужен (и гейт `inline-prompt` не даст вписать их в `.py`).

# Consequences

Поведение оркестратора тестируется без живой модели — LLM в тестах мокается,
и это возможно именно потому, что решения не в ней.

# Related

- [Sentence streaming](sentence-streaming.md) — что происходит с формулировкой дальше.

# Implementation map

| Area | Path |
|---|---|
| Оркестратор интервью | `backend/app/orchestrator/interview.py` |
| Оркестратор review | `backend/app/orchestrator/review.py` |
| Банк вопросов | `backend/app/orchestrator/question_bank.py` |
| Промпты / вопросы (данные) | `data/prompts/`, `data/questions/` |

# Sources

- `docs/04-interview-orchestrator.md`, `docs/11-two-modes-review-dialogue.md`, `docs/16-prompts-library.md`
