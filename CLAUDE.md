# CLAUDE.md — Voice Interview Coach

Голосовой AI-агент для mock technical interviews на английском. Локальный инструмент для одного пользователя (MacBook Air M5, 32 GB): whisper.cpp (STT) → Ollama qwen2.5:14b-instruct (LLM) → Piper (TTS), FastAPI + React. Всё офлайн, privacy-first.

## Окружение

Репозиторий живёт в `/Users/anthony/Documents/voice-interview-coach`. Обычные
инструменты работают штатно: `uv run`, npm-скрипты, venv внутри репо, Vite fs-checks.

> Историческая заметка: до 2026-07-27 репо лежал в пути с `:` (`Other:Another`), что
> ломало `uv run`, npm-скрипты и venv. После переезда ограничение снято — прямые
> вызовы `backend/.venv/bin/<tool>` больше не обязательны. При повторном переносе
> репозитория пересоздай venv (`cd backend && uv sync --all-extras`): шебанги
> console-скриптов содержат абсолютный путь и переезд их ломает.

## Команды

```bash
./scripts/dev.sh                     # всё разом: ollama + backend --reload + vite HMR; Ctrl+C гасит
./scripts/run_checks.sh              # локальный quality gate (module size + ruff + mypy + pytest)

# Quality gates вручную:
python3 scripts/check_module_size.py                       # ≤ 500 LOC на файл
cd backend && uv run ruff check app tests && uv run ruff format --check app tests
cd backend && uv run mypy app                              # strict
cd backend && uv run pytest                                # coverage gate 85% (сейчас ~93%)
cd frontend && npm run build && npm test
```

## Структура

- `docs/00–20` — **канонический дизайн**; читать перед изменениями. Канон-источники: doc 12 (схема хранения), doc 16 (LLM-параметры), doc 13 (behavioral contracts), doc 20 (token budgets)
- `backend/app/` — FastAPI: `voice/` (STT/TTS/pipeline), `llm/`, `api/ws_voice.py` (WS по doc 15), `container.py` (DI)
- `frontend/src/` — React: `hooks/useVoiceSession.ts` (WS+mic+VAD), `lib/vad.ts`, `lib/audioQueue.ts`
- `data/prompts/` — промпты (перечитываются на каждой сессии, рестарт не нужен); `data/contracts/` — ABC-lite YAML; `data/knowledge/profile_condensed.md` — профиль кандидата в системный промпт; `data/sessions/` — транскрипты (gitignored, приватные)

## Ключевые архитектурные решения (не переизобретать)

- **Sentence-streaming обязателен**: TTS по предложениям, буферизация полного ответа проваливает latency-гейт (замерено: 4.8 s vs 3.0 s). Enforcer контрактов — тоже per-sentence (doc 13)
- **D-8 закрыт**: ВСЁ голосовое — qwen2.5:14b-instruct; deepseek-r1:14b ТОЛЬКО offline summary (R1 = 31–52 s/ход, замерено). Не предлагать R1 в voice-цикл
- **Оркестратор владеет структурой, LLM — только формулировками** (I1-H6); follow-up решается детерминированной политикой (doc 04)
- Порт фронта **5273** (5173 занят линкбилдинг-проектом пользователя)
- Микрофон открывается только после окончания воспроизведения агента (echo-защита); VAD float-домен, −50 dBFS
- Транскрипт — единственный невосполнимый артефакт: flush при каждом turn, любые падения хода — recoverable

## Инженерные правила (doc 18, enforced в CI)

≤ 500 LOC на файл · SOLID, всё AI за Protocols (`SpeechToText`, `TextToSpeech`, `LlmClient`) · mypy strict · тесты в том же PR, реальные AI всегда мокаются · промпты/контракты в `data/`, не в коде.

## Состояние (2026-07-05)

- **Phase 0** ✅ · **Phase 1** ✅ · **Phase 2 🟡 code complete (2026-07-05)** — оркестраторы, sentence-gated Contract Enforcer, Mode 2, SQLite, History/Words UI, R1-summary + Vocabulary Bank; live e2e-smoke пройден (interview→review→summary→bank). Остался ручной UI-прогон
- Агента зовут **Генри**: голос `en_US-hfc_male-medium`, темп `PIPER_LENGTH_SCALE=1.15`
- Backend: 91 тест / 93.5% coverage (гейт 85), contracts 100%, mypy strict; frontend: 14 тестов
- Наблюдать в использовании: качество R1-summary (замечен артефакт в translation_ru), markdown-списки в wrap-up review
- GitHub: приватный `AnthonyPriceOne2691/voice-coach`, CI зелёный; gh CLI авторизован
- Коммиты: identity задана локально (noreply-алиас аккаунта); пушить после каждого логического блока
