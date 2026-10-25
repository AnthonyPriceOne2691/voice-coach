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
  - backend/app/summary/validate.py
  - backend/app/config.py
  - data/prompts/summary_system.txt
  - data/prompts/minimal_summary_system.txt
  - data/prompts/translate_term_system.txt
---

# Purpose

Решение D-8 закрыто, но предложение «а давай в интервью тоже R1, он же умнее»
возвращается каждый раз, когда качество формулировок кажется низким. Concept
существует, чтобы спор не начинался с нуля.

# Decision

- **Весь голосовой цикл** (интервью, review-диалог, разговор с 2026-10-17) — `qwen2.5:14b-instruct`.
  У разговора свои `talk_temperature` и `talk_max_tokens`, модель та же.
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
- **Проверка речи в разговоре (D3a.2) — на qwen, тем же клиентом и с тем же
  `num_ctx`.** Она идёт в голосовом цикле (после ответа Генри, пока он звучит), и
  R1 туда не годится по той же причине, что в сам голос. Ответ ограничен
  JSON-схемой (`json_schema` → Ollama `format`): схема меняет выборку, а не промпт,
  поэтому префикс разговора в KV-кэше остаётся общим. Другой `num_ctx` заставил бы
  Ollama перезагрузить модель. Параметры — `talk_check_temperature` 0.0 и
  `talk_check_max_tokens` 120 в `config.py`.
- **Починка вывода R1 идёт на qwen, а не на R1.** R1 мультиязычен и на длинной
  генерации срывается на китайский — так в банк слов попал `выразительный陳述`.
  Повторный перевод термина (`SummaryService.translate_term`) выполняется
  `ollama_model_interview`: просить починку у источника дефекта — худший из
  возможных выборов, а офлайн-путь может позволить себе второй вызов.
- **Форме вывода R1 не доверяют: поля-списки приводит валидатор.** На подсказку
  `next_session_focus [string]` R1 вернул одну строку вместо списка, и экран
  History → Open → Summary падал пустой страницей. `validate_summary` приводит
  каждое поле-список схемы (doc 08) к списку ДО записи в БД: строка на месте
  списка строк — список из неё, голая строка на месте объекта — объект с главным
  полем, мусор выбрасывается. Записи, сохранённые раньше, приводит `SummaryCard`
  (`frontend/src/lib/debrief.ts`). Сторож выводит поля-списки из самой подсказки
  модели (`SCHEMA_HINT`): новое поле без приведения — красный тест.
- **Офлайн-разбор видит профиль кандидата.** Обе сводки (R1 и qwen) получают
  `profile_condensed.md` в системном сообщении тем же плейсхолдером
  `{{profile_condensed}}`, что голосовые промпты; подставляет общий загрузчик
  `PromptLibrary.system()` (`backend/app/knowledge/prompts.py`), своего метода у сводки
  нет. До 2026-10-25 промпты объявляли профиль входом и ставили балл `positioning`, а
  профиль не доходил ни разу: балл ставился по роли, зашитой в текст промпта, и роль
  разошлась с профилем. Позиционирование сверяется с разделом `Positioning rules`
  профиля, а не с ролью в промпте. Профиль стоит ~1,270 токенов; бюджет обеих сводок —
  doc 20 (15-минутная сессия влезает с запасом, 30 и 45 минут — открытый вопрос).

# Related

- [Sentence streaming](sentence-streaming.md) — из того же latency-бюджета.

# Implementation map

| Area | Path |
|---|---|
| Клиент Ollama | `backend/app/llm/ollama_client.py` |
| Вырезание thinking | `backend/app/llm/strip_thinking.py` |
| Offline summary | `backend/app/summary/service.py` |
| Проверка вывода: перевод (S-H6), форма полей-списков (S-H1) | `backend/app/summary/validate.py` |
| Промпты офлайн-разбора | `data/prompts/summary_system.txt`, `minimal_summary_system.txt`, `translate_term_system.txt` |
| Параметры моделей | `backend/app/config.py` |

# Sources

- `docs/14-llm-model-split.md`, `docs/16-prompts-library.md`, `docs/20-context-token-budget.md`
- Замеры: `docs/19-phase0-benchmark-results.md`
