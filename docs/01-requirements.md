# 01 — Requirements

> Voice Interview Coach · Design doc · v0.2 · 2026-07-02

## Функциональные требования

### FR-0 Service modes

> См. [11-two-modes-review-dialogue.md](11-two-modes-review-dialogue.md)

| ID | Требование | MVP | Priority |
|----|------------|-----|----------|
| FR-0.1 | **Mode 1 — Mock Interview** (голосовой) | ✅ | P0 |
| FR-0.2 | **Mode 2 — Review Together** (голосовой разбор с рекрутером-другом) | ✅ | P0 |
| FR-0.3 | Mode 2: пройти по ответам — **хорошо / можно лучше** + rephrases | ✅ | P0 |
| FR-0.4 | После Mode 1 → предложить Mode 2; можно позже из History | ✅ | P0 |
| FR-0.5 | **Хранить** полный transcript interview и review | ✅ | P0 |
| FR-0.6 | History UI: пары interview + review | ✅ | P0 |

### FR-1 Voice session

| ID | Требование | MVP | Priority |
|----|------------|-----|----------|
| FR-1.1 | Пользователь отвечает **голосом** (микрофон) | ✅ | P0 |
| FR-1.2 | Агент задаёт вопросы **голосом** (TTS) | ✅ | P0 |
| FR-1.3 | Сессия длится **15–45 min** (настраиваемый режим) | 15 min default | P0 |
| FR-1.4 | Полный **transcript** сохраняется локально | ✅ | P0 |
| FR-1.5 | Агент не переключается на RU mid-session | ✅ | P0 |

### FR-2 Interview behavior

| ID | Требование | MVP | Priority |
|----|------------|-----|----------|
| FR-2.1 | Структура: intro → questions → follow-ups → wrap-up | ✅ | P0 |
| FR-2.2 | Follow-up вопросы по ответам пользователя | ✅ | P0 |
| FR-2.3 | Mode 1 persona: **supportive senior colleague** (interviewer) | ✅ | P0 |
| FR-2.8 | Mode 2 persona: **experienced recruiter friend** (review together) | ✅ | P0 |
| FR-2.4 | Режим MVP: **Technical + project walkthrough** | ✅ | P0 |
| FR-2.5 | Доп. режимы: screening, system design, behavioral only | ❌ | P2 |
| FR-2.6 | Hard mode: перебивания, «simplify», «trade-off» | partial | P1 |
| FR-2.7 | Stress personas (skeptical CTO и др.) — **opt-in**, post-MVP | ❌ | P2 |

### FR-3 Personalization

| ID | Требование | MVP | Priority |
|----|------------|-----|----------|
| FR-3.1 | System prompt включает CV и case study | ✅ | P0 |
| FR-3.2 | Вопросы релевантны целевым ролям (AI Automation Engineer) | ✅ | P0 |
| FR-3.3 | Follow-up по проектам из профиля (LinkBuilder, inbound pipeline) | ✅ | P0 |
| FR-3.4 | Debrief: флаг inconsistency (SEO lead vs automation engineer) | ✅ | P1 |
| FR-3.5 | RAG по документам workspace | ❌ | P2 |

### FR-4 Post-session summary (после Mode 2)

> Structured scores/summary генерируется **после Review Together**.  
> См. [08-post-session-debrief.md](08-post-session-debrief.md)

| ID | Требование | MVP | Priority |
|----|------------|-----|----------|
| FR-4.1 | Mode 2 review dialogue — основной формат обратной связи | ✅ | P0 |
| FR-4.2 | Structured summary (scores, JSON) после Mode 2 | ✅ | P0 |
| FR-4.3 | **Strengths** — что было хорошо, с привязкой к моментам | ✅ | P0 |
| FR-4.4 | **Problems & improvements** — конкретные проблемы + evidence из transcript + fix | ✅ | P0 |
| FR-4.5 | **Weak answers** — top 2–3 с suggested rephrase на EN | ✅ | P0 |
| FR-4.6 | Vocabulary to learn (5–10 терминов) | ✅ | P0 |
| FR-4.7 | Next session focus — на что обратить внимание в следующий раз | ✅ | P0 |
| FR-4.8 | Consistency flags (SEO lead vs automation engineer и т.п.) | ✅ | P0 |
| FR-4.9 | Во время interview агент **не даёт coaching** — enforced FR-7 | ✅ | P0 |
| FR-4.10 | Debrief **English only** — UI, JSON, rephrases (кроме vocabulary → см. FR-6) | ✅ | P0 |
| FR-4.11 | Voice-only summary без Mode 2 | ❌ | — |
| FR-4.12 | «Try again» на 1–2 проваленных вопросах | ❌ | P2 |
| FR-4.13 | История сессий, тренд scores, повтор слабых тем | basic | P1 |
| FR-4.14 | Spaced repetition / flashcards export | ❌ | P3 |

### FR-6 Vocabulary Bank (вкладка «Полезные слова»)

> См. [10-vocabulary-bank.md](10-vocabulary-bank.md)

| ID | Требование | MVP | Priority |
|----|------------|-----|----------|
| FR-6.1 | Отдельная **вкладка** «Useful Words» / «Полезные слова» | ✅ | P0 |
| FR-6.2 | **Авто-пополнение** словаря после каждого интервью (ИИ) | ✅ | P0 |
| FR-6.3 | **`translation_ru` обязателен** на каждой записи | ✅ | P0 |
| FR-6.4 | Запись: `term_en` + `example_en` (spoken interview style) | ✅ | P0 |
| FR-6.5 | Dedup — не плодить дубликаты; merge / update | ✅ | P0 |
| FR-6.6 | Preview новых слов на экране debrief + link на вкладку | ✅ | P0 |
| FR-6.7 | Search, filter (category), sort на вкладке | ✅ | P0 |
| FR-6.8 | User: удалить запись, пометить learned | ❌ | P1 |
| FR-6.9 | Export CSV / Anki (EN + RU + example) | ❌ | P2 |

### FR-7 Behavioral contracts (ABC-lite)

> См. [13-behavioral-contracts.md](13-behavioral-contracts.md)

| ID | Требование | MVP | Priority |
|----|------------|-----|----------|
| FR-7.1 | **Contract Enforcer** проверяет текст агента **перед TTS** | ✅ | P0 |
| FR-7.2 | Mode 1 **hard**: EN only, no coaching, no praise/scoring, max 3 sentences | ✅ | P0 |
| FR-7.3 | Mode 1: orchestrator owns structure; LLM только wording | ✅ | P0 |
| FR-7.4 | Recovery: 1 regenerate → template fallback | ✅ | P0 |
| FR-7.5 | Mode 2 hard: grounded in interview transcript | ✅ | P0 |
| FR-7.6 | Violation logging (debug / session metadata) | ✅ | P1 |
| FR-7.7 | `*.contract.yaml` in `data/contracts/` | ✅ | P1 |

### FR-5 UX (черновик)

```
[Interview]  [History]  [Useful Words]  [Settings]

Mode 1: Start Mock Interview → voice ~15 min → save
        → «Review together?» → Mode 2

Mode 2: Review Together → voice dialog with recruiter friend
        → save review transcript → structured summary + vocabulary

History: list interview + review pairs, transcripts, re-run review
```

## Нефункциональные требования

### NFR-1 Performance & latency

| ID | Требование | Target |
|----|------------|--------|
| NFR-1.1 | End-to-end voice turn (user stops → agent starts speaking), **включая silence threshold VAD** | **< 4 s** acceptable, **< 2.5 s** ideal |
| NFR-1.2 | STT после end-of-utterance | < 1.5 s |
| NFR-1.3 | LLM first token | < 1 s (streaming) |
| NFR-1.4 | TTS start after first sentence ready | < 0.5 s |

> Latency критичен: выше 4–5 s ощущение «не live interview» ломается.

**Статус после Phase 0:** full turn warm ~3.0 s на коротком промпте; с VAD tail 1.2 s и sentence-streaming TTS perceived ≈ 3.1 s ✅, **без** streaming ≈ 4.2 s ❌ → sentence-streaming обязателен (см. [03-voice-pipeline.md](03-voice-pipeline.md)). Gate на продовом промпте 4–5K токенов — Phase 1 ([20-context-token-budget.md](20-context-token-budget.md)).

### NFR-2 Privacy & storage

| ID | Требование |
|----|------------|
| NFR-2.1 | Все записи и транскрипты **только локально** |
| NFR-2.2 | Нет отправки аудио в cloud в MVP |
| NFR-2.3 | Явный контроль: удаление сессии, экспорт transcript |
| NFR-2.4 | Модели скачиваются один раз; inference offline |

### NFR-3 Platform

| ID | Требование |
|----|------------|
| NFR-3.1 | macOS Apple Silicon (M5), 32 GB RAM |
| NFR-3.2 | Диск: модели STT + LLM + TTS укладываются в **512 GB** с запасом под сессии |
| NFR-3.3 | Работа без VPN / без зарубежных API в MVP |

### NFR-4 Reliability

| ID | Требование |
|----|------------|
| NFR-4.1 | Graceful degradation при OOM: меньшая модель или текстовый fallback |
| NFR-4.2 | Сессия не теряется при сбое — checkpoint transcript каждые N turns |

### NFR-5 Usability

| ID | Требование |
|----|------------|
| NFR-5.1 | Одна кнопка Start для MVP |
| NFR-5.2 | Визуальный индикатор: listening / thinking / speaking |
| NFR-5.3 | Возможность прервать агента (barge-in) — post-MVP или P1 |

### NFR-6 Code quality & tests

> Детали: [18-engineering-standards.md](18-engineering-standards.md)

| ID | Требование | Target |
|----|------------|--------|
| NFR-6.1 | Размер модуля: один исходный файл | **≤ 500 LOC** |
| NFR-6.2 | SOLID: слои, DI, интерфейсы STT/TTS/LLM | обязательно |
| NFR-6.3 | DRY: без дублирования бизнес-логики | обязательно |
| NFR-6.4 | Unit + integration tests; LLM/STT/TTS — через mocks | обязательно |
| NFR-6.5 | Backend coverage `app/` | ≥ 85% к концу Phase 2 |
| NFR-6.6 | Contract enforcer + orchestrators | ≥ 90–95% coverage |
| NFR-6.7 | Lint + typecheck (ruff, mypy/pyright, eslint) | CI / pre-merge |

## Out of scope (MVP)

- Мобильное приложение
- Multi-user / auth
- Видео / avatar
- Интеграция с календарём или LinkedIn
- Cloud sync
- Real-time code editor / whiteboard для system design

## Open questions

Первоначальные OQ-1…OQ-4 **закрыты**:

| # | Вопрос | Решение |
|---|--------|---------|
| OQ-1 | Web UI vs native/desktop | ✅ React + FastAPI ([07-tech-stack.md](07-tech-stack.md)) |
| OQ-2 | Streaming STT vs batch | ✅ VAD + batch в MVP; streaming — Phase 3 backlog |
| OQ-3 | Одна модель или две | ✅ Split ([14-llm-model-split.md](14-llm-model-split.md)) |
| OQ-4 | Barge-in в MVP | ✅ P1; в MVP mic не пишется в состоянии `speaking` ([03-voice-pipeline.md](03-voice-pipeline.md)) |

Актуальный открытый вопрос:

| # | Вопрос | Статус |
|---|--------|--------|
| **D-8** | Модель для Mode 2 voice review (R1 ~18–21 s/ход vs Qwen) | 🔲 OPEN — закрыть в Phase 1 re-benchmark, до Phase 2 ([14-llm-model-split.md](14-llm-model-split.md)) |

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial requirements from brief + local constraints |
| 2026-06-26 | Debrief expanded: mandatory post-session feedback with problems/improvements |
| 2026-06-26 | Debrief language fixed: English only |
| 2026-06-26 | Persona: supportive senior colleague (soft, guiding) |
| 2026-06-26 | FR-6: Vocabulary Bank tab, auto-fill, mandatory RU translation |
| 2026-06-26 | FR-0: two modes; FR-4: review dialogue + structured summary |
| 2026-06-26 | FR-7: ABC-lite behavioral contracts |
| 2026-06-26 | NFR-6: SOLID, DRY, 500 LOC, test coverage gates |
| 2026-07-02 | v0.2: NFR-1.1 уточнён (включает VAD tail) + статус Phase 0; OQ-1…4 закрыты; D-8 добавлен |
