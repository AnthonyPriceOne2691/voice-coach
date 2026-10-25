# 13 — Behavioral Contracts (ABC-lite)

> Voice Interview Coach · Design doc · v0.2 · 2026-07-02  
> Based on: Bhardwaj, «Agent Behavioral Contracts: Formal Specification and Runtime Enforcement for Reliable Autonomous AI Agents», arXiv:2602.22302 — контракт C = (P, I, G, R), hard/soft split, bounded recovery, runtime enforcement

## Что берём из full ABC, что нет

| Идея из paper | У нас | Почему |
|---------------|-------|--------|
| C = (P, I_hard, I_soft, G_hard, G_soft, R) | ✅ полностью | Ядро фреймворка, дешёвое в реализации |
| Hard = никогда; soft = допустимо с recovery ≤ k шагов | ✅ k = 1 (regenerate) | Lemma 3.10 paper: без recovery комплаенс падает экспоненциально (q^T), с recovery — линейно (≥ 1 − T(1−q)(1−r)). Наша сессия T ≈ 15–20 turns: даже q=0.95 без recovery даёт ~0.36 на сессию — recovery обязателен |
| Метрики считаются **до** recovery («transparency effect») | ✅ | Violation log фиксирует сырое поведение модели; иначе не видно, что промпт деградирует |
| Drift score D(t) = compliance-gap + JSD | ⚠️ только compliance-компонента (счётчики violations на rolling window) | JSD по action distribution требует reference-калибровки — не окупается для соло-инструмента |
| (p, δ, k)-satisfaction, SPRT-сертификация | ❌ неформально | Один пользователь; порогом служит «hard violations ≥ 3/session → tighten» |
| ContractSpec DSL | ✅ упрощённый YAML (`data/contracts/`) | Декларативность нужна, полный DSL — нет |
| Композиция контрактов (C1–C4) | ❌ | Один агент за раз; Mode 1 → Mode 2 handoff покрыт precondition P2-1 |
| Overhead < 10 ms/action (Prop. 4.15) | ✅ ожидаемо | Наши проверки — regex + счётчики, O(k) |

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
| ~~I1-H2~~ | ~~No coaching~~ — **СНЯТ 2026-08-12**, см. «Пересмотр» ниже | — |
| I1-H3 | **No scoring / debrief** — no rubric, grades, overall assessment | pattern list |
| ~~I1-H4~~ | ~~No praise as coach~~ — **СНЯТ 2026-08-12** вместе с I1-H2 | — |
| I1-H5 | **Role = supportive coach** — не переключаться в экзаменатора или рекрутёра-оценщика | mode flag in prompt |
| I1-H6 | **Structure from orchestrator** — LLM не выбирает следующий topic/question | orchestrator owns `question_id`, state |

#### Пересмотр 2026-08-12: помощь разрешена, оценка — нет

Решение человека: Генри — **добрый тренер-помощник**, задача снять барьер, а не
проверять. `I1-H2` (no coaching) и `I1-H4` (no praise) **сняты**: подсказка,
предложенная форма ответа, похвала по делу и переформулировка — теперь работа
агента, а не нарушение.

**Почему это была именно контрактная правка, а не промптовая.** Енфорсер
режет фразу ДО озвучки: модель могла согласиться помогать, а пользователь
этого не слышал. Барьер держала машина.

**Что осталось в `I1-H3` и почему.** Баллы, рубрики и итоговый разбор внутри
интервью запрещены: оценка — работа Mode 2 и debrief, иначе тренировка и
разбор сливаются. Граница проходит по конкретным конструкциям
(«i'd score», «overall your», «the rubric»), а не по тону — тон машиной не
проверяется, это честно записано у I1-S1.

**Оракул границы:** `backend/tests/test_contract_coach_boundary.py` проверяет
обе стороны: подсказка и похвала проходят, баллы и итоговый разбор режутся.
Односторонний тест был бы зелёным и на пустом контракте.

### Hard governance (G_hard)

| ID | Rule | Enforcement |
|----|------|-------------|
| G1-H1 | **Max 3 sentences** per agent turn | sentence splitter + count |
| G1-H2 | **Max ~400 chars** per turn (TTS ~30 s) | length check |
| G1-H3 | **Max 2 follow-ups** per core question | orchestrator counter, not LLM |
| G1-H4 | **One question at a time** (except WRAP_UP) | in CORE/FOLLOW_UP: must contain `?` OR be short ack (≤12 words, no `?`) |

### Soft invariants (I_soft)

> **Реализуемость в MVP** (колонка MVP): ✅ — механическая проверка (regex/счётчик), enforced в коде; 📝 — только prompt-level, runtime-проверки нет (детекция «тона» регэкспом невозможна, LLM-judge в voice-цикле — неприемлемая latency). Честно пометить нереализуемое — лучше, чем декларировать неисполняемое правило (paper §8.4: false sense of security).

| ID | Rule | Recovery | MVP |
|----|------|----------|-----|
| I1-S1 | Tone: professional warm, not chatty | regenerate with stricter prompt | 📝 prompt-only |
| I1-S2 | No filler monologue before question | truncate preamble → keep last sentence with `?` | ✅ |
| I1-S3 | Acknowledgment before follow-up | if missing, prepend template *Got it.* | ✅ |

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
| I2-H2 | **Ground in transcript** — не выдумывать Q&A которых не было | LLM gets transcript; post-check: quoted Q index ∈ transcript (`question_id` в turns, doc 12) |
| I2-H3 | **No new mock interview** — не задавать interview questions как Mode 1 | reject turns matching interview-only patterns without review framing |
| I2-H4 | **Role = recruiter friend / reviewer** — coaching **allowed** | mode flag |
| I2-H5 | **Non-empty after `strip_thinking()`** — thinking-модель не съела весь num_predict | empty check до TTS → hard fail → regenerate с бóльшим num_predict → template (урок Phase 0, doc 19/20) |

#### Пересмотр 2026-08-12: помощь разрешена, оценка — нет

Решение человека: Генри — **добрый тренер-помощник**, задача снять барьер, а не
проверять. `I1-H2` (no coaching) и `I1-H4` (no praise) **сняты**: подсказка,
предложенная форма ответа, похвала по делу и переформулировка — теперь работа
агента, а не нарушение.

**Почему это была именно контрактная правка, а не промптовая.** Енфорсер
режет фразу ДО озвучки: модель могла согласиться помогать, а пользователь
этого не слышал. Барьер держала машина.

**Что осталось в `I1-H3` и почему.** Баллы, рубрики и итоговый разбор внутри
интервью запрещены: оценка — работа Mode 2 и debrief, иначе тренировка и
разбор сливаются. Граница проходит по конкретным конструкциям
(«i'd score», «overall your», «the rubric»), а не по тону — тон машиной не
проверяется, это честно записано у I1-S1.

**Оракул границы:** `backend/tests/test_contract_coach_boundary.py` проверяет
обе стороны: подсказка и похвала проходят, баллы и итоговый разбор режутся.
Односторонний тест был бы зелёным и на пустом контракте.

### Hard governance (G_hard)

| ID | Rule | Enforcement |
|----|------|-------------|
| G2-H1 | **Max 5 sentences** per turn (review may be longer than interview) | count |
| G2-H2 | **Max ~700 chars** per turn | length |
| G2-H3 | Cover each core question before WRAP_UP | orchestrator tracks `questions_reviewed[]` |

### Soft invariants (I_soft)

| ID | Rule | Recovery | MVP |
|----|------|----------|-----|
| I2-S1 | Start with strength before improvement | regenerate if only negative | 📝 prompt-only (надёжной механической проверки «only negative» нет) |
| I2-S2 | Tone: warm, collaborative (*let's*, *together*) | regenerate once | 📝 prompt-only |
| I2-S3 | Offer rephrase after critique | orchestrator nudge in prompt if missing | ✅ (nudge — детерминированная вставка в инструкцию) |

### Soft governance (G_soft)

| ID | Rule | Recovery |
|----|------|----------|
| G2-S1 | User can interrupt / ask | allow barge-in P1 |
| G2-S2 | Don't monologue > 60 s | split turn, ask *Does that make sense?* |

---

## Talk: разговор с Генри (D3a, 2026-10-17)

Третий голосовой режим — беседа на повседневные темы (`talk.contract.yaml`).

| ID | Rule | Исполнитель |
|----|------|-------------|
| I3-H1 | English only | `no_cyrillic`, на каждом предложении |
| I3-H2 | Никаких оценок: ни балла, ни уровня, ни рубрики | `forbid_patterns` + `talk_forbidden.txt`; список узкий — «score» в разговоре о матче законен, похвала — не оценка |
| I3-H3 | Роль — друг-наставник | декларативно (`mode_persona`) |
| I3-H4 | Поправки речи — только от кода (D3a.2): Генри сам не поправляет и не объясняет грамматику | `forbid_patterns` + `talk_corrections_forbidden.txt` — форма поправки и урока; «grammar», «tense» в беседе законны, перефраз мимо списка не ловится |
| G3-H1 / G3-H2 | ≤ 4 предложений, ≤ 450 символов | `max_sentences`, `max_chars_cumulative` |
| G3-H3 | Тема, прощание, конец по времени — решения кода | `orchestrator/talk.py`, не текстовая проверка |
| G3-H4 | Заметка к речи (D3a.2): фрагмент дословно в распознанном, вариант меняет слова, английский и проходит этот контракт, повтор в разговоре — не заметка; причина до пяти слов | `orchestrator/tips.py` — решение кода о кандидате модели; модель только предлагает |

Теплота и «один вопрос в ответ» — prompt-level, advisory. Просьбы к Генри
(оценка, другой язык, смена темы, прощание) узнаются **по форме** до модели и
отвечаются репликами из `data/talk/talk.yaml`; эти реплики звучат мимо
енфорсера, поэтому каждая проверяется тестом на этот контракт.

Подсказку вслух после ответа (D3a.2, talk-tips) говорит код по шаблону `tips:` из
того же `talk.yaml`: она проходит этот контракт целиком, кроме I3-H4, — и именно
I3-H4 не дал бы сказать её модели. У каждого правила `forbid_patterns` свой
`patterns_file` (до 2026-10-25 загрузчик читал один на контракт, и второе правило
проверяло чужой список).

---

## Summary generator & Vocabulary (non-voice LLM passes)

Отдельные контракты для JSON-only passes:

| Pass | Hard |
|------|------|
| Summary JSON | Valid JSON schema; EN body fields; scores 1–5 integers |
| Vocabulary extract | Each item has `term_en` + **`translation_ru` required**; no empty strings |

Voice contract enforcer **не применяется** — schema validator instead.

---

## Память Генри (D3b, 2026-10-25)

Не голосовой контракт `memory.contract.yaml`: что из предложенного моделью после
разговора станет заметкой памяти. Решает код (`backend/app/memory/`), негодный кандидат
отбрасывается целиком; числа и список «никогда» код читает из контракта.

| ID | Rule | Исполнитель |
|----|------|-------------|
| M-H1 | `{"memories": [{kind, text, follow_up, evidence}]}`, kind — plan · update · topic; годных больше трёх — первые три в порядке модели | разбор: не-JSON — отказ всего ответа, кривой кандидат — только ему |
| M-H2 | Текст, вопрос и цитата — латиница целиком | `tips.latin_only` |
| M-H3 | Цитата ≥ 3 слов дословно в ОДНОЙ его реплике; текст делит с ней значимое слово | `tips.locate`; хранится цитата в написании распознанного |
| M-H4 | Ни контактов, ни денег, ни суда, ни здоровья, ни семьи, ни Ally — и в реплике с цитатой | шаблоны `memory_never_store.txt`; перефраз мимо списка — advisory |
| M-H5 | Текст «you …» (и «your»), 3–25 слов, одно предложение без «?»; вопрос с «?», ≤ 15 слов | код формы |
| M-H6 | Общих значимых слов < 60% от МЕНЬШЕГО набора — с сохранёнными и с принятым соседом | код |
| M-H7 | Текст и вопрос проходят `talk.contract.yaml` | `contract_gate` с енфорсером разговора |

В лог об отказе идут причина, категория и число — никогда текст. Маркеры id в коде
сторожит `test_contracts.py`, как у сводки.

---

## Runtime pipeline (MVP — Contract Enforcer, sentence-gated)

**Проблема, которую решает эта секция:** «enforcer валидирует реплику целиком перед TTS» (doc 02 v0.1) несовместим с sentence-streaming TTS (doc 03): нельзя проверить «max 3 предложения», когда первое уже надо озвучивать. Буферизация полного ответа добавляет ~1.2 s к perceived latency (LLM total 1.8 s против ~0.6 s до конца первого предложения) и выбивает нас за NFR-1.1.

**Решение: инкрементальная валидация по предложениям.** Инвариант doc 02 переформулируется: **ни одно не-валидированное предложение не попадает в TTS** (гранулярность — предложение, не реплика).

```
LLM streams tokens ──▶ buffer до границы предложения (. ? !)
                              │
                    предложение s_i готово
                              ▼
              ┌────────────────────────────────┐
              │ Per-sentence hard checks:       │
              │  · Cyrillic / EN-only           │
              │  · forbidden patterns           │
              │  · cumulative chars ≤ 400       │
              │  · sentence count i ≤ 3         │
              └───────┬───────────────┬────────┘
                 pass │               │ fail
                      ▼               ▼
              s_i → TTS queue   ┌──────────────────────────────┐
              (playback идёт)   │ i == 1 (ничего не озвучено): │
                      │         │  abort stream → regenerate ≤1 │
                      │         │  → template fallback          │
                      │         │ i > 1 (s_1..s_{i-1} звучат): │
                      │         │  abort stream, truncate —     │
                      │         │  s_i и далее НЕ озвучиваются  │
                      │         └──────────────┬───────────────┘
                      ▼                        │
        stream done → turn-level checks        │
        (question_or_ack G1-H4)                │
                      │ fail: append seed      │
                      │ question (additive fix,│
                      │ ничего не «отзываем»)  │
                      └──────────┬─────────────┘
                                 ▼
                    log violation events (pre-recovery)
```

**Почему это корректно:**
- Per-sentence проверки (язык, паттерны, длина) — **монотонные**: валидность s_1..s_{i-1} не зависит от s_i. Озвученный префикс всегда compliant, что бы ни сгенерировалось дальше.
- Единственная turn-level проверка G1-H4 (question-or-ack) — **аддитивно-восстановимая**: если к концу стрима вопроса нет, дозвучиваем seed question из банка. Ничего произнесённого исправлять не нужно.
- Полный regenerate (стоит latency) случается только при нарушении в **первом** предложении — до начала озвучки; статистически это редкий случай (нарушения — обычно coaching-хвосты в конце реплики).
- Mode 2: та же схема, лимиты 5 предложений / 700 chars; плюс hard-проверка «пусто после `strip_thinking()`» **до** первого предложения (см. [20-context-token-budget.md](20-context-token-budget.md)).

### Violation event schema (logging)

Каждое срабатывание проверки — событие в session metadata (structlog + `metadata_json` сессии). **Фиксируется до recovery** (принцип paper §7.1: compliance отражает сырое поведение модели; recovery-исход пишется отдельным полем):

```json
{
  "turn_index": 7,
  "state": "FOLLOW_UP",
  "constraint_id": "I1-H2",
  "severity": "hard",
  "sentence_index": 3,
  "matched": "you should try saying",
  "recovery": "truncate",
  "recovered": true,
  "ts": "2026-07-02T..."
}
```

Per-session агрегаты (аналог метрик paper, без Θ-композита): `hard_violations`, `soft_violations`, `recovery_success_rate`, `fallback_count`. Показываются в Settings → Diagnostics; используются drift-детекцией ниже.

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

**Статус: файлы существуют** в `data/contracts/` (созданы 2026-07-02):

```
voice-interview-coach/
└── data/
    └── contracts/
        ├── interview.contract.yaml     # Mode 1 — полный контракт
        ├── review.contract.yaml        # Mode 2 — полный контракт
        ├── summary.contract.yaml       # JSON-passes (schema validation)
        ├── talk.contract.yaml          # разговор (D3a)
        ├── talk_forbidden.txt          # оценки в разговоре (I3-H2)
        ├── talk_corrections_forbidden.txt  # поправки речи — только от кода (I3-H4)
        ├── memory.contract.yaml        # память разговора (D3b), не голосовой
        ├── memory_never_store.txt      # чего память не хранит никогда (M-H4)
        ├── interview_forbidden.txt     # coaching/debrief паттерны
        └── ack_whitelist.txt           # допустимые короткие acks
```

Как и в ContractSpec из paper, YAML — декларативный и **не** Turing-complete: только именованные проверки, реализованные в `contracts/rules/`; enforcer отклоняет контракт с неизвестным `check` при загрузке (schema validation до runtime).

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
    # no_coaching снят 2026-08-12; остался только no_scoring
    - id: no_scoring
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

Paper (Def. 3.12) определяет D(t) = w_c·(compliance gap) + w_d·JSD(action distribution). Мы берём **только compliance-компоненту** (lagging indicator): наш «action vocabulary» — это текст реплик, JSD-компонента требует reference-распределение с калибровочных сессий и даёт шумный сигнал на малом словаре действий (paper Remark 3.15) — не окупается.

Rationale из paper, который применим напрямую: LLM **дрейфует со временем сессии** (E2: drift растёт во второй половине 12-turn сессий даже у frontier-моделей) — значит, пороги ниже должны срабатывать *внутри* сессии, не post-hoc:

| Signal (rolling window, из violation events) | Action |
|--------|--------|
| Hard violations ≥ 3 in one session | Log warning; tighten temperature 0.75→0.5 |
| Same soft violation ≥ 5 | Inject system reminder in next LLM call |
| Avg sentences per turn creeping up | Enforce stricter truncate |
| Recovery success < 50% за сессию | Fallback-only режим до конца сессии (canned lines) + warning в UI |

Post-MVP: rolling window on ack/question ratio, coaching pattern frequency.

---

## Requirements mapping

| Requirement | Contract |
|-------------|----------|
| FR-1.5 EN only mid-session | I1-H1, I2-H1 |
| FR-4.9 → **пересмотрено**: no scoring in interview | I1-H3 |
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
| 2026-07-02 | v0.2 (сверка с полным paper): sentence-gated enforcement — конфликт со streaming TTS закрыт; таблица «что берём из full ABC»; I2-H5 (empty after strip_thinking); soft-rules помечены ✅/📝 по реализуемости; violation event schema (pre-recovery); drift-детекция дополнена recovery-success порогом; contract YAML файлы созданы в data/contracts/ |
| 2026-10-17 | Talk (D3a): `talk.contract.yaml` — I3-H1..H3, G3-H1..H3; просьбы к Генри — по форме, до модели |
| 2026-10-25 | Память (D3b, memory-guard): `memory.contract.yaml` — M-H1..M-H7 и список `memory_never_store.txt`; исполнитель — `backend/app/memory/` |
| 2026-10-25 | Talk (D3a.2, talk-tips): I3-H4 — поправки речи только от кода, свой список; запрещённые фразы — по правилу, а не одним списком на контракт |
