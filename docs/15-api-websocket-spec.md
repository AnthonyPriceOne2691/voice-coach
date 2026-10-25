# 15 — API & WebSocket Specification

> Voice Interview Coach · Design doc · v0.2 · 2026-07-02

## Base URLs

| Service | URL |
|---------|-----|
| REST | `http://127.0.0.1:8000` |
| WebSocket (voice) | `ws://127.0.0.1:8000/ws/session` |
| Frontend dev | `http://127.0.0.1:5273` → proxy `/sessions`, `/vocabulary`, `/settings`, `/health`, `/ws` (5173 занят другим проектом) |

> ⚠ **Список префиксов выше — часть спецификации, а не примечание.** До
> 2026-08-12 здесь стояло `proxy /api, /ws`, хотя ни один эндпоинт ниже под
> `/api` не живёт. Обе половины реализовали добросовестно и разными файлами:
> бэкенд и `lib/api.ts` пошли за перечнем эндпоинтов, `vite.config.ts` — за
> этой строкой. Результат — History и Useful Words не работали 38 дней при
> зелёных сборке, тестах и гейтах. Соответствие теперь проверяется тестом
> `dev-proxy покрывает все префиксы api.ts`; **добавляя эндпоинт с новым
> префиксом, обнови и эту строку, и `server.proxy`**.

## Auth

MVP: **none** (localhost single-user). CORS: `127.0.0.1`, `localhost` only.

---

## REST API

### `GET /health`

```json
{ "status": "ok", "version": "0.1.0" }
```

### `GET /sessions/interviews`

List interviews, newest first.

**Query:** `limit` (default 50), `offset` (default 0)

```json
{
  "items": [
    {
      "id": "uuid",
      "started_at": "2026-06-26T10:00:00Z",
      "ended_at": "2026-06-26T10:14:00Z",
      "interview_mode": "technical_project_walkthrough",
      "duration_sec": 840,
      "has_review": true,
      "review_session_id": "uuid",
      "has_debrief": true
    }
  ],
  "total": 12
}
```

### `GET /sessions/interviews/{id}`

```json
{
  "id": "uuid",
  "transcript": [{ "role": "agent", "text": "...", "timestamp_ms": 0, "turn_index": 0 }],
  "metadata": { "duration_sec": 840, "question_count": 6 },
  "debrief": null,
  "review_session_id": null,
  "status": "completed"
}
```

`status`: `in_progress` | `completed` | `failed`

### `GET /sessions/reviews/{id}`

Review transcript + link to source interview.

### `POST /sessions/interviews/{id}/review`

Start Mode 2 for a completed interview. Returns `{ "review_session_id": "uuid" }` — client opens WebSocket with that id.

### `POST /sessions/interviews/{id}/minimal-summary`

Generate **minimal summary** when user skipped Mode 2 (LLM pass on interview only).

### `DELETE /sessions/interviews/{id}`

Cascade delete linked review + debrief. Returns `204`.

### `GET /sessions/talks` (D3a.2, 2026-10-23)

Разговоры с Генри, новые первыми. **Query:** `limit` (1…100, по умолчанию 50),
`offset` (≥ 0); вне границ — **422**: разговоров с каждым днём больше, и страница без
верхней границы однажды отдала бы всё.

```json
{
  "items": [
    {
      "id": "uuid",
      "started_at": "2026-10-23T18:00:00+00:00",
      "ended_at": "2026-10-23T18:12:30+00:00",
      "duration_sec": 750,
      "status": "completed",
      "notes_count": 2
    }
  ]
}
```

`duration_sec` — `ended_at − started_at`. Без `ended_at` (разговор брошен) —
`null`: клиент пишет «not finished», а не число, которое итогом не является.

### `GET /sessions/talks/{id}`

Строка списка + `transcript` (turns, doc 12) + `language_notes` — заметки «было →
лучше» в порядке разговора (контракт — doc 12). **404** — разговора нет.

### `POST /sessions/talks/{id}/notes/{n}/vocabulary`

Лучший вариант заметки `n` (индекс в `language_notes`) → Useful Words (doc 10).

```json
{
  "status": "added",
  "term_en": "I went to the office and met my client",
  "translation_ru": "Я пошёл в офис и встретился с клиентом"
}
```

`status`: `added` — записано или возвращено удалённое человеком; `exists` — уже в
банке: ничего не меняется, модель не зовётся. **502** — перевод не прошёл S-H6 или
модель недоступна, ничего не записано. **404** — нет разговора или заметки с таким
номером; отрицательный номер — тоже 404, а не «последняя заметка».

### `GET /sessions/talks/{id}/notes/{n}/audio`

`audio/wav` — лучший вариант голосом Генри в сохранённом темпе `speech_length_scale`:
тот же коридор, что у сессии; не число или вне коридора — темп по умолчанию. **404** —
как выше.

### `GET /vocabulary`

**Query:** `q`, `category`, `sort` (`recent` | `alpha`), `limit`, `offset`

### `GET /vocabulary/{id}`

Single entry.

### `DELETE /vocabulary/{id}`

Soft delete — `status='deleted'`, запись остаётся для dedup-правила «don't re-add» ([12-session-storage.md](12-session-storage.md)). (P1 user edit.)

### `GET /settings` / `PATCH /settings`

Хранение: key-value таблица `settings` в том же `app.db` (один файл-источник, бэкап копированием — см. [12-session-storage.md](12-session-storage.md)).

```json
{
  "show_live_transcript": true,
  "interview_duration_min": 15,
  "silence_threshold_ms": 2000,
  "speech_length_scale": 1.15,
  "mic_device_id": null
}
```

`speech_length_scale` — темп речи агента (Piper `length_scale`: 1.0 = нативный
темп голоса, больше = медленнее). Меняется двумя путями: этим PATCH'ем и
**голосом внутри сессии** («speak slower» — мета-ход, см. [04](04-interview-orchestrator.md)),
причём голосовой путь пишет сюда же, поэтому темп переживает сессию.

Коридор — `0.85 … 1.60`. Значение вне коридора PATCH **отвергает кодом 422**, а
не зажимает молча: молчаливый зажим неотличим от принятого значения, и клиент
получил бы 200 на настройку, которая не применилась.

`mic_device_id` — микрофонный вход (`MediaDeviceInfo.deviceId`), `null` =
системный по умолчанию. Сервер проверяет только форму (строка ≤ 256 символов или
`null`, иначе 422): существование устройства знает **только браузер**, и id он
«солит» под origin — при очистке данных сайта сохранённое значение перестаёт
находиться.

Отсюда правило для клиента: вход открывается как `deviceId: { exact }`, а не
`{ ideal }`. `ideal` при пропаже устройства молча откроет другой микрофон —
человек узнает об этом по плохому распознаванию, а не из интерфейса. Фолбэк на
системный вход разрешён, но обязан быть **видимым** (то же правило, что 422 на
темп). Отказ в доступе (`NotAllowedError`) фолбэком не лечится: это другая
причина и другое лечение.

---

## WebSocket: `/ws/session`

One connection per active voice session (Mode 1 or Mode 2).

### Connection

```
ws://127.0.0.1:8000/ws/session
```

Client sends `hello` immediately after open.

### Message envelope

All messages JSON:

```json
{ "type": "<message_type>", "payload": { } }
```

Optional top-level `request_id` for correlating errors.

---

### Client → Server

#### `hello`

```json
{
  "type": "hello",
  "payload": {
    "client_version": "0.1.0",
    "capabilities": ["webm_opus"]
  }
}
```

Server responds `ready`.

#### `start_interview`

```json
{
  "type": "start_interview",
  "payload": {
    "mode": "technical_project_walkthrough",
    "duration_min": 15
  }
}
```

Server: pre-warm Qwen model → `state: processing` → first agent turn → `audio` chunks.

#### `start_review`

```json
{
  "type": "start_review",
  "payload": {
    "interview_id": "uuid"
  }
}
```

Server: evict Qwen → load R1 → begin review intro.

#### `start_talk` (D3a, 2026-10-17)

```json
{ "type": "start_talk", "payload": {} }
```

Разговор с Генри на повседневные темы. Server: `session_started {session_kind:
"talk"}` → приветствие и открывающий вопрос (их выбирает код, модель не вызывается)
→ `listening`. В `state` поля вопроса — `null`. По «bye» или через 20 минут Генри
прощается, и приходит `session_ended {next_action: "none"}`.

#### `utterance_end`

User finished speaking (client VAD).

```json
{
  "type": "utterance_end",
  "payload": {
    "audio_base64": "<webm opus or wav>",
    "mime": "audio/webm",
    "duration_ms": 8200
  }
}
```

#### `barge_in` (P1)

```json
{ "type": "barge_in", "payload": {} }
```

**MVP (без barge-in):** в состоянии `speaking` клиент **не захватывает микрофон**; `utterance_end`, пришедший в `speaking`/`processing`, сервер отвергает без side effects (state event перешлётся клиенту).

#### `end_session`

```json
{
  "type": "end_session",
  "payload": {
    "reason": "user"
  }
}
```

#### `ping`

```json
{ "type": "ping", "payload": {} }
```

---

### Server → Client

#### `ready`

```json
{
  "type": "ready",
  "payload": {
    "server_version": "0.1.0",
    "ollama_ok": true
  }
}
```

#### `state`

```json
{
  "type": "state",
  "payload": {
    "value": "idle|listening|processing|speaking|loading_model",
    "session_kind": "interview|review|talk|null",
    "session_id": "uuid|null",
    "question_index": 3,
    "question_total": 6,
    "question_kind": "behavioral|technical|null"
  }
}
```

Три последних поля (с 2026-08-13) — «вопрос N из M и какого класса». Нужны
экрану сессии: знать, сколько осталось, снимает тревогу, а это и есть задача
тренажёра. У Mode 2 своего счётчика вопросов нет, поэтому там все три `null` —
**клиент обязан быть готов к `null`**, а не только к числам.

#### `model_loading`

Shown during Qwen ↔ R1 swap (~5–15 s).

```json
{
  "type": "model_loading",
  "payload": {
    "model": "deepseek-r1:14b",
    "message": "Loading review model..."
  }
}
```

#### `transcript`

```json
{
  "type": "transcript",
  "payload": {
    "role": "user|agent",
    "text": "Walk me through an internal tool you built.",
    "turn_index": 1,
    "final": true
  }
}
```

`final: false` — optional partial STT (P2 streaming).

#### `audio`

```json
{
  "type": "audio",
  "payload": {
    "chunk_base64": "<wav>",
    "mime": "audio/wav",
    "final": false
  }
}
```

`final: true` on last chunk of agent turn.

#### `session_started`

```json
{
  "type": "session_started",
  "payload": {
    "session_kind": "interview",
    "session_id": "uuid"
  }
}
```

#### `session_ended`

```json
{
  "type": "session_ended",
  "payload": {
    "session_kind": "interview",
    "session_id": "uuid",
    "duration_sec": 842,
    "next_action": "offer_review"
  }
}
```

`next_action`: `offer_review` | `generate_summary` | `none`

#### `summary_ready`

After Mode 2 or minimal-summary REST job.

```json
{
  "type": "summary_ready",
  "payload": {
    "interview_id": "uuid",
    "debrief_id": "uuid"
  }
}
```

#### `error`

```json
{
  "type": "error",
  "payload": {
    "code": "STT_EMPTY|OLLAMA_DOWN|CONTRACT_FAIL|MIC_DENIED|INTERNAL",
    "message": "Human-readable",
    "recoverable": true
  }
}
```

#### `pong`

Response to `ping`.

---

## Error codes

| Code | When | Client action |
|------|------|---------------|
| `STT_EMPTY` | No speech / too short (< 700 ms или < 2 слов) | Show hint, return to listening |
| `OLLAMA_DOWN` | Cannot reach Ollama | Block start, link to setup |
| `CONTRACT_FAIL` | Enforcer exhausted retries | Agent uses template line |
| `MODEL_LOAD_FAIL` | R1/Qwen load timeout | Retry or abort |
| `SESSION_NOT_FOUND` | Bad interview_id for review | Toast + History |
| `MIC_DENIED` | Client-side | Settings instructions |
| `TTS_FALLBACK` | Piper упал → перешли на macOS `say` | Warning toast; сессия продолжается |
| `PIPELINE_FAILURE` | Ollama/STT умерли mid-session после retry | Сессия завершена, transcript сохранён |

## Mid-session failure policy

Принцип: **transcript — единственный невосполнимый артефакт**. При любом отказе — немедленный flush в SQLite, затем деградация по матрице:

| Отказ mid-session | Реакция сервера |
|-------------------|-----------------|
| Ollama не отвечает | 1 retry (backoff 2 s) → fail: flush transcript → `session_ended {reason: "pipeline_failure"}` → сессия в History со `status: failed`, partial transcript виден, доступна кнопка minimal summary |
| STT ошибка / пусто | Агент говорит **template-строку** (не LLM): «Sorry, I didn't catch that — could you repeat?»; **2 подряд** отказа → завершение как при pipeline_failure |
| Piper упал | Fallback на macOS `say` до конца сессии + `TTS_FALLBACK` event — сессия **не прерывается** (голос важнее тембра, NFR-4.1) |
| WS disconnect | Checkpoint уже на диске (3 turns / 30 s); сессия `in_progress` в History; resume — P1 |

---

## Session state machine (transport layer)

```
idle ──start_interview──▶ loading_model ──▶ speaking (intro)
                              │
listening ◀── utterance_end ──┤
     │                        │
     └──▶ processing ──▶ speaking ──▶ listening
                              │
                    end_session / timer
                              ▼
                         session_ended
```

---

## Checkpointing

Every **3 turns or 30 s** (что раньше — как в [12-session-storage.md](12-session-storage.md)) server persists transcript (`status: in_progress`).  
On disconnect: interview remains resumable from History (P1); в MVP partial transcript виден в History как `in_progress`.

---

## Phase mapping

| Endpoint / message | Phase |
|--------------------|-------|
| `/health`, `hello`, `start_interview`, `utterance_end`, `transcript`, `audio` | 1 |
| `start_review`, model swap, REST History | 2 |
| `minimal-summary`, vocabulary REST | 2 |
| `/sessions/talks*` — разговоры и заметки | D3a.2 |
| `barge_in`, resume session | P1 |

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial API + WebSocket spec |
| 2026-07-02 | v0.2: MVP-поведение mic при `speaking` (no barge-in); checkpoint «3 turns or 30 s» согласован с doc 12; DELETE /vocabulary — soft delete |
| 2026-07-02 | v0.3: mid-session failure policy (матрица деградации, flush-first); коды TTS_FALLBACK, PIPELINE_FAILURE; settings — kv-таблица в app.db |
| 2026-10-17 | `start_talk`, `session_kind: talk` — разговор с Генри (D3a) |
| 2026-10-23 | REST разговоров и заметок «было → лучше»: страница, деталь, Useful Words, звук (D3a.2) |
