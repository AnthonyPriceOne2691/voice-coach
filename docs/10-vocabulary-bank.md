# 10 — Vocabulary Bank (полезные слова)

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## Суть (принятое уточнение)

Отдельная **вкладка «Полезные слова»** — персональный словарь для расширения **разнообразия речи** на interview. После **каждого** интервью ИИ **автоматически** пополняет словарь. У каждой записи **обязателен перевод на русский**.

```
[Interview]  →  [Debrief]  →  AI извлекает vocabulary  →  [Vocabulary Bank tab]
                                                              EN term + RU translation
                                                              + example + context
```

**Зачем:** B2 async OK, но на live interview речь однообразная — словарь копит то, что реально пригодится в **твоих** ответах про automation / internal SaaS.

## Принятые решения

| Решение | Значение |
|---------|----------|
| UI | Отдельная вкладка в приложении |
| Пополнение | **Авто** после каждой сессии (часть debrief pipeline) |
| Перевод | **RU обязателен** для каждой записи |
| Язык term / example | English (interview register) |
| Debrief vs Vocabulary | Debrief остаётся EN; **перевод только во вкладке словаря** |

> Исключение из «English only»: перевод нужен для **усвоения**, не для mid-interview switching.

## Что попадает в словарь

ИИ отбирает после анализа **interview + review** transcripts и structured summary:

| Источник | Примеры |
|----------|---------|
| Слова, которых **не хватило** в ответе | Хотел сказать «trade-off», сказал «problem» |
| Более **точные** alternatives | `throughput` вместо `speed` |
| **Collocations** для interview | `measured impact`, `end-to-end ownership` |
| Technical terms из контекста | `human-in-the-loop`, `backpressure`, `idempotency` |
| Фразы-связки (разнообразие) | `The way I'd frame it…`, `What we optimized for was…` |

**Не добавлять:** базовую лексику (API, database), дубликаты без нового context, слова вне interview/SaaS/automation domain (unless session-specific gap).

**Объём за сессию:** 5–12 новых записей (merge с существующими, без spam).

## Структура записи

```json
{
  "id": "uuid",
  "term_en": "trade-off",
  "translation_ru": "компромисс; осознанный выбор между двумя вариантами",
  "type": "word | phrase | collocation",
  "example_en": "The main trade-off was latency versus cost.",
  "context_note_en": "Use when explaining architecture decisions.",
  "session_id": "uuid",
  "added_at": "2026-06-26T...",
  "category": "architecture | impact | process | fluency | technical",
  "status": "new | learning | learned",
  "times_seen": 1
}
```

### Обязательные поля (MVP)

| Поле | Required |
|------|----------|
| `term_en` | ✅ |
| `translation_ru` | ✅ **обязательно** |
| `example_en` | ✅ |
| `session_id` / `added_at` | ✅ |

### Optional (P1)

- `context_note_en` — когда использовать
- `status` — new / learning / learned (user toggle)
- `audio_tts` — озвучка term (local TTS)

## UX: вкладка «Useful Words»

```
┌─────────────────────────────────────────────────────────────┐
│  [Interview]  [History]  [Useful Words ★]  [Settings]         │
├─────────────────────────────────────────────────────────────┤
│  Search…          Filter: All | New | Architecture | …        │
│  Sort: Recent | A–Z | Category                                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │ trade-off                              [learning ▼] │   │
│  │ компромисс; выбор между двумя вариантами            │   │
│  │ "The main trade-off was latency versus cost."       │   │
│  │ Added: Session 2026-06-26 · architecture            │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ measured impact                         [new]       │   │
│  │ измеримый результат; эффект в цифрах                │   │
│  │ "We delivered measurable impact: 5 FTE to 1."       │   │
│  └─────────────────────────────────────────────────────┘   │
│  …                                                          │
│  Total: 47 words · 12 new this week                         │
└─────────────────────────────────────────────────────────────┘
```

### Поведение

- После summary — toast: *«12 new words added to Useful Words»* + link на вкладку
- На summary-screen — блок «Words added» с preview (3–5) + «View all»
- User может: удалить запись, пометить learned, редактировать перевод (manual fix)

## Pipeline (auto-populate)

```
interview_transcript + review_transcript + summary JSON
        │
        ▼
Vocabulary Extractor (LLM — sub-step после Mode 2)
        │
        ├── prompt: extract interview-useful EN terms/phrases
        ├── require translation_ru for each
        ├── require example_en in spoken interview style
        └── dedupe against existing vocabulary_bank table
        │
        ▼
Merge into SQLite `vocabulary_bank`
        │
        ▼
UI tab refresh
```

### Dedup rules

| Case | Action |
|------|--------|
| Exact same `term_en` already exists | Increment `times_seen`; update example if better |
| Same root, different phrase | New entry (e.g. `trade-off` vs `trade off X for Y`) |
| User deleted entry | Don't re-add same term from that session unless LLM flags as critical |

> Правило «deleted → don't re-add» требует **soft delete** (`status = 'deleted'`, запись остаётся в таблице) — иначе экстрактору не с чем сверять. Зафиксировано в [12-session-storage.md](12-session-storage.md).

## Фразы из разговора (D3a.2, 2026-10-23)

Второй источник банка — заметки «было → лучше» разговора с Генри (doc 11, doc 12).
Пополнение **ручное**: запись появляется только по кнопке «Add to Useful Words» у
заметки (`POST /sessions/talks/{id}/notes/{n}/vocabulary`, doc 15), а не после
каждого разговора.

| Поле | Значение |
|---|---|
| `term_en` | лучший вариант фразы (`better`) |
| `translation_ru` | qwen, тем же `translate_term`, что чинит банк (не R1, D-8); судит S-H6 — негодный перевод не записывается |
| `example_en` | предложение Антона, где стоял фрагмент, — уже с лучшим вариантом |
| `context_note_en` | `You said: “…” — причина` |
| `type` | `word` или `phrase` — по числу слов |
| `category` | `fluency` — беглость повседневной речи, а не архитектура и не импакт интервью |
| `session_id` | id разговора (`talk_sessions`) |

**Dedup явного добавления** отличается от автоматического в двух местах:

- термин уже в банке — запись не меняется вовсе, даже `times_seen`: повторное
  нажатие — не «встретилось снова»;
- термин удалён человеком — запись **возвращается**. Правило «удалённое не добавлять
  снова» защищает банк от экстрактора, который без спроса вернул бы то же слово после
  следующей сессии. Нажатие «Add» — сама просьба человека; отказ на неё значил бы,
  что удалённое слово нельзя вернуть никогда.

## LLM prompt (concept)

```
From the mock interview transcript, review dialogue, and summary, extract 5–12 English words or phrases
the candidate should add to speak more precisely and diversely in technical interviews.

For EACH item provide:
- term_en (word or short phrase)
- translation_ru (clear Russian translation — REQUIRED, not optional)
- example_en (natural spoken sentence in interview context)
- category: architecture | impact | process | fluency | technical

Skip basic vocabulary. Focus on gaps visible in the candidate's answers.
Prefer phrases that make answers sound more senior/builder-like.
```

## Storage

SQLite table `vocabulary_bank` (+ index on `term_en`, `added_at`, `status`).

Link to sessions: `session_id` FK optional for «added from session X».

Export (P2): CSV / Anki deck with EN + RU + example.

## Связь с debrief

| Debrief block | Vocabulary Bank |
|---------------|-----------------|
| `vocabulary[]` in debrief JSON | **Source** — те же items **plus** merge в persistent bank |
| Показ в debrief | Preview 5 items с переводом RU |
| Полный список | Только вкладка Useful Words |

Debrief FR-4.6 остаётся; добавляется FR-6 для persistent tab.

## MVP checklist

| # | Requirement | Phase |
|---|-------------|-------|
| 1 | Tab «Useful Words» в UI | 2 |
| 2 | Auto-add после каждой сессии | 2 |
| 3 | `translation_ru` обязателен на каждой записи | 2 |
| 4 | `term_en` + `example_en` | 2 |
| 5 | Dedup / merge с существующим словарём | 2 |
| 6 | Preview на debrief screen + link | 2 |
| 7 | Search / filter / sort | 2 |
| 8 | User: delete, mark learned | P1 |
| 9 | Export Anki/CSV | P2 |
| 10 | Spaced repetition quiz | P3 |

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial: vocabulary tab, auto-fill, mandatory RU translation |
| 2026-06-26 | Source: interview + review transcripts after Mode 2 |
| 2026-10-23 | Фразы из заметок разговора (D3a.2): ручное добавление, `category: fluency`, dedup явного действия |
