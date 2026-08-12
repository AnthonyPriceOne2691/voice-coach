# 05 — Knowledge Base & Personalization

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## Назначение

Агент задаёт **релевантные** вопросы и follow-ups, проверяет consistency с positioning, а debrief опирается на реальный профиль — не generic interview prep.

## Источники (workspace)

| Файл | Содержание | Использование |
|------|------------|---------------|
| `ANTON_ASPIDOV_CV_EN.md` | Positioning, опыт, skills | Источник для профиля; в промпт НЕ инжектится |
| `PORTFOLIO_LINKBUILDER_CASE.md` | Architecture, metrics, HITL | То же: источник, не инжектится |
| `FOREIGN_MARKET_OUTREACH_PLAN.md` | Target roles, keywords | Question framing, debrief consistency |
| `Documents/PORTFOLIO_SITE_DESIGN.md` §5 | Аудит четырёх репозиториев 2026-07-20 | Источник цифр по проектам вне LinkBuilder |

**Что реально попадает в промпт (2026-08-12):** только `profile_condensed.md`
через плейсхолдер `{{profile_condensed}}` (`app/knowledge/prompts.py`). Остальные
файлы — исходники, из которых профиль поддерживается вручную.

**Статус (2026-07-02):** копии CV и case study **закоммичены** в `data/knowledge/` вместе с готовым `profile_condensed.md`. Решение: хранить в git (репозиторий приватный) — версионирование нужно для воспроизводимости debrief; gitignore здесь вредит.

## Knowledge injection (MVP — no RAG)

```
┌────────────────────────────────────────┐
│ System prompt (static template)        │
│  + condensed CV (≤ 1500 tokens)        │
│  + case study summary (≤ 2000 tokens)  │
│  + positioning rules                   │
│  + weak spots to probe                 │
└────────────────────────────────────────┘
```

### Condensed profile (maintain manually)

Отдельный файл `data/knowledge/profile_condensed.md` — **не** raw CV, а extract:

- One-liner positioning: AI Automation Engineer, internal SaaS
- 3 flagship projects with metrics
- Tech stack keywords
- **Anti-patterns:** не представляться SEO lead; builder/automation angle
- Known interview weak spots

**Причина:** полный CV + case в каждый prompt = медленно и дорого по context; condensed version обновляется вручную после правок CV.

### Портфолио: индекс в профиле, глубина — за оркестратором (2026-08-12)

Проектов пять (LinkBuilder, Voice Coach, Local Web Agent, Lash Try-On, Event
Content System). Пять полных кейсов — ~5000 токенов сверх бюджета: при
`num_ctx` 8192 они вытеснили бы транскрипт и удлинили prefill КАЖДОГО хода,
то есть ударили бы по latency-инварианту ~3.0 s (doc 20).

**Решение:** в профиле — индекс с цифрами (≤1500 токенов, проверяется
`backend/tests/test_knowledge_profile.py`). Слот `case study ≤ 1000` остаётся
пустым до тех пор, пока оркестратор не научится выбирать проект: чей кейс
подставить — решение о структуре интервью, а структурой владеет оркестратор
(I1-H6, doc 04), не промпт.

### Источник цифр — замер, а не CV (решение человека 2026-08-12)

Числа в профиле измерены по репозиториям, дата замера указана в шапке файла.
Где CV расходится — прав замер, а CV попадает в список правок для человека.
Замер 2026-08-12: LinkBuilder 7,393 тест-функции (CV говорит 4,200+),
Local Web Agent 409 (CV — 380). Агент не правит CV сам: это заявление
человека о себе.

**Цена решения:** агент может спросить про цифру, которой в текущем CV нет.
Принято сознательно — кандидат обязан знать свои системы лучше, чем резюме.

## Positioning rules (for agent & debrief)

| Do | Don't |
|----|-------|
| Automation engineer, internal tools, LLM apps | SEO lead, link building manager |
| Measurable impact (5→1 FTE, cycle time) | Vague «improved efficiency» |
| HITL, queues, behavioral contracts | Buzzwords without architecture |
| Trade-offs and failures | Only success stories |

## Weak spots to probe (from brief)

1. Live system design on English
2. Long monologues without structure
3. SEO angle instead of builder angle
4. Pauses / filler words under follow-up pressure

Orchestrator и debrief **явно помечают** эти паттерны.

## Debrief

Полная спецификация post-session feedback — в **[08-post-session-debrief.md](08-post-session-debrief.md)**.

Knowledge base поставляет debrief generator:

- condensed profile + positioning rules
- weak spots to probe
- target role keywords

Debrief prompt strategy:

- Separate LLM call **after** session (temperature 0.3)
- Full transcript + rubric template + positioning rules
- Output: structured JSON + markdown для UI

## Session memory (P1)

SQLite table `session_summaries`:

```
session_id, date, scores_json, next_session_focus, questions_asked[]
```

Before new session, orchestrator loads last 3 summaries → prompt snippet:

«In previous sessions, candidate struggled with: … Focus follow-ups on: …»

## RAG (post-MVP)

When to add:
- Documents > 8K tokens combined
- Multiple case studies
- Company-specific prep packs

**Design placeholder:**
- Chunk size 500 tokens, overlap 50
- Embed with local model (nomic-embed)
- Retrieve top-k per question theme

## Maintenance workflow

1. Update CV/case in workspace
2. Refresh `profile_condensed.md` (manual or script)
3. Version in git — debrief reproducibility

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial knowledge base design |
| 2026-06-26 | Debrief section moved to 08-post-session-debrief.md |
| 2026-07-02 | data/knowledge/ создан: копии CV + case study + profile_condensed.md; решение — коммитить в git (приватный репо, воспроизводимость debrief) |
