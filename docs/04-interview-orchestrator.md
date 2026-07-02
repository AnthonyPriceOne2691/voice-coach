# 04 — Interview Orchestrator

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## Назначение

Управление **структурой интервью**, а не свободным диалогом. State machine определяет фазу, допустимые переходы, тайминг и когда задавать follow-up vs переходить к следующему блоку.

## State machine (MVP)

```
                    ┌─────────┐
                    │  IDLE   │
                    └────┬────┘
                         │ start_session
                         ▼
                    ┌─────────┐
              ┌────▶│  INTRO  │──── greeting + set expectations
              │     └────┬────┘
              │          │
              │          ▼
              │     ┌─────────────┐
              │     │ CORE_QUEST  │◀──┐
              │     └──────┬──────┘   │
              │            │          │ next_question
              │     user_answer       │
              │            ▼          │
              │     ┌─────────────┐   │
              │     │  FOLLOW_UP  │───┘ (max 2 per question)
              │     └──────┬──────┘
              │            │ exhausted / timeout
              │            ▼
              │     ┌─────────────┐
              │     │  WRAP_UP    │──── "Any questions for me?"
              │     └──────┬──────┘
              │            │
              │            ▼
              │     ┌─────────────┐
              └─────│  DEBRIEF    │──── post-session (async LLM)
                    └─────────────┘
```

## States — behavior

### IDLE
- Ожидание Start
- Pre-warm: load STT/LLM/TTS models optional

### INTRO (~1–2 min)
- Agent представляет формат: «This is a mock technical interview, ~15 minutes, English only»
- Первый вопрос: often **«Tell me about yourself»** (short) или сразу project walkthrough — **TBD для MVP** (рекомендация: skip long TMAY, сразу project)

### CORE_QUEST (bulk of session)
- Вопрос из **question bank** для режима `technical_project_walkthrough`
- Таймер сессии: при 80% времени → переход к WRAP_UP
- Не более **5–7 core questions** за 15 min

### FOLLOW_UP
- Триггеры:
  - Ответ короткий (< N words) → «Can you elaborate on…?»
  - Упомянута технология без trade-off → «Why X over Y?»
  - Противоречие с CV → «You mentioned SEO — how does that relate to automation?»
  - Vague claim → «What was the measurable impact?»
- **Max 2 follow-ups** на один core question (иначе застревание)
- После 2 → `next_question`

### WRAP_UP (~1 min)
- «That’s all from my side. Any questions for us?»
- Короткий ответ пользователя → closing

### DEBRIEF
- Orchestrator не генерирует voice
- Handoff to Debrief Generator — **обязательный** post-session pass (см. [08-post-session-debrief.md](08-post-session-debrief.md))
- Во время CORE_QUEST / FOLLOW_UP агент **не хвалит и не коучит** — enforced via [13-behavioral-contracts.md](13-behavioral-contracts.md).

## MVP mode: `technical_project_walkthrough`

**Duration:** 15 min default  
**Persona:** supportive senior colleague (см. [09-agent-persona-and-tone.md](09-agent-persona-and-tone.md))  
**Focus:** AI Automation Engineer, internal SaaS, LLM pipelines

### Question bank (ordered pool, LLM adapts wording)

| # | Theme | Example seed question |
|---|-------|----------------------|
| 1 | Project overview | Walk me through an internal tool you built end-to-end. |
| 2 | Architecture | How is the system modularized? What are the main services? |
| 3 | LLM / AI pipeline | Describe your inbound reply handling and where the LLM sits. |
| 4 | HITL & safety | How do you decide what gets auto-sent vs human review? |
| 5 | Queues / async | Why separate queues for inbound and OpenAI calls? |
| 6 | Impact | What changed in team size or cycle time? How did you measure it? |
| 7 | Trade-offs | What would you rebuild if you started today? |
| 8 | Failure | Tell me about a production issue and how you debugged it. |

Orchestrator picks **5–6** из пула per session; порядок может варьироваться; повтор между сессиями — weighted random с penalty на недавно заданные.

## Persona: supportive senior colleague (MVP)

> Полная спецификация: [09-agent-persona-and-tone.md](09-agent-persona-and-tone.md)

**Role:** senior engineer / peer mentor, проводит mock ради твоей подготовки  
**Tone:** мягкий, спокойный, respectful — **не hostile, не cold HR**  
**Behaviors:**
- Follow-ups через curiosity: «Help me understand…», «What was the trade-off…»
- Short acknowledgments: «Got it», «That makes sense», «Okay, let's dig into that»
- Умеренное давление — enough to practice, not to intimidate
- **No coaching** during session (mentor mode → только debrief)

**System prompt snippet (concept):**

```
You are a senior software engineer — a supportive colleague running a mock technical interview.
Your goal is to help the candidate practice, not to intimidate them.
Tone: calm, professional, warm but not chatty. Soft and respectful.
Ask one question at a time. Keep your spoken lines under 3 sentences.
Use follow-ups to understand their thinking. Do not give coaching during the interview.
Do not switch to Russian. Use the candidate profile for relevant follow-ups.
```

## Post-MVP personas (opt-in stress test)

Default **не меняется**. Эти режимы — optional hard mode:

| Persona | Behavior |
|---------|----------|
| Friendly recruiter | More behavioral, less deep technical |
| Skeptical CTO | Pushback, «I didn't follow», demand metrics |
| Time-pressed HM | Interrupts long answers, «bottom line?» |

## Session timing

| Parameter | Value |
|-----------|-------|
| Default duration | 15 min |
| Warning at | 12 min (agent: «We have a few minutes left») |
| Hard stop at | 16 min → WRAP_UP |
| Max agent monologue | ~30 s TTS |

## Orchestrator ↔ LLM contract

Каждый turn orchestrator передаёт LLM:

```json
{
  "state": "FOLLOW_UP",
  "core_question_id": "llm_pipeline",
  "follow_up_count": 1,
  "time_remaining_min": 8,
  "last_user_answer": "...",
  "transcript_tail": [...],
  "instruction": "Ask one follow-up about HITL gates"
}
```

LLM возвращает **только текст реплики interviewer** (не JSON в MVP — проще для TTS).

## Hard mode (P1, partial in MVP)

Флаги в session config:

- `interrupt_long_answers`: если user > 90 s → agent перебивает
- `ask_simplify`: случайно 1× за сессию
- `challenge_tradeoff`: обязательно на architecture вопросах

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial orchestrator design |
| 2026-06-26 | Persona updated: supportive senior colleague |
