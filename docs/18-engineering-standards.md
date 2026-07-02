# 18 — Engineering Standards (SOLID, DRY, tests, module size)

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## Принцип

Код пишется **только после Phase 0**, но **с первого коммита** — по этим правилам.  
Нарушение — не «потом поправим», а блокер merge / exit criteria фазы.

**Связанные docs:** [02-architecture.md](02-architecture.md), [06-mvp-phases.md](06-mvp-phases.md), [01-requirements.md](01-requirements.md) (NFR-6).

---

## 1. Размер модулей — hard limit 500 LOC

### Правило

| Метрика | Лимит |
|---------|-------|
| Один **исходный файл** (`.py`, `.ts`, `.tsx`) | **≤ 500 строк** (без пустых строк и комментариев — желательно; с ними — строгий потолок) |
| Один **пакет/папка** (например `orchestrator/`) | каждый файл ≤ 500; пакет дробится по ответственности |

**Исключения (только с явным комментарием в PR / changelog):**
- Автогенерированный код
- Большие fixture-файлы в `tests/fixtures/` (не production code)
- Временный spike в `scripts/spike/` (не входит в `backend/app/`)

### Когда дробить (до 500)

- Файл > **350 LOC** — планировать split в том же PR
- Смешаны **2+ ответственности** (HTTP + бизнес-логика + SQL в одном файле) — split немедленно
- Класс/модуль с **> 5 публичных методов** без единой темы — выделить подмодуль

### Целевая гранулярность (backend)

```
backend/app/
├── main.py                 # wiring only, < 150 LOC
├── api/
│   ├── routes_health.py
│   ├── routes_sessions.py
│   └── ws_voice.py         # WebSocket handler — thin
├── voice/
│   ├── gateway.py
│   ├── stt_whisper.py
│   ├── tts_piper.py
│   └── vad.py
├── contracts/
│   ├── loader.py           # YAML → Contract
│   ├── enforcer.py         # validate + recover
│   └── rules/              # one rule ≈ one small module
├── orchestrator/
│   ├── interview/          # state machine per file
│   └── review/
├── llm/
│   ├── ollama_client.py
│   ├── model_swap.py
│   └── strip_thinking.py
├── summary/
├── storage/
│   ├── models.py           # SQLAlchemy ORM
│   └── repositories/       # one entity ≈ one repo file
└── knowledge/
```

### Целевая гранулярность (frontend)

```
frontend/src/
├── pages/                  # route-level, thin
├── components/             # presentational, small
├── hooks/                  # one concern per hook
├── api/                    # WebSocket + REST client
└── lib/                    # pure utils
```

### Enforcement

- [ ] `scripts/check_module_size.py` — fail CI если любой файл в `backend/app/` или `frontend/src/` > 500
- [ ] Pre-commit hook (опционально, Phase 2)
- [ ] Code review checklist в каждой фазе (см. [06-mvp-phases.md](06-mvp-phases.md))

---

## 2. SOLID — обязательно

Не академический чеклист, а **конкретные правила проекта**:

### S — Single Responsibility

| Компонент | Единственная ответственность |
|-----------|------------------------------|
| `VoiceGateway` | маршрутизация audio, не LLM |
| `ContractEnforcer` | валидация текста, не генерация |
| `InterviewOrchestrator` | state + transitions, не HTTP |
| `OllamaClient` | HTTP к Ollama, не prompt assembly |
| `SessionRepository` | CRUD SQLite, не бизнес-правила |

**Запрещено:** `main.py` с логикой orchestrator; enforcer, который сам вызывает LLM.

### O — Open/Closed

- Новый **режим интервью** / новый **contract rule** — через **новый файл** или YAML, без правки ядра enforcer
- STT/TTS/LLM — за **интерфейсом** (Protocol / ABC): `SpeechToText`, `TextToSpeech`, `LlmClient`
- Phase 3 (Kokoro, mlx-lm) — новая реализация интерфейса, не fork существующей

### L — Liskov Substitution

- Любая реализация `LlmClient` (Ollama, mock) — взаимозаменяема в тестах и prod wiring
- Mock STT/TTS не меняют контракт `transcribe(audio) -> str` / `synthesize(text) -> bytes`

### I — Interface Segregation

- Не один «God interface» `AiService`
- Раздельно: `Transcriber`, `Synthesizer`, `ChatCompleter`, `JsonExtractor`

### D — Dependency Inversion

- Orchestrator зависит от **абстракций** (`LlmClient`, `SessionStore`), не от `httpx` / SQLAlchemy напрямую
- **Dependency injection** через FastAPI `Depends` или явный `AppContainer` в `main.py`
- Конфиг (`Settings`) — один источник; не `os.getenv` разбросан по модулям

---

## 3. DRY — обязательно, с оговоркой

### Дублировать нельзя

- Парсинг WebSocket messages
- Загрузка contract YAML / prompts
- Формат transcript turn `{role, text, ts}`
- `strip_thinking()` для R1
- SQL-запросы к одной таблице в нескольких местах
- Одинаковые React-паттерны (session state indicator, error toast)

### Где DRY не гонять

- **Prompts** — отдельные `.txt` файлы, не строки в коде (исключение: 1-line fallbacks в enforcer)
- **Orchestrator states** Mode 1 vs Mode 2 — **разные** state machines, не один generic «на все случаи»
- Тесты — явные arrange/act/assert лучше, чем магический mega-helper

### Shared code

| Слой | Где жить общее |
|------|----------------|
| Backend pure logic | `backend/app/common/` |
| Backend schemas | `backend/app/schemas/` |
| Frontend types | `frontend/src/types/` |
| Константы контрактов | `data/contracts/*.yaml` |

---

## 4. Тесты — максимальное разумное покрытие

### Цели покрытия (gate)

| Область | Минимум line coverage | Когда обязателен |
|---------|----------------------|------------------|
| `contracts/` | **95%** | Phase 2+ |
| `orchestrator/` | **90%** | Phase 2+ |
| `summary/`, `storage/` | **90%** | Phase 2+ |
| `llm/` (клиент, strip_thinking) | **85%** | Phase 1+ |
| `voice/` (без subprocess e2e) | **80%** | Phase 1+ |
| `api/` routes | **80%** | Phase 1+ |
| Frontend `lib/`, `hooks/` | **85%** | Phase 2+ |
| Frontend components | **70%** | Phase 2+ (критичные flows) |

**Общий backend `app/` (без `main.py` wiring):** ≥ **85%** к концу Phase 2.

Инструменты:
- Backend: `pytest`, `pytest-cov`, `pytest-asyncio`, `httpx` TestClient
- Frontend: `vitest`, `@testing-library/react`
- CI: `pytest --cov-fail-under=85` (Phase 2), поэтапно с Phase 1

### Что тестировать обязательно

| Модуль | Тип теста | Примеры кейсов |
|--------|-----------|----------------|
| Contract Enforcer | unit | EN-only reject; coaching phrase; max 3 sentences; regenerate once; template fallback |
| Interview orchestrator | unit | INTRO→CORE→FOLLOW_UP→WRAP_UP; timer; question pool penalty |
| Review orchestrator | unit | grounded in transcript; USER_Q handling |
| Transcript segmentation | unit | split interview into Q&A pairs |
| `strip_thinking` | unit | R1 `<think>…</think>` blocks removed; **пустой результат после strip → hard fail** (doc 20) |
| Session repository | integration | save interview + review pair; vocabulary dedup |
| Summary parser | unit | valid JSON rubric; malformed LLM output recovery |
| WebSocket handler | integration | mock STT/LLM/TTS; full turn happy path |
| API health / sessions REST | integration | 200/404/422 |

### Что мокать

| Реальный сервис | В unit/integration |
|-----------------|-------------------|
| Ollama | ✅ always mock (fixture responses) |
| whisper.cpp subprocess | ✅ mock или recorded audio fixture |
| Piper | ✅ mock audio bytes |
| SQLite | in-memory для integration |
| Browser MediaRecorder | mock в vitest |

### E2E (manual + optional automated)

- Phase 1: **5 manual turns** (уже в exit criteria)
- Phase 2: checklist smoke (interview → review → summary → vocabulary)
- Авто E2E с реальным Ollama — **не в CI** (тяжело, flaky); отдельный `scripts/e2e_local.sh`

### TDD-порядок (рекомендуемый)

1. **Contract enforcer** — тесты до реализации правил
2. **Orchestrator transitions** — таблица state × event → next state
3. **Repositories** — CRUD
4. **Voice loop** — integration с mocks
5. UI — после стабильного API

---

## 5. Качество кода (дополнительно)

| Практика | Инструмент |
|----------|------------|
| Lint backend | `ruff` |
| Type check backend | `mypy` или `pyright` (strict на `app/`) |
| Lint frontend | `eslint` + `@typescript-eslint` |
| Format | `ruff format` / `prettier` |
| No secrets in repo | `.env.example` only |

---

## 6. Definition of Done (каждая фаза)

Помимо функциональных exit criteria из [06-mvp-phases.md](06-mvp-phases.md):

- [ ] Нет файлов > 500 LOC в `backend/app/`, `frontend/src/`
- [ ] Новый код — с тестами в том же PR
- [ ] Coverage не ниже порога фазы
- [ ] Нет дублирования логики, вынесенной в shared (review на DRY)
- [ ] Зависимости через интерфейсы / DI, не hard import конкретики в orchestrator
- [ ] `ruff` / `eslint` clean

---

## 7. Anti-patterns (явный запрет)

| Anti-pattern | Почему |
|--------------|--------|
| `utils.py` на 800 строк | нарушение SRP и лимита |
| LLM prompt inline в orchestrator | DRY, нет версионирования |
| Прямой `subprocess` в route handler | нарушение слоёв |
| Skip tests «потому что локальный AI» | mock обязателен |
| Copy-paste state machine Mode 1→2 без общих **типов** | дублирование transition helpers OK, не логики |
| Один `session.py` на storage + API + summary | split |

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial: 500 LOC, SOLID, DRY, coverage gates |
