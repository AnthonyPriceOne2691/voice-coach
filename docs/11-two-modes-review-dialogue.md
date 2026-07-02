# 11 — Two Modes & Review Dialogue

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## Суть (принятое уточнение)

В сервисе у ИИ **два режима** — оба голосовые (STT/TTS), оба **сохраняются** с полным transcript:

| # | Режим | Суть |
|---|-------|------|
| **1** | **Mock Interview** | Само интервью — симуляция live technical interview |
| **2** | **Review Together** | Опытный **рекрутер-друг** вместе с тобой разбирает прошедшее интервью: где ответ хороший, где можно было лучше |

```
┌──────────────────┐         ┌──────────────────────────────┐
│  Mode 1          │         │  Mode 2                       │
│  Mock Interview  │ ──────▶ │  Review Together              │
│                  │  link   │  (recruiter friend, voice)    │
│  senior colleague│         │  «Q3 was strong… at Q5 try…»  │
│  interviewer     │         │                               │
└────────┬─────────┘         └──────────────┬───────────────┘
         │                                   │
         └──────────────┬────────────────────┘
                        ▼
              Session Store (SQLite)
              interview + review transcripts
                        │
                        ▼
              Structured summary + Vocabulary Bank
              (background после Mode 2)
```

## Принятые решения

| Решение | Значение |
|---------|----------|
| Количество режимов | **2** — Interview + Review Together |
| Mode 2 delivery | **Голосовой диалог** (не только текст) |
| Persona Mode 1 | Supportive senior colleague / mock interviewer |
| Persona Mode 2 | **Experienced recruiter friend** — разбор «вместе», со стороны |
| Хранение | **Interview и review dialogues** — полные transcripts, локально |
| Связь сессий | Review → `source_interview_id` |
| Structured debrief | Генерируется **после** Mode 2 (scores, JSON) + Vocabulary Bank |
| Повторный разбор | Можно начать Mode 2 для **любого** прошлого interview из History |

---

## Mode 1: Mock Interview

> Детали: [04-interview-orchestrator.md](04-interview-orchestrator.md), persona: [09-agent-persona-and-tone.md](09-agent-persona-and-tone.md)

- Голосовой mock ~15 min
- Persona: senior colleague проводит interview
- **Во время сессии — zero coaching**
- По завершении → сохранение interview session → предложение Mode 2

---

## Mode 2: Review Together

### Концепция

Не лекция и не сухой отчёт — **разговор с другом-рекрутером**, который смотрел на интервью со стороны и идёт с тобой по ответам:

> *«Okay, let's go through this together. Question 2 — walk me through the tool you built. Your opening was clear, I liked that you mentioned the team size early. But when he asked about queues, you got a bit vague — want me to show how I'd tighten that?»*

### Persona: experienced recruiter friend

| Aspect | Behavior |
|--------|----------|
| Роль | Опытный tech recruiter, **друг**, на твоей стороне |
| Тон | Мягкий, supportive, «мы вместе» — *let's look at*, *together*, *you could try* |
| Структура | Идёт **по вопросам** из interview transcript по порядку (или по слабым местам) |
| Хвалит | Явно: *«That was a strong answer because…»* |
| Улучшает | Конкретно: *«Here you lost them — try leading with the metric»* |
| Интерактив | User может спросить: *«What about my HITL answer?»* |
| Язык | **English only** (как interview) |

Отличие от Mode 1 persona: Mode 1 **не оценивает**; Mode 2 **полностью про оценку и улучшение**, но в формате диалога, не monologue report.

### Review orchestrator (state machine)

```
IDLE → INTRO → WALK_QUESTIONS → (per question) HIGHLIGHT → IMPROVE → USER_Q?
                      ↑                              │
                      └──────── next question ───────┘
                      │
                      ▼
                 WRAP_UP → END → save review session
                                    → trigger structured debrief + vocabulary
```

| State | Agent behavior |
|-------|----------------|
| **INTRO** | «Let's review your mock together. I'll go question by question.» |
| **WALK_QUESTIONS** | Берёт Q+N из interview transcript |
| **HIGHLIGHT** | Что было хорошо (specific) |
| **IMPROVE** | Где слабо + как переформулировать (spoken example) |
| **USER_Q** | Ответ на уточнения пользователя по этому моменту |
| **WRAP_UP** | 2–3 главных takeaway + focus для следующего раза |

**Duration:** 10–20 min (гибко; можно закончить раньше)

### Context для LLM (Mode 2)

```json
{
  "mode": "review_together",
  "source_interview_id": "uuid",
  "interview_transcript": [...],
  "current_question_index": 2,
  "state": "IMPROVE",
  "candidate_profile": "...",
  "instruction": "Address queue answer — suggest tighter opening with metric"
}
```

---

## Хранение сессий

### Schema (SQLite)

> **Канон схемы — [12-session-storage.md](12-session-storage.md)** (там же формат turn c `state`/`question_id`, `summary_kind`, `status`). Здесь — сокращённая выжимка:

```sql
-- Mode 1
interview_sessions (
  id              TEXT PRIMARY KEY,
  started_at      TEXT,
  ended_at        TEXT,
  interview_mode  TEXT,  -- 'technical_project_walkthrough'
  persona         TEXT,  -- 'senior_colleague'
  transcript_json TEXT,  -- turns: см. doc 12
  metadata_json   TEXT,
  debrief_json    TEXT,  -- заполняется после summary
  summary_kind    TEXT,  -- NULL | 'minimal' | 'full'
  status          TEXT,  -- in_progress | completed | failed
  review_session_id TEXT NULL
);

-- Mode 2
review_sessions (
  id                    TEXT PRIMARY KEY,
  source_interview_id   TEXT NOT NULL REFERENCES interview_sessions(id),
  started_at            TEXT,
  ended_at              TEXT,
  persona               TEXT,  -- 'recruiter_friend'
  transcript_json       TEXT,
  metadata_json         TEXT
);
```

### Что хранится

| Artifact | Interview | Review |
|----------|-----------|--------|
| Full transcript | ✅ | ✅ |
| Timestamps per turn | ✅ | ✅ |
| Audio recording (optional P1) | 🔲 | 🔲 |
| Structured debrief JSON | ✅ (after review) | — |
| Vocabulary additions | ✅ (after review) | — |

**Retention:** бессрочно локально; user может удалить пару interview+review.

### History UI

```
┌─────────────────────────────────────────────────────────┐
│  History                                                 │
├─────────────────────────────────────────────────────────┤
│  📅 2026-06-26  Technical walkthrough  ·  14 min       │
│     Interview ✓   Review together ✓                      │
│     [Replay transcript] [Review again] [Delete]          │
├─────────────────────────────────────────────────────────┤
│  📅 2026-06-24  Technical walkthrough  ·  15 min       │
│     Interview ✓   Review — not started                   │
│     [Start review together]                              │
└─────────────────────────────────────────────────────────┘
```

---

## User flow (happy path)

```
1. Home → [Start Mock Interview]  (Mode 1)
2. Voice interview ~15 min
3. Interview saved
4. Screen: «Interview complete. Review together with your recruiter friend?»
   → [Start Review]  or  [Skip for now — review later from History]
5. Mode 2 voice dialogue ~10–15 min
6. Review saved, linked to interview
7. Background: structured debrief (scores, JSON) + Vocabulary Bank update
8. Screen: summary card + link to Useful Words + full transcripts
```

**Skip allowed?** Да — interview всё равно сохранён; review можно позже из History.  
**Value без review:** частичный — vocabulary и rubric генерируются **после review** (или fallback LLM-only from interview if user skips — TBD, recommend require review for full debrief).

**Рекомендация MVP:** если user skip review → minimal auto-summary from interview only; полный rubric + rich vocabulary после Mode 2.

---

## Связь с другими блоками

| Block | Relationship |
|-------|--------------|
| [08-post-session-debrief.md](08-post-session-debrief.md) | Structured scores/summary — **после** Mode 2; UI card + JSON |
| [10-vocabulary-bank.md](10-vocabulary-bank.md) | Populated from **interview + review** transcripts |
| [09-agent-persona-and-tone.md](09-agent-persona-and-tone.md) | Two personas per mode |

---

## MVP checklist

| # | Requirement | Phase |
|---|-------------|-------|
| 1 | Mode 1 Mock Interview (voice) | 2 |
| 2 | Mode 2 Review Together (voice) | 2 |
| 3 | Recruiter friend persona in Mode 2 | 2 |
| 4 | Save interview transcript | 2 |
| 5 | Save review transcript | 2 |
| 6 | Link review → interview | 2 |
| 7 | History UI with both sessions | 2 |
| 8 | Start review from History (past interviews) | 2 |
| 9 | Structured debrief + vocabulary after review | 2 |
| 10 | Optional audio recording | P1 |

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Two modes: Interview + Review Together; persistent storage |
| 2026-07-02 | Schema согласована с doc 12 (канон): `interview_mode`, `summary_kind`, `status` |
