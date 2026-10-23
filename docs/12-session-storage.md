# 12 — Session Storage & History

> Voice Interview Coach · Design doc · v0.2 · 2026-07-02  
> **Канонический источник** схемы хранения; doc 11 зеркалит её.

## Назначение

Спецификация хранения **interview** и **review** диалогов. Дополняет [11-two-modes-review-dialogue.md](11-two-modes-review-dialogue.md).

## Принципы

| Принцип | Описание |
|---------|----------|
| **Everything local** | SQLite + optional JSON export |
| **Full transcripts** | Каждый turn: role, text, timestamp |
| **Linked pairs** | Review всегда привязан к interview |
| **No silent loss** | Checkpoint transcript каждые N turns во время live session |
| **User control** | Delete interview (cascade review), export |

## Transcript turn format

```json
{
  "role": "agent | user",
  "text": "Walk me through an internal tool you built.",
  "timestamp_ms": 12500,
  "turn_index": 3,
  "state": "CORE_QUEST",
  "question_id": "llm_pipeline",
  "question_kind": "technical"
}
```

Кроме фаз машины состояний, `state` принимает одно **мета**-значение —
`PACE_REQUEST`: просьба сменить темп речи и ответ на неё (doc 04). Такой turn
записывается (он произошёл, и пользователь его слышал), но `question_id` у него
`null`, поэтому он не попадает ни в `build_segments` для Mode 2, ни в промпт
суммаризации: это не реплика по существу, и в разборе она выглядела бы ответом.

`question_kind` — класс вопроса (`technical` | `behavioral`, doc 04). Пишется
рядом с `question_id`, потому что банк вопросов — **данные**: они меняются, и по
одному `question_id` через полгода уже не сказать, каким был вопрос. У мета-ходов
и у ходов без вопроса — `null`.

`state` и `question_id` пишет orchestrator (он владеет структурой — doc 04). **Зачем обязательно в MVP:** Mode 2 grounding (I2-H2: «quoted Q index ∈ transcript») и evidence в summary («Q3, ~04:15») требуют знать, какой turn относится к какому вопросу. Восстанавливать это post-hoc из текста — ненадёжно; на записи это бесплатно. Для user-turns `question_id` = вопрос, на который отвечает; в review-сессиях `question_id` = разбираемый вопрос интервью.

## Tables

### `interview_sessions`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| started_at | ISO8601 | |
| ended_at | ISO8601 | |
| interview_mode | TEXT | `technical_and_behavioral` с 2026-08-13; раньше `technical_project_walkthrough` — старые записи так и остаются, они описывают другую сессию |
| persona | TEXT | `senior_colleague` |
| transcript_json | TEXT | JSON array of turns |
| metadata_json | TEXT | `{duration_sec, question_count, ...}` |
| debrief_json | TEXT | NULL until summary generated |
| summary_kind | TEXT | NULL \| `minimal` (skip review) \| `full` (after Mode 2) |
| status | TEXT | `in_progress` \| `completed` \| `failed` — для checkpoint/resume |
| review_session_id | TEXT | NULL → FK when review done |
| created_at | ISO8601 | |

### `review_sessions`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| source_interview_id | UUID | FK → interview_sessions |
| started_at | ISO8601 | |
| ended_at | ISO8601 | |
| persona | TEXT | `recruiter_friend` |
| transcript_json | TEXT | JSON array of turns |
| metadata_json | TEXT | `{duration_sec, questions_reviewed, ...}` |
| created_at | ISO8601 | |

### `talk_sessions` (D3a, 2026-10-17)

Разговор с Генри — **своя таблица**, а не `interview_sessions` с особым режимом:
History и суммаризация читают ту таблицу как интервью, и разговор получил бы
«Review together» и сводку, которых у него нет.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| started_at / ended_at / created_at | ISO8601 | |
| persona | TEXT | `friend_mentor` |
| transcript_json | TEXT | turns; `state` — `INTRO` \| `CHAT` \| `TOPIC` \| `REQUEST` \| `GOODBYE` (чем оказалась реплика), `question_id` — `null` |
| metadata_json | TEXT | `{phase, topics, hard_violations, soft_violations, fallback_count}` |
| status | TEXT | `in_progress` \| `completed` \| `failed` |

Общие колонки записи сессии (`started_at` … `created_at`) живут в миксине
`SessionRecord` (`storage/models.py`).

**Заметки «было → лучше» (D3a.2, 2026-10-23)** — ключ `language_notes` в
`metadata_json`: список в порядке разговора. Пишет **только** проверка речи
(talk-check), читает REST (doc 15); у разговоров до проверки речи ключа нет — это
пустой список.

| Поле | Значение |
|---|---|
| `turn_index` | `turn_index` реплики Антона в транскрипте |
| `kind` | `error` (ошибка) \| `style` (бедная речь) |
| `said` | дословный фрагмент распознанной реплики |
| `better` | лучший вариант |
| `why` | причина до пяти английских слов, может быть `""` |
| `spoken` | прозвучала ли подсказка вслух; до поставки talk-tips — `false` |

Заметка без строк `said` и `better` — нарушение контракта со стороны записи: читатель
пропускает её с записью в лог, а не роняет экран. Номер заметки в адресах REST —
индекс в списке, который отдаёт `GET /sessions/talks/{id}`.

### `vocabulary_bank`

См. [10-vocabulary-bank.md](10-vocabulary-bank.md) — `session_id` может ссылаться на interview, review или разговор (фраза из заметки, D3a.2).

**Удаление — soft delete:** `status = 'deleted'` вместо физического DELETE. Иначе правило dedup «user deleted entry → don't re-add same term» (doc 10) нереализуемо — экстрактору не с чем сверяться.

### `settings`

Key-value: `key TEXT PRIMARY KEY, value_json TEXT, updated_at ISO8601`. Все пользовательские настройки (doc 17) — в том же `app.db`: один файл-источник, бэкап = копия файла, без отдельного config-формата.

## API (conceptual)

| Endpoint | Action |
|----------|--------|
| `GET /sessions/interviews` | List interviews |
| `GET /sessions/interviews/{id}` | Interview + transcript + debrief + linked review |
| `GET /sessions/reviews/{id}` | Review transcript |
| `POST /sessions/interviews/{id}/review` | Start Mode 2 for past interview |
| `DELETE /sessions/interviews/{id}` | Delete interview + linked review |
| `GET /sessions/talks` | List talks, page of `limit` ≤ 100 (D3a.2) |
| `GET /sessions/talks/{id}` | Talk + transcript + `language_notes` |

## Checkpoint during live session

Каждые **3 turns** или **30 s** — flush transcript to SQLite (status `in_progress`).  
On crash → resume or show partial in History.

## Export (P2)

- Interview transcript → `.md` / `.txt`
- Review transcript → `.md`
- Pair bundle → zip

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial storage spec for interview + review |
| 2026-07-02 | v0.2: turn format + `state`/`question_id` (grounding Mode 2, evidence в summary); колонки `summary_kind`, `status`; vocabulary soft delete; объявлен каноном схемы |
| 2026-07-02 | v0.3: таблица `settings` (kv в app.db) |
| 2026-10-17 | Таблица `talk_sessions` — разговор с Генри (D3a) |
| 2026-10-23 | `talk_sessions.metadata_json.language_notes` — заметки «было → лучше» (D3a.2); `vocabulary_bank.session_id` — и разговор |
