# 05 — Knowledge Base & Personalization

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## Назначение

Агент задаёт **релевантные** вопросы и follow-ups, проверяет consistency с positioning, а debrief опирается на реальный профиль — не generic interview prep.

## Источники (workspace)

| Файл | Содержание | Использование |
|------|------------|---------------|
| `ANTON_ASPIDOV_CV_EN.md` | Positioning, опыт, skills — копия CV от 2026-10-08 | Источник позиционирования и названий проектов; в промпт НЕ инжектится |
| `PORTFOLIO_LINKBUILDER_CASE.md` | Architecture, metrics, HITL | То же: источник, не инжектится |
| `FOREIGN_MARKET_OUTREACH_PLAN.md` | Target roles, keywords | Question framing, debrief consistency |
| `Documents/PORTFOLIO_SITE_DESIGN.md` §5 | Аудит четырёх репозиториев 2026-07-20 | Исторический источник; с 2026-10-17 цифры берутся из замеров ниже |
| `portfolio-site/tests/numbers.test.mjs` | Замер 2026-10-08 двух сервисов агентства (тесты, строки, PR) | Цифры SEO case-study и Prospecting & outreach platform |
| `G connect/MEMORY.md` | Снапшот проекта 2026-10-02 (тесты, правила) | Цифры G connect |
| `Prepare/rag/README.md`, `Prepare/CODE_QUALITY_GATES.md` | Замеры RAG по канону; число проверок контура | Цифры RAG over a rulebook и Quality contour |

**Что реально попадает в промпт (сверено 2026-10-25):** только `profile_condensed.md`
через плейсхолдер `{{profile_condensed}}` (`app/knowledge/prompts.py`) — в промпты
интервью, разбора, разговора и обеих сводок. В сводки — с 2026-10-25: до того они
объявляли профиль входом, а подстановки не было (поставка `summary-profile`). Остальные
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

- Кто он и позиционирование: AI Delivery Lead (с 2026-10); прежняя должность AI Automation Engineer
- Чем занят сейчас и зачем ему разговорный английский (с 2026-10-17)
- Индекс проектов, у каждого — измеренная цифра
- Как он работает и стек
- **Anti-patterns:** не представляться SEO lead; builder/delivery angle
- Known interview weak spots

Личное (семья, быт, хобби) в профиль **не пишется** — решение человека
2026-10-17: Генри узнаёт его только из разговоров и только то, что Антон скажет
сам. Сторож — `test_profile_keeps_private_life_out`.

**Причина:** полный CV + case в каждый prompt = медленно и дорого по context; condensed version обновляется вручную после правок CV.

### Портфолио: индекс в профиле, глубина — за оркестратором (2026-08-12)

Проектов было пять (LinkBuilder, Voice Coach, Local Web Agent, Lash Try-On, Event
Content System); с 2026-10-17 — десять: добавлены SEO case-study platform,
Prospecting & outreach platform, Quality contour, G connect и RAG over a rulebook.
Всё та же форма — строка индекса с цифрой на проект, профиль ~1270 токенов. Пять полных кейсов — ~5000 токенов сверх бюджета: при
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

Сверка 2026-10-17 (поставка `profile-refresh`): Voice Coach — 213 backend + 51
front-end тестов; правил в трёх контрактах 21, на каждом предложении проверяются
10. Расхождения CV и сайта с замером (G connect 400+/34 против 605/43, бриф сайта
«21 rules checked on every sentence») отданы человеку списком в `plan.md` поставки.

## Positioning rules (for agent & debrief)

> Живая таблица — раздел `Positioning rules` в `profile_condensed.md`: по ней судят
> позиционирование обе сводки (с 2026-10-25). Ниже — исходная редакция 2026-07-02.

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
| 2026-10-17 | Профиль на октябрь: AI Delivery Lead, нынешняя работа, зачем английский, десять проектов с датированными замерами; личное в профиль не пишется; копия CV от 2026-10-08 |
| 2026-10-25 | Профиль впервые доходит до обеих сводок; живая таблица позиционирования — в профиле |
