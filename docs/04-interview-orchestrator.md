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

**Кто решает:** решение «follow-up vs next_question» принимает **только оркестратор**, детерминированной политикой (ноль дополнительных LLM-вызовов, тестируется unit-тестами как чистая функция). LLM решает лишь, *о чём* спросить, — не *задавать ли вопрос*. Это следствие I1-H6 / FR-7.3.

**Политика (deterministic):**

| # | Правило |
|---|---------|
| 1 | **Первый follow-up — всегда** (если время позволяет, см. таймер): в тренажёре follow-up почти всегда ценен — это и есть практика давления |
| 2 | **Второй follow-up** — только если ответ **< 40 слов** ИЛИ лишён признака качества. Признак **зависит от класса вопроса** (2026-08-13), см. ниже |
| 3 | **Max 2 follow-ups** на core question → `next_question` |
| 4 | Осталось < 20% времени сессии → follow-ups отключаются, добираем core questions |

**Признак сильного ответа — по классу вопроса:**

| Класс | Сильный ответ | Почему так |
|---|---|---|
| `technical` | есть **цифра** | заявление без измерения стоит переспросить |
| `behavioral` | есть **эпизод** (что произошло) **и** **исход** (чем кончилось) | у behavioral-ответа цифр нет почти никогда, и правило «нет цифр» срабатывало бы ВСЕГДА — каждый soft-вопрос съедал бы максимум допросов независимо от качества. Это выглядело бы придиркой к хорошим ответам |

Оба признака — словари в `orchestrator/interview.py` рядом с политикой, не модель:
цена ошибки низкая в обе стороны (лишний допрос у доброго тренера — не беда,
пропущенный тоже), а воспроизводимость нужна тестам.

**Семантические триггеры** (не решают «задавать ли», а подсказывают LLM формулировку — уходят в prompt-инструкцию). Набор **свой на класс**:

*Technical:*
  - Упомянута технология без trade-off → «Why X over Y?»
  - Противоречие с CV → «You mentioned SEO — how does that relate to automation?»
  - Vague claim → «What was the measurable impact?»
  - Иначе generic → «Can you elaborate on…?» / «Help me understand…»

*Behavioral* (у рассказа о людях другие дыры — спрашивать про trade-off здесь мимо):
  - Описана ситуация, но не свои действия → «What did you personally do?»
  - Нет реакции другой стороны → «How did that land?»
  - История без финала → «How did it turn out?»
  - Иначе → «What would you do differently now?»

### WRAP_UP (~1 min)
- «That’s all from my side. Any questions for us?»
- Короткий ответ пользователя → closing

### DEBRIEF
- Orchestrator не генерирует voice
- Handoff to Debrief Generator — **обязательный** post-session pass (см. [08-post-session-debrief.md](08-post-session-debrief.md))
- Во время CORE_QUEST / FOLLOW_UP агент **не хвалит и не коучит** — enforced via [13-behavioral-contracts.md](13-behavioral-contracts.md).

## MVP mode: `technical_and_behavioral`

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

### Question bank: behavioral (2026-08-13)

Второй банк — `data/questions/behavioral.yaml`, класс задаётся ключом `kind:`
**файла**, а не строкой вопроса.

| # | Theme | Example seed question |
|---|-------|----------------------|
| 1 | Disagreement | Tell me about a time you disagreed with a stakeholder. How did it end? |
| 2 | Explaining to non-technical people | How do you explain a technical trade-off to someone non-technical? |
| 3 | Missed deadline | Describe a deadline you missed. What did you do about it? |
| 4 | Receiving feedback | Tell me about feedback that stung. What did you change afterwards? |
| 5 | Competing priorities | Two people needed you at once and both were urgent. |
| 6 | Async and remote work | Tell me about a time async communication went wrong. |
| 7 | Pushing back on scope | Tell me about a time you said no to a request. |
| 8 | Learning something unfamiliar | Describe something you had to learn from scratch under time pressure. |

### Чередование классов

Сессия из шести вопросов — **три технических и три behavioral, строго через
один**, начиная с технического открывающего (`first: true`):

```
T (project_overview) → S → T → S → T → S
```

Случаен только выбор вопросов **внутри** класса. Чередование детерминированное,
а не «случайно 3 из 6», потому что случайная выборка регулярно даёт три
behavioral подряд, и сессия перестаёт тренировать **переключение** между
режимами речи — ровно то, ради чего классы и смешаны.

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

## Мета-ходы: просьба о темпе речи

Не всякая реплика пользователя — ответ. Просьба «speak slower» / «too fast»
адресована **инструменту**, а не интервьюеру, и обрабатывается до оркестратора:

- распознавание — детерминированное (`backend/app/orchestrator/pace.py`): фраза
  из таблицы **и** реплика короче 12 слов. Второе условие обязательно: без него
  содержательный ответ со словами «we had to speed up the pipeline» стал бы
  мета-ходом и пропал бы из транскрипта;
- состояние машины **не двигается**: вопрос и follow-up не тратятся, `question_id`
  прежний. Иначе просьба о темпе стоила бы пользователю куска интервью;
- ответ — шаблонное подтверждение плюс **дословный повтор** последней реплики
  агента, уже новым темпом. **LLM не участвует**: решение структурное (I1-H6), а
  просьба замедлиться почти всегда означает «я не расслышал»;
- история для модели не пополняется — иначе в контексте появится дубль вопроса,
  за который платит бюджет токенов (doc 20);
- новое значение сохраняется в настройку `speech_length_scale` (doc 15) и
  переживает сессию; коридор `0.85 … 1.60`, шаг `0.15`. На границе произносится
  **другая** реплика — о том, что это предел: подтвердить изменение, которого не
  произошло, значит соврать голосом.

В транскрипте такой ход помечен `state: PACE_REQUEST`, `question_id: null`
(doc 12) и исключён из Mode 2 и суммаризации.

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
| 2026-07-02 | FOLLOW_UP: детерминированная политика оркестратора (1-й всегда, 2-й при <40 слов/нет метрик); семантические триггеры → prompt-подсказки для LLM |
