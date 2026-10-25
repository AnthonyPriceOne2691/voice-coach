# 16 — Prompts Library

> Voice Interview Coach · Design doc · v0.2 · 2026-07-02  
> **Канонический источник** параметров LLM-вызовов (model / temp / max_tokens); doc 07 зеркалит эту таблицу.

## File layout (актуальное состояние `data/prompts/`)

```
data/prompts/
├── interviewer_system.txt      # Mode 1 system                    ✅ exists
├── review_system.txt           # Mode 2 system                    ✅ exists
├── summary_system.txt          # Post-review JSON (incl. vocabulary) ✅ exists
├── minimal_summary_system.txt  # Skip-review fallback             ✅ exists
├── translate_term_system.txt   # Починка перевода термина (S-H6) ✅ exists
├── talk_system.txt             # Talk: друг-наставник (D3a)        ✅ exists
├── language_check.txt          # Talk: просьба о проверке речи (D3a.2) — НЕ системный
│                               #   промпт: дописывается в конец истории разговора
└── templates/
    ├── interview_intro.txt                                        ✅ exists
    ├── interview_wrap_up.txt                                      ✅ exists
    └── contract_fallback.txt                                      ⚠ exists, не читается никем
```

**Vocabulary extraction — не отдельный файл в MVP:** входит в `summary_system.txt` (поле `vocabulary[]` схемы из doc 08). Отдельный `vocabulary_extract.txt` — P1, только если общий pass извлекает словарь плохо.

Prompts loaded at startup; **not** embedded in Python (DRY + versioning).

Knowledge injected via `{{profile_condensed}}` placeholder (from `data/knowledge/profile_condensed.md`).

---

## Decisions reflected in prompts

| Decision | Prompt impact |
|----------|-----------------|
| D-4: skip TMAY | INTRO short → first question = project walkthrough |
| Mode 1 no coaching | Hard rules in system + contract enforcer |
| English only (session) | Explicit in all mode prompts |
| Positioning | Profile stresses AI Automation Engineer, not SEO lead |

---

## `interviewer_system.txt` (Mode 1)

See file: [`data/prompts/interviewer_system.txt`](../data/prompts/interviewer_system.txt)

**Orchestrator overrides:** LLM receives `current_state`, `question_seed`, `follow_up_count` in user turn wrapper — not in system file.

**User turn wrapper (code, not file):**

```
[STATE=CORE_QUESTION]
[QUESTION_ID=2]
[FOLLOW_UP_COUNT=0]
Candidate answer:
{transcript}
```

---

## `review_system.txt` (Mode 2)

See [`data/prompts/review_system.txt`](../data/prompts/review_system.txt)

**Injected context:** segmented Q&A from interview (`Q1: ... / A1: ...`).

---

## `summary_system.txt`

Structured JSON only. Temperature **0.3**. Model: **deepseek-r1:14b**, `num_ctx: 16384` (два транскрипта, см. [20-context-token-budget.md](20-context-token-budget.md)).

Output must match schema in [08-post-session-debrief.md](08-post-session-debrief.md). Включает `vocabulary[]` — каждый term **must** include `translation_ru`.

---

## `minimal_summary_system.txt`

When user skips Mode 2: shorter JSON — `scores` (rough), `strengths`, `improvements` (max 3), **no** rich vocabulary list.

---

## Regeneration prompts (contract recovery)

**Strict regenerate — одна подсказка на все режимы** (константа `STRICT_REGENERATE` в
`backend/app/voice/turn_runner.py`, с 2026-10-17 без правил экзаменатора, L73):

```
Your previous reply broke a rule of this session: {violation}. Rewrite it in English only,
keeping your role, the limits you were given and the original intent: {intent}
```

Поле `recovery.regenerate_prompt: strict_regenerate` контрактов кодом не читается, файла
с таким именем в `data/prompts/` нет — свой текст на режим остаётся долгом (сторож
`test_contract_keys.py`, 2026-10-25).

**Template fallback:** запасная реплика — `seed` плана оркестратора (вопрос банка,
реплика `fallback` разговора). `data/prompts/templates/contract_fallback.txt` не читает
никто с 2026-07-02.

---

## Model assignment (канон)

> `max_tokens` (`num_predict`) для R1 **включает thinking-токены** — поэтому значения ≫ видимого output. С 220–450 R1 возвращает пустой ответ (доказано Phase 0, doc 19).

| Prompt file | Model | num_ctx | max_tokens | temp |
|-------------|-------|---------|------------|------|
| interviewer_system | qwen2.5:14b-instruct | 8192 | 220 | 0.75 |
| review_system | **qwen2.5:14b-instruct** (D-8 закрыт, doc 14) | 8192 | 300 | 0.6 |
| summary_system | deepseek-r1:14b | **16384** | 4096 | 0.3 |
| minimal_summary | **qwen2.5:14b-instruct** (уже загружен при Skip — без model swap) | 8192 | 800 | 0.3 |
| talk_system | qwen2.5:14b-instruct | 8192 | 200 | 0.8 |
| language_check (просьба в конце разговора, ответ — JSON-схема `CANDIDATE_SCHEMA`, D3a.2) | qwen2.5:14b-instruct — тот же префикс и `num_ctx`, что у ответа | 8192 | 120 | 0.0 |
| translate_term_system | qwen2.5:14b-instruct (не R1 — он источник утечки, S-H6) | 8192 | — | 0.3 |

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial prompt library + data files |
| 2026-07-02 | v0.2: канонизация params (были расхождения с doc 07); R1 max_tokens с учётом thinking; vocabulary merged в summary; убран несуществующий vocabulary_extract.txt из MVP layout |
| 2026-07-02 | v0.3: minimal_summary → qwen2.5:14b-instruct (без swap при Skip) |
| 2026-10-23 | Talk и починка перевода в раскладке и таблице моделей; `language_check.txt` — просьба о проверке речи в конце истории разговора (D3a.2) |
| 2026-10-25 | Перегенерация — нынешний текст `STRICT_REGENERATE` вместо экзаменаторского; `regenerate_prompt` контрактов и `contract_fallback.txt` не читаются (contract-keys) |
