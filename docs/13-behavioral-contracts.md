# 13 — Behavioral Contracts (ABC-lite)

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26  
> Inspired by: Agent Behavioral Contracts (ABC), arXiv:2602.22302 — formal P/I/G/R + runtime enforcement

## Зачем

Prompt и persona **недостаточны** для Mode 1: за 15+ минут LLM **drift’ит** — начинает коучить, хвалить, советовать, уходить с языка. Mock interview превращается в «репетитора с микрофоном».

**Решение:** behavioral contracts — **hard rules** (блок до TTS) + **soft rules** (recovery) + **orchestrator** держит структуру. Полный ABC/AgentAssert не тащим в MVP; делаем **ABC-lite** под local solo tool.

**Contracts ≠ model quality:** Mode 1 — **`qwen2.5:14b-instruct`**; Mode 2/summary — **`deepseek-r1:14b`**. См. [14-llm-model-split.md](14-llm-model-split.md).

```
Orchestrator (hard structure)  →  LLM (wording)  →  Contract Enforcer  →  TTS
        │                              │                    │
   что спросить                   как сформулировать    можно ли озвучить?
```

## Модель контракта (упрощённая ABC)

Как в paper: **C = (P, I, G, R)**

| Компонент | У нас | Пример |
|-----------|-------|--------|
| **P** Preconditions | Перед стартом mode | Mode 2: interview transcript exists |
| **I** Invariants | На каждом turn / session | EN only; no coaching in Mode 1 |
| **G** Governance | На каждое действие (реплику) | max 3 sentences; max 2 follow-ups |
| **R** Recovery | При soft/hard fail | regenerate → template fallback |

**Hard** — нарушение = reject, не озвучивать, recovery обязателен.  
**Soft** — допустимо кратко; recovery в ≤ k шагов (MVP: k=1 regenerate).

---

## Mode 1: Mock Interview

### Preconditions (P)

| ID | Rule | Check |
|----|------|-------|
| P1-1 | Session type = `interview` | orchestrator |
| P1-2 | Knowledge profile loaded | startup |
| P1-3 | Microphone / STT ready | client |

### Hard invariants (I_hard)

| ID | Rule | Enforcement |
|----|------|-------------|
| I1-H1 | **English only** — no Cyrillic, no RU phrases | regex / lang detect on output |
| I1-H2 | **No coaching** — no advice how to answer | pattern list (see below) |
| I1-H3 | **No scoring / debrief** — no rubric, grades, «your weakness» | pattern list |
| I1-H4 | **No praise as coach** — not *Great answer!*, *Well done!*, *Perfect!* | pattern list |
| I1-H5 | **Role = interviewer** — не переключаться в mentor/recruiter-friend | mode flag in prompt + reject mentor phrases |
| I1-H6 | **Structure from orchestrator** — LLM не выбирает следующий topic/question | orchestrator owns `question_id`, state |

### Hard governance (G_hard)

| ID | Rule | Enforcement |
|----|------|-------------|
| G1-H1 | **Max 3 sentences** per agent turn | sentence splitter + count |
| G1-H2 | **Max ~400 chars** per turn (TTS ~30 s) | length check |
| G1-H3 | **Max 2 follow-ups** per core question | orchestrator counter, not LLM |
| G1-H4 | **One question at a time** (except WRAP_UP) | in CORE/FOLLOW_UP: must contain `?` OR be short ack (≤12 words, no `?`) |

### Soft invariants (I_soft)

| ID | Rule | Recovery |
|----|------|----------|
| I1-S1 | Tone: professional warm, not chatty | regenerate with stricter prompt |
| I1-S2 | No filler monologue before question | truncate preamble → keep last sentence with `?` |
| I1-S3 | Acknowledgment before follow-up | if missing, prepend template *Got it.* |

### Soft governance (G_soft)

| ID | Rule | Recovery |
|----|------|----------|
| G1-S1 | Prefer follow-up patterns *Help me understand…* | optional style pass post-MVP |
| G1-S2 | Session time ≥ 80% → move to WRAP_UP | orchestrator timer, override LLM |

### Forbidden patterns (Mode 1 — coaching / debrief)

```text
great answer, well done, perfect answer, good job, you should,
try saying, here's a better, i'd recommend, let me coach,
your score, rating, out of 5, weakness, improve your,
vocabulary to learn, rephrase your, tip for you
```

```text
# Cyrillic — any match → hard fail
[\u0400-\u04FF]
```

### Allowed short acknowledgments (Mode 1)

Whitelist when no `?` in turn:

```text
got it, okay, ok, that makes sense, understood, right, i see,
thanks, thank you, clear, alright
```

(max 12 words total for ack-only turn)

---

## Mode 2: Review Together

### Preconditions (P)

| ID | Rule | Check |
|----|------|-------|
| P2-1 | `source_interview_id` exists with transcript | DB |
| P2-2 | Interview transcript non-empty | DB |

### Hard invariants (I_hard)

| ID | Rule | Enforcement |
|----|------|-------------|
| I2-H1 | **English only** (session language) | same as Mode 1 |
| I2-H2 | **Ground in transcript** — не выдумывать Q&A которых не было | LLM gets transcript; post-check: quoted Q index ∈ transcript |
| I2-H3 | **No new mock interview** — не задавать interview questions как Mode 1 | reject turns matching interview-only patterns without review framing |
| I2-H4 | **Role = recruiter friend / reviewer** — coaching **allowed** | mode flag |

### Hard governance (G_hard)

| ID | Rule | Enforcement |
|----|------|-------------|
| G2-H1 | **Max 5 sentences** per turn (review may be longer than interview) | count |
| G2-H2 | **Max ~700 chars** per turn | length |
| G2-H3 | Cover each core question before WRAP_UP | orchestrator tracks `questions_reviewed[]` |

### Soft invariants (I_soft)

| ID | Rule | Recovery |
|----|------|----------|
| I2-S1 | Start with strength before improvement | regenerate if only negative |
| I2-S2 | Tone: warm, collaborative (*let's*, *together*) | regenerate once |
| I2-S3 | Offer rephrase after critique | orchestrator nudge in prompt if missing |

### Soft governance (G_soft)

| ID | Rule | Recovery |
|----|------|----------|
| G2-S1 | User can interrupt / ask | allow barge-in P1 |
| G2-S2 | Don't monologue > 60 s | split turn, ask *Does that make sense?* |

---

## Summary generator & Vocabulary (non-voice LLM passes)

Отдельные контракты для JSON-only passes:

| Pass | Hard |
|------|------|
| Summary JSON | Valid JSON schema; EN body fields; scores 1–5 integers |
| Vocabulary extract | Each item has `term_en` + **`translation_ru` required**; no empty strings |

Voice contract enforcer **не применяется** — schema validator instead.

---

## Runtime pipeline (MVP — Contract Enforcer)

```
LLM generates candidate_text
        │
        ▼
┌───────────────────┐
│ 1. Hard checks    │  language, patterns, length, role, structure
└─────────┬─────────┘
          │ fail
          ▼
┌───────────────────┐     success
│ 2. Recovery R     │──────────────────────────────┐
│  retry ≤ 1 with   │                              │
│  violation hint   │                              ▼
└─────────┬─────────┘                    ┌───────────────────┐
          │ fail again                   │ 3. Soft checks    │
          ▼                              └─────────┬─────────┘
┌───────────────────┐                              │ fail
│ 4. Template       │                              ▼
│    fallback       │                    truncate / prepend ack
└─────────┬─────────┘                              │
          │                                        │
          └────────────────┬───────────────────────┘
                           ▼
                      TTS speak
                           │
                           ▼
                   log violation event (debug)
```

### Recovery strategies

| Violation | Recovery (order) |
|-----------|------------------|
| Cyrillic / RU | Regenerate: «English only. Rephrase.» → fallback EN template for current state |
| Coaching in Mode 1 | Regenerate: «Interviewer only. Ask question, no feedback.» → orchestrator canned question |
| Too long | Truncate to 3 sentences; if no question, append orchestrator seed question |
| No question in CORE/FOLLOW_UP | Append seed question from question bank |
| Mode 2 too harsh only | Regenerate: «Start with one strength, then improvement.» |

### Template fallbacks (Mode 1)

Orchestrator holds **canned lines** per state — if LLM fails 2×:

```text
INTRO:     "Let's begin. Walk me through an internal tool you built end-to-end."
FOLLOW_UP: "Help me understand the trade-off you considered there."
WRAP_UP:   "That's all from my side. Do you have any questions for us?"
```

---

## ContractSpec files (repo)

```
voice-interview-coach/
└── data/
    └── contracts/
        ├── interview.contract.yaml
        ├── review.contract.yaml
        └── summary.contract.yaml
```

### `interview.contract.yaml` (excerpt)

```yaml
mode: interview
version: "1.0"

preconditions:
  - session_type: interview
  - profile_loaded: true

invariants:
  hard:
    - id: en_only
      check: no_cyrillic
    - id: no_coaching
      check: forbid_patterns
      patterns_file: interview_forbidden.txt
    - id: interviewer_role
      check: mode_persona
      persona: senior_colleague

governance:
  hard:
    - id: max_sentences
      max: 3
    - id: max_chars
      max: 400
    - id: question_or_ack
      states: [CORE_QUEST, FOLLOW_UP]
      ack_max_words: 12

  soft:
    - id: warm_professional
      recovery: regenerate_once

recovery:
  max_retries: 1
  fallback: orchestrator_template
```

---

## Module layout (planned)

```
backend/app/
├── contracts/
│   ├── loader.py          # load YAML
│   ├── enforcer.py        # run checks on candidate text
│   ├── patterns.py        # forbidden/allowed lists
│   └── recovery.py        # regenerate, truncate, template
└── orchestrator/
    ├── interview.py       # owns hard structure (G1-H3, G1-H4)
    └── review.py
```

**Integration point:** `enforcer.validate(text, mode, state) → ValidatedText | RecoveryAction`

---

## Drift detection (Phase 2 — lightweight)

Session-level metric без full ABC drift score:

| Signal | Action |
|--------|--------|
| Hard violations ≥ 3 in one session | Log warning; tighten temperature 0.7→0.5 |
| Same soft violation ≥ 5 | Inject system reminder in next LLM call |
| Avg sentences creeping up | Enforce stricter truncate |

Post-MVP: rolling window on ack/question ratio, coaching pattern frequency.

---

## Requirements mapping

| Requirement | Contract |
|-------------|----------|
| FR-1.5 EN only mid-session | I1-H1, I2-H1 |
| FR-4.9 no coaching in interview | I1-H2–H4 |
| Mode 2 grounded review | I2-H2 |
| Persona separation | I1-H5, I2-H4 |
| FR-6.3 translation_ru | Vocabulary pass hard |

---

## MVP scope

| Item | Phase |
|------|-------|
| `interview.contract.yaml` + enforcer hard checks | 2 |
| Recovery: 1 retry + template fallback | 2 |
| Review contract (hard + soft) | 2 |
| Violation logging | 2 |
| `summary.contract.yaml` JSON schema validation | 2 |
| Full drift score / AgentAssert library | Post-MVP |
| ContractSpec parser generic DSL | Post-MVP (hardcode checks OK for MVP) |

---

## Out of scope (MVP)

- Full ABC `(p, δ, k)`-satisfaction proofs / metrics dashboard
- AgentAssert port or multi-agent composition theorem
- SMT / generation-time constraint (Agent-C style)

---

## Связанные документы

- [04-interview-orchestrator.md](04-interview-orchestrator.md) — structure G1-H3
- [09-agent-persona-and-tone.md](09-agent-persona-and-tone.md) — personas per mode
- [11-two-modes-review-dialogue.md](11-two-modes-review-dialogue.md) — modes
- [02-architecture.md](02-architecture.md) — Contract Enforcer component

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial ABC-lite spec |
| 2026-06-26 | Linked to two-model LLM split (doc 14) |
