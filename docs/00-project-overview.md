# 00 — Project Overview

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## One-liner

Голосовой AI-агент для mock technical interviews на английском: симуляция live interview (STT/TTS, follow-ups), персонализация под CV и case study (AI Automation Engineer / internal SaaS builder), debrief с rubric и прогрессом между сессиями.

## Контекст

**Кто:** Anton Aspidov — AI Automation Engineer / Fullstack Internal Tools Builder. Production internal SaaS (outreach CRM, LLM pipelines, HITL, behavioral contracts). Целевой рынок — remote/contract за рубежом.

**Проблема:** английский B2 достаточен для async и технической переписки, но слабое место — **live interview на английском**: system design, walkthrough проектов, behavioral questions, импровизация под follow-up.

**Решение:** сервис с **двумя голосовыми режимами** — оба сохраняются локально:

1. **Mode 1 — Mock Interview** — live dialog, follow-ups, давление как на созвоне
2. **Mode 2 — Review Together** — рекрутер-друг **вместе** разбирает интервью: где хорошо, где можно лучше

После разбора — structured summary (scores), Vocabulary Bank. Без Mode 2 ценность неполная.

## Целевые роли для тренировки

- AI Automation Engineer
- Internal Tools / Fullstack Builder
- LLM Application Engineer

Ключевые темы: архитектура LinkBuilder (обезличенно), inbound AI pipeline, Agent Behavioral Contracts, trade-offs HITL vs autosend, «tell me about a project where you had measurable impact».

## Принятые решения (на старте проектирования)

| Решение | Значение | Статус |
|---------|----------|--------|
| Развёртывание | Локально на Mac | ✅ зафиксировано |
| Железо | MacBook Air 13 M5, 32 GB RAM, 512 GB SSD | ✅ зафиксировано |
| Voice I/O | STT + TTS (пользователь и агент голосом) | ✅ зафиксировано |
| Язык сессии | English only | ✅ из brief |
| Privacy | Записи и транскрипты локально | ✅ из brief |
| Cloud fallback | Не в MVP; опционально позже | 🔲 TBD |
| Post-session debrief | **Mode 2** voice review + structured summary | ✅ зафиксировано |
| Debrief format MVP | **Review Together** (voice dialog) + text summary card | ✅ зафиксировано |
| Язык debrief | **English only** (как и сессия) | ✅ зафиксировано |
| Persona & tone | **Supportive senior colleague** — мягкий, помогает и направляет | ✅ зафиксировано |
| Vocabulary Bank | Вкладка «Полезные слова»; авто после сессии; **RU перевод обязателен** | ✅ зафиксировано |
| Два режима ИИ | Mode 1 Interview + Mode 2 Review Together | ✅ зафиксировано |
| Хранение | Interview + review transcripts локально | ✅ зафиксировано |
| Behavioral contracts | ABC-lite: hard rules Mode 1, runtime enforcer перед TTS | ✅ зафиксировано |
| Tech stack | FastAPI + React + Ollama + whisper.cpp + Piper (doc 07) | ✅ зафиксировано |
| LLM | **Qwen 14B instruct** (Mode 1) + **DeepSeek R1 14B** (summary/vocabulary JSON) | ✅ зафиксировано |
| LLM Mode 2 voice review | R1 vs Qwen — **D-8 open** (R1: ~18–21 s/ход) | 🔲 Phase 1 ([doc 14](14-llm-model-split.md)) |
| Phase 0 benchmark | Warm full turn **~3 s** (короткий промпт); Phase 0 ✅ closed с limitations | ✅ 2026-06-26 |

## Phase 0 — результаты тестирования

> Детали: [19-phase0-benchmark-results.md](19-phase0-benchmark-results.md)

На MacBook Air M5 локальный voice loop **работает с приемлемой скоростью**:

- **~3 s** от конца реплики пользователя до начала ответа агента (warm, короткий промпт)
- STT whisper.cpp ~0.7 s · Qwen ~1.8 s · Piper TTS ~0.5 s
- Первый запуск медленный (~11 s STT load) → в приложении pre-load при старте сессии

**Оговорки** (см. Limitations в doc 19): промпт бенчмарка ~120 токенов вместо продовых 4–5K; 2 warm runs; R1 для Mode 2 показал ~18–21 s/ход при пустом видимом ответе → открыт **D-8** и re-benchmark gate в Phase 1 ([20-context-token-budget.md](20-context-token-budget.md)).

**Следующий шаг:** Phase 1 — минимальный voice loop в коде + re-benchmark + закрытие D-8.

1. Заранее заданная **структура интервью**, тайминг, давление follow-up
2. **Персонализация** под реальный профиль и целевые компании
3. **Mode 2 Review Together** — голосовой разбор с рекрутером-другом; interview + review хранятся
4. **Rubric и прогресс** между сессиями
5. **Vocabulary Bank** — вкладка полезных слов с авто-пополнением и переводом
6. Режим **hard mode**: перебивания (post-MVP, opt-in)
7. Опционально (post-MVP): pitch modes, resume walkthrough

## Success criteria

- После **10 сессий**: уверенно прохожу **2-min project pitch** и **inbound pipeline explanation** без длинных пауз
- Debrief показывает **измеримый прогресс** (fluency, structure, fewer «SEO lead» slips)
- Инструмент используется **3× в неделю** по 20–30 min

## Связанные документы

- [01-requirements.md](01-requirements.md)
- [02-architecture.md](02-architecture.md)
- [06-mvp-phases.md](06-mvp-phases.md)
- [08-post-session-debrief.md](08-post-session-debrief.md)
- [09-agent-persona-and-tone.md](09-agent-persona-and-tone.md)
- [10-vocabulary-bank.md](10-vocabulary-bank.md)
- [11-two-modes-review-dialogue.md](11-two-modes-review-dialogue.md)
- [12-session-storage.md](12-session-storage.md)
- [13-behavioral-contracts.md](13-behavioral-contracts.md)
- [14-llm-model-split.md](14-llm-model-split.md)

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial overview; local M5 constraint added |
| 2026-06-26 | Post-session debrief as mandatory core feature |
| 2026-06-26 | Debrief language: English only |
| 2026-06-26 | Persona: supportive senior colleague, soft tone |
| 2026-06-26 | Vocabulary Bank tab: auto-fill + mandatory RU translation |
| 2026-06-26 | Two modes: Interview + Review Together; session storage |
| 2026-06-26 | LLM split: qwen2.5:14b-instruct + deepseek-r1:14b |
| 2026-06-26 | ABC-lite behavioral contracts (doc 13) |
| 2026-06-26 | Phase 0 benchmark complete; warm turn ~3 s (doc 19) |
| 2026-07-02 | Doc review: benchmark limitations зафиксированы; D-8 (Mode 2 model) открыт; doc 20 (token budget) добавлен |
