# 08 — Post-Session Summary (structured)

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## Роль этого блока

**Основная обратная связь** — **Mode 2: Review Together** (голосовой диалог с рекрутером-другом).  
См. [11-two-modes-review-dialogue.md](11-two-modes-review-dialogue.md).

Этот документ описывает **structured summary** — scores, JSON, UI card — генерируется **после** Mode 2 (на основе interview + review transcripts).

```
Mode 1 Interview  →  Mode 2 Review (voice)  →  Structured summary + Vocabulary Bank
     save                  save                         persist
```

## Принципы debrief

| Принцип | Описание |
|---------|----------|
| **Always on** | Mode 2 review рекомендуется после каждого interview; summary — после review |
| **Конкретика** | Не «speak more clearly», а цитата из transcript + что именно не так + как переформулировать |
| **Actionable** | Каждая проблема → что сделать в следующий раз |
| **Честность + kindness** | Слабые места — прямо, но tone **senior colleague**, не judge (см. [09-agent-persona-and-tone.md](09-agent-persona-and-tone.md)) |
| **Привязка к профилю** | Сверка с CV/case study и target role (AI Automation Engineer) |
| **Прогресс** | Сравнение с прошлыми сессиями, когда есть history (P1) |

## Что debrief должен покрывать

### 1. Общая оценка (rubric scores)

Пять измерений, шкала 1–5:

- **Clarity** — понятность ответов
- **Structure** — STAR / логика начало–середина–конец
- **Technical depth** — архитектура, trade-offs, детали
- **English fluency** — grammar, vocabulary, fillers, длинные паузы (по transcript)
- **Positioning** — consistent narrative (builder vs SEO lead)

### 2. Что было хорошо (`strengths`)

2–4 пункта с привязкой к конкретным моментам сессии:

> «Strong explanation of queue separation at Q4 — clear cause and effect.»

### 3. Проблемы и что улучшить (`improvements`)

Главный блок по запросу пользователя. Категории:

| Категория | Примеры проблем |
|-----------|-----------------|
| **Structure** | Ответ без conclusion; rambling > 2 min; нет метрик |
| **Technical** | Неточность в архитектуре; buzzwords без деталей; пропущен trade-off |
| **English** | Grammar errors; limited vocabulary; fillers (`um`, `like`, `you know`) |
| **Positioning** | «SEO lead» вместо automation engineer; фокус на links, не на systems |
| **Interview skill** | Не ответил на follow-up; ушёл в сторону; слишком короткий ответ |
| **Consistency** | Противоречие с CV или case study |

Формат каждого пункта:

```
Problem:    [что не так]
Evidence:   [цитата или timestamp из transcript]
Impact:     [почему interviewer это плохо воспримет]
Fix:        [как улучшить / suggested rephrase]
```

### 4. Разбор слабых ответов (`weak_answers`)

Top 2–3 вопроса, где ответ провалился или был слабым:

- оригинальный вопрос
- краткое summary ответа пользователя
- **suggested rephrase** — улучшенная версия на английском
- тип проблемы: `structure | depth | fluency | positioning`

### 5. Vocabulary to learn → Vocabulary Bank

5–12 терминов/фраз за сессию → **автоматически** в persistent [Vocabulary Bank](10-vocabulary-bank.md).

Каждая запись:
- **EN** term + example (interview register)
- **RU translation** — обязательно
- category, session source

На debrief — preview; полный список — вкладка «Useful Words».

### 6. Фокус на следующую сессию (`next_session_focus`)

2–3 темы для повторения — связь со spaced repetition (post-MVP).

## UX flow

```
Mode 2 Review ends
        │
        ▼
┌───────────────────┐
│  "Summarizing..." │  ← LLM: interview + review transcripts → JSON
└─────────┬─────────┘
          │
          ▼
┌───────────────────────────────────────────────────────────┐
│  SUMMARY SCREEN (+ review transcript available)            │
│  Scores · Strengths · Improvements · Vocabulary preview  │
│  [Interview transcript] [Review transcript] [Useful Words] │
└───────────────────────────────────────────────────────────┘
```

### Voice vs text

| Layer | Format |
|-------|--------|
| **Mode 2 Review** | Voice dialog (primary feedback) |
| **Structured summary** | Text UI card + JSON |
| **Transcripts** | Text — interview + review, stored always |

## Техническая реализация

### Pipeline

```
interview_transcript + review_transcript + session_metadata + knowledge profile
        │
        ▼
Summary Generator (LLM, temp 0.3)
        │
        ├── structured JSON (schema below)
        └── markdown summary for UI
        │
        ▼
Session Store (SQLite)
        │
        ▼
UI render (+ optional TTS summary P1)
```

### Отдельный LLM pass

Debrief **не смешивается** с interview dialog:

- во время сессии агент **не коучит** («Good answer!» — запрещено)
- весь coaching — только post-session
- можно использовать ту же модель или более крупную (14B) — качество debrief важнее latency

### Output schema

```json
{
  "overall_summary": "2-3 sentences: how the session went overall",
  "scores": {
    "clarity": 4,
    "structure": 3,
    "technical_depth": 4,
    "english_fluency": 3,
    "positioning": 2
  },
  "strengths": [
    {"text": "...", "reference": "Q3, ~04:15"}
  ],
  "improvements": [
    {
      "category": "positioning",
      "problem": "...",
      "evidence": "...",
      "impact": "...",
      "fix": "..."
    }
  ],
  "weak_answers": [
    {
      "question": "...",
      "user_answer_summary": "...",
      "suggested_rephrase": "...",
      "issue": "structure"
    }
  ],
  "vocabulary": [
    {
      "term_en": "throughput",
      "translation_ru": "пропускная способность; объём обработки за единицу времени",
      "example_en": "We improved queue throughput by separating inbound and API workers.",
      "category": "technical"
    }
  ],
  "consistency_flags": ["..."],
  "next_session_focus": ["HITL trade-offs", "2-min project pitch"],
  "voice_summary_script": "Optional P1: 3-4 sentences for TTS"
}
```

## Prompt guidelines (debrief system)

```
You are the senior colleague who ran the mock interview — now giving constructive feedback as a mentor.

Tone: warm, supportive, honest. You want to help them improve and land the role.
Start with what went well. Address problems gently but clearly — guide, don't judge.
Every improvement must include a concrete fix or suggested rephrase.
Speak as a peer mentor, not a hiring manager rejecting a candidate.
- Be specific: cite moments from the transcript
- Flag positioning mistakes (SEO vs automation engineer)
- Suggested rephrases: natural spoken English, not essay style
- Vocabulary items: each MUST include translation_ru (Russian, Cyrillic — never Chinese/Japanese/Korean characters) — required for Vocabulary Bank tab
- Output valid JSON matching the schema
- Language of debrief: English only — all fields, UI copy, voice summary script
```

## `translation_ru` — русский, и это проверяется (S-H6, 2026-08-15)

Поле исключено из `S-H2_en_body` («все текстовые поля по-английски») — и до
2026-08-15 его не проверяло **ничто**: исключение из одного правила молча стало
«может быть чем угодно». `deepseek-r1:14b` мультиязычен и на длинной генерации
срывается на китайский, поэтому в банке слов оказалось `выразительный陳述`.

Правило `S-H6_translation_is_russian`: перевод обязан содержать кириллицу и не
содержать иероглифов/каны/хангыля. Латиница законна — `автоматизация outreach`
и `очередь задач (Redis/RQ)` нормальны, запрет дал бы ложные срабатывания.

Запись с испорченным переводом **чинится** повторным переводом термина на
`qwen2.5` (не на R1: он и есть источник) и отбрасывается, только если починка не
удалась — с термином в логе, потому что молчаливая пропажа неотличима от
«модель не предложила слово».

## Язык debrief: English only ✅

**Решение зафиксировано:** весь debrief на английском — scores, проблемы, rephrases, vocabulary, voice summary (P1).

**Почему:**
- Тренировка **читать и усваивать** feedback так же, как на real hiring loop (feedback от HM/recruiter — EN)
- **Suggested rephrases** сразу в spoken EN register
- **Перевод (RU)** — только во вкладке Useful Words, для усвоения лексики; debrief body остаётся EN
- Единый язык сессии: interview EN → debrief EN → next session EN
- Меньше prompt/UI complexity; нет риска «поплыть» в RU mid-product

**Out of scope:** RU summary, bilingual debrief — не планируется, если явно не запросишь отдельно.

## Связь с прогрессом между сессиями

| Session N debrief | → | Session N+1 interview |
|-------------------|---|-------------------------|
| `next_session_focus` | → | orchestrator probes these topics |
| recurring `improvements` | → | debrief highlights «still appearing» |
| `scores` trend | → | UI progress chart (P2) |

## MVP checklist (debrief)

| # | Requirement | Phase |
|---|-------------|-------|
| 1 | Auto-trigger after every session | 2 |
| 2 | Rubric scores (5 dimensions) | 2 |
| 3 | Strengths + improvements with evidence | 2 |
| 4 | Weak answers + suggested rephrase (≥2) | 2 |
| 5 | Vocabulary list | 2 |
| 6 | Next session focus | 2 |
| 7 | Full transcript on same screen | 2 |
| 8 | Persist debrief in SQLite | 2 |
| 9 | Push vocabulary to Useful Words tab (with RU translation) | 2 |
| 10 | Voice summary of top issues | 3 (P1) |

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial doc; post-session feedback as mandatory core feature |
| 2026-06-26 | Debrief language: English only (decided) |
| 2026-06-26 | Debrief tone aligned with supportive senior colleague persona |
| 2026-06-26 | Vocabulary linked to persistent Bank + mandatory translation_ru |
| 2026-06-26 | Primary feedback = Mode 2 review; this doc = structured summary |
