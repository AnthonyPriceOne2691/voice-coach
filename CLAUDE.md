# CLAUDE.md — Voice Interview Coach

Голосовой AI-агент для mock technical interviews на английском. Локальный инструмент для одного пользователя (MacBook Air M5, 32 GB): whisper.cpp (STT) → Ollama qwen2.5:14b-instruct (LLM) → Piper (TTS), FastAPI + React. Всё офлайн, privacy-first.

## Canon stack / Agent Delivery Harness

- **Start here:** `docs/canon/AGENT_STACK.md` (order: Delivery → CQG → OKF).
  Каноны вендорятся в `docs/canon/`; рабочая копия человека — `Prepare/` (не коммитится).
- Process canon: `docs/canon/AGENT_DELIVERY_HARNESS.md`.
- Active delivery: `delivery/active/STATUS.md` — **read before coding**.
- **Order:** follow delivery phases. Do not oneshot large work.
- **Done:** only when verify oracles pass **and CI is green**; never declare done on red.
- Prefer git worktree for class M/L (Delivery §5.1).
- Smoke/evals: `delivery/evals/smoke/` + `active/eval-smoke.md` (Delivery §6).
- Metrics on handoff: `python3 scripts/delivery_metrics.py --base origin/main --write`.
- Merge only via `bash scripts/merge_guard.sh <branch>` — серверной защиты ветки нет (§8.5).
- Hooks: `scripts/hooks/` (Delivery §10).
- Do **not** duplicate code-quality rules here — they live in `docs/canon/CODE_QUALITY_GATES.md`
  и в `.pre-commit-config.yaml`.
- Do **not** invent domain canon — use `knowledge/` (OKF) и `docs/00–20`.

## OKF knowledge bundle

- Bundle root: `knowledge/` (Open Knowledge Format v0.2).
- **Before answering canonical questions** (инварианты voice-цикла, выбор модели,
  политики данных): читай `knowledge/index.md` и иди по ссылкам. Не выдумывай по памяти.
- **When changing invariants** in code: обнови соответствующий concept в том же
  изменении; освежи родительский `index.md` и `log.md`. Это **enforced**, а не пожелание:
  `scripts/okf_sync_gate.py` роняет CI, если путь из `implementation:` изменился, а
  concept — нет. Осознанный дрейф (чистый рефакторинг): `ALLOW_CANON_DRIFT=1`, видимо в PR.
- Новое устойчивое знание — concept'ом с frontmatter `type`, не новым orphan-файлом.
- Полный дизайн остаётся в `docs/00–20`; карта соответствия —
  `knowledge/references/design-docs.md`.
- Upstream spec (сверять при deploy/migrate):
  https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

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

## Состояние (2026-07-28)

- **Phase 0** ✅ · **Phase 1** ✅ · **Phase 2 🟡 code complete (2026-07-05), НЕ принята** — оркестраторы, sentence-gated Contract Enforcer, Mode 2, SQLite, History/Words UI, R1-summary + Vocabulary Bank; live e2e-smoke пройден (interview→review→summary→bank). Остались ручной UI-прогон и блокер ниже
- **Канон-стек обновлён (2026-08-11)**: `delivery@1.68 · cqg@2.02 · okf@1.15` — ветка `contour/2.01`, ждёт push/PR человека. Вход — `docs/canon/AGENT_STACK.md`; активная поставка — `delivery/active/STATUS.md`; приёмка и остатки — `delivery/STACK-ACCEPTANCE.md`
- **Обновление контура ≠ развёртывание**: порядок — CQG §5.5. Природа расхождения определяется сверкой со снимком `docs/canon/`, адаптации объявлены в `scripts/lint/adapted.json`; рядом `canaries.json` и `not-applicable.json`. Скрипты контура — **комплекты**: `contour_doctor.py` из 9 файлов, `delivery_check.py` из 11; без своей части вход не стартует
- Агента зовут **Генри**: голос `en_US-hfc_male-medium`, темп `PIPER_LENGTH_SCALE=1.15`
- Backend: 91 тест / 93.8% coverage (гейт 85), contracts 100%, mypy strict; frontend: 14 тестов, eslint 0 errors, warning-ратчет держит снимок
- **Гейты фронта ожили на 2.01**: у complexity и jscpd появились TS-половины, у роли слоёв — `dependency-cruiser` (конфиг в корне + `tsconfig.depcruise.json`, оба знают, что фронт в подкаталоге). До 2.01 фронт этими ролями не проверялся вовсе — зелёное значило «никто не смотрел»
- **⚠ CI КРАСНЫЙ, и это правда, а не поломка стека.** `test_ws_voice.py` виснет на ubuntu-runner: WS-сессия не завершается, если клиент отключился без `end_session`. Падает через раз (`test_stt_empty_recoverable` / `test_decode_failure_is_recoverable`). Дефект с 2026-07-05 — тогда прогоны main висели по 6 ч и отменялись, поэтому строка «CI зелёный» здесь была неверной. Диагноз и лид — `delivery/active/spec.md`, первый пункт in-scope. Джобы `quality/gates` и `main-guard` зелёные
- Наблюдать в использовании: качество R1-summary (замечен артефакт в translation_ru), markdown-списки в wrap-up review
- GitHub: приватный `AnthonyPriceOne2691/voice-coach`; **серверной защиты ветки нет** (Free-тариф, 403) → мерж только через `bash scripts/merge_guard.sh <branch>`; gh CLI авторизован
- Коммиты: identity задана локально (noreply-алиас аккаунта); пушить после каждого логического блока
