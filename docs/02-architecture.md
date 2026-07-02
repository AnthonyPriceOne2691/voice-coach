# 02 — Architecture

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## High-level diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (Browser)                         │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Mic in   │  │ Session UI   │  │ Useful Words tab + Debrief view │
│  └────┬─────┘  └──────┬───────┘  └──────────────────────────┘  │
└───────┼───────────────┼──────────────────────────────────────────┘
        │ WebSocket/REST│
        ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI, local)                      │
│                                                                  │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │ Voice Gateway   │───▶│ Interview Orchestrator (Mode 1)  │   │
│  │ (audio I/O)     │    │ Review Orchestrator (Mode 2)       │   │
│  └────────┬────────┘    └──────────────┬───────────────────┘   │
│           │                            │                        │
│     ┌─────▼─────┐              ┌───────▼────────┐              │
│     │ STT       │              │ LLM Engine     │              │
│     │ (Whisper) │              │ (Ollama/MLX)   │              │
│     └───────────┘              └───────┬────────┘              │
│           ▲                            │                        │
│     ┌─────┴─────┐              ┌───────▼────────┐              │
│     │ TTS       │◀─────────────│ Contract       │◀── LLM     │
│     │ (local)   │              │ Enforcer       │              │
│     └───────────┘              └────────────────┘              │
│                                                                  │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │ Session Store   │    │ Knowledge Loader                 │   │
│  └─────────────────┘    └──────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Summary Generator (post Mode 2)                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. Client

**Назначение:** захват аудио, воспроизведение TTS, UI сессии и debrief.

**MVP scope:**
- Кнопка Start / End session
- Индикатор состояния: `idle | listening | processing | speaking`
- Отображение live transcript (optional, полезно для отладки)
- Экран debrief после сессии
- Вкладка **Useful Words** — persistent vocabulary bank (см. [10-vocabulary-bank.md](10-vocabulary-bank.md))

**Технология (гипотеза):** React + Vite, `MediaRecorder` / Web Audio API, WebSocket к backend.

### 2. Voice Gateway

**Назначение:** маршрутизация аудио между client и STT/TTS; VAD (voice activity detection) для определения конца реплики пользователя.

**Ответственность:**
- Приём audio chunks с клиента
- Детекция end-of-utterance (пауза N ms или VAD)
- Отправка финального аудио в STT
- Стриминг или batch TTS обратно на клиент

### 3. STT (Speech-to-Text)

**Назначение:** транскрипция речи пользователя на английском.

**MVP:** локальный Whisper (см. [03-voice-pipeline.md](03-voice-pipeline.md)).

### 4. LLM Engine

**Назначение:** генерация реплик interviewer и post-session debrief.

**MVP:** локальная модель через Ollama или MLX; system prompt + session history + knowledge snippets.

### 5. TTS (Text-to-Speech)

**Назначение:** озвучивание реплик агента.

**MVP:** локальный TTS (Piper / Kokoro / MLX-TTS). Получает только **validated** text от Contract Enforcer.

### 6. Contract Enforcer (ABC-lite)

**Назначение:** runtime проверка текста агента **перед TTS** — hard/soft rules per mode.

**См.:** [13-behavioral-contracts.md](13-behavioral-contracts.md)

**MVP:** EN-only, forbidden coaching patterns (Mode 1), max sentences, question-or-ack; recovery = 1 regenerate + template fallback.

### 7. Interview / Review Orchestrator

**Назначение:** state machine интервью; не «свободный чат», а сценарий с фазами и таймингом.

**См.:** [04-interview-orchestrator.md](04-interview-orchestrator.md), [11-two-modes-review-dialogue.md](11-two-modes-review-dialogue.md)

### 8. Knowledge Loader

**Назначение:** загрузка и инъекция в prompt: CV, case study, target roles, rubric, типичные слабые места.

**MVP:** статические markdown-файлы, скопированные или symlinked в `data/knowledge/`.

### 9. Session Store

**Назначение:** персистентность **interview** и **review** сессий.

**См.:** [12-session-storage.md](12-session-storage.md)

**MVP schema:**

```
interview_sessions  — Mode 1 transcript, debrief_json, review_session_id
review_sessions     — Mode 2 transcript, source_interview_id
vocabulary_bank     — см. doc 10
```

### 10. Summary Generator

**Назначение:** после Mode 2 — LLM pass по interview + review transcripts → rubric JSON + vocabulary extract.

**MVP:** синхронный после review End; результат в UI и SQLite; vocabulary → Vocabulary Bank.

### 11. Vocabulary Bank

**Назначение:** persistent словарь полезных слов/фраз для interview; авто-пополнение после debrief.

**MVP:** SQLite `vocabulary_bank`; LLM extractor (sub-step debrief); UI tab с EN + **RU translation** + example.

## Основной поток (happy path)

```
1. User → Start Mock Interview (Mode 1)
2. Interview loop: LLM → Contract Enforcer → TTS → save interview_sessions
3. Prompt: Start Review Together?
4. Review orchestrator loop (uses interview transcript) → save review_sessions
5. Summary Generator → debrief_json + Vocabulary Bank
6. Client: summary card + both transcripts in History
```

## Границы MVP

| In MVP | Post-MVP |
|--------|----------|
| Single process backend | Separate STT/TTS workers |
| One interview mode | Mode picker UI |
| Static knowledge files | RAG + chunking |
| Batch STT per turn | Streaming STT |
| Simple SQLite | Analytics dashboard |
| Localhost only | Optional cloud LLM fallback |

## Repo layout (planned)

**Инженерные ограничения:** каждый файл в `backend/app/`, `frontend/src/` — **≤ 500 LOC**; SOLID, DRY, тесты — см. [18-engineering-standards.md](18-engineering-standards.md).

```
voice-interview-coach/
├── README.md
├── docs/                    # design documents (this folder)
├── backend/
│   ├── app/
│   │   ├── main.py          # wiring only
│   │   ├── api/             # routes + ws (thin)
│   │   ├── schemas/
│   │   ├── common/
│   │   ├── voice/           # STT/TTS/VAD behind protocols
│   │   ├── contracts/       # ABC-lite enforcer
│   │   ├── orchestrator/    # interview/ + review/ subpackages
│   │   ├── llm/
│   │   ├── storage/
│   │   ├── summary/
│   │   └── knowledge/
│   ├── tests/               # unit + integration (mirrors app/)
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   └── tests/               # vitest
├── data/
│   ├── contracts/           # interview.contract.yaml, review.contract.yaml
│   ├── knowledge/
│   ├── prompts/
│   └── sessions/
└── scripts/
    ├── check_module_size.py
    ├── spike/               # Phase 0 only
    └── ...
```

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial architecture |
| 2026-06-26 | Contract Enforcer (ABC-lite) component added |
| 2026-06-26 | Repo layout: module size limit, tests/, check_module_size |
