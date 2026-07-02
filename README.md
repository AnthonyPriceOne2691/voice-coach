# Voice Interview Coach

Голосовой AI-агент для mock technical interviews на английском.

**Статус:** Phase 0 ✅ · **Phase 1 ✅** (live-проверено) · Phase 2 next · Интервьюера зовут **Генри**  
**Автор:** Anton Aspidov  
**Планирование:** см. [`docs/`](docs/)

## Запуск (Phase 1 voice loop) — одна команда

```bash
./scripts/dev.sh        # → http://localhost:5273 · Ctrl+C гасит всё
```

Скрипт сам: поднимет Ollama (если не запущен), поставит зависимости (если нет), запустит backend c **auto-reload** (правки в `backend/app/` применяются сами) и frontend с **HMR** (правки в `frontend/src/` применяются сами, без перезагрузки страницы). Промпты в `data/prompts/` перечитываются на каждой новой сессии — тоже без рестарта.

<details><summary>Запуск по частям (если нужно)</summary>

```bash
# T1: ollama serve
# T2: cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
# T3: cd frontend && ./node_modules/.bin/vite     # http://localhost:5273
```
</details>

> ⚠️ Из-за `:` в пути (`Other:Another`) **`uv run` и npm-скрипты не работают** — вызывай бинарники напрямую: `backend/.venv/bin/<tool>`, `frontend/node_modules/.bin/<tool>`. Лечится переносом репозитория в путь без `:`.

## Phase 0 results (2026-06-26)

| Metric | Warm latency |
|--------|--------------|
| Full voice turn | **~3.0 s** (p95 ~3.1 s) |
| STT whisper.cpp | ~0.7 s |
| LLM Qwen 14B | ~1.8 s |
| TTS Piper | ~0.5 s |

✅ Gate < 5 s пройден (короткий промпт, 2 warm runs — см. Limitations в [docs/19](docs/19-phase0-benchmark-results.md)).  
⚠️ Открыто **D-8**: модель для Mode 2 voice review — R1 показал ~18–21 s/ход ([docs/14](docs/14-llm-model-split.md)). Re-benchmark на продовом промпте — gate Phase 1 ([docs/20](docs/20-context-token-budget.md)).

## Цель

Симуляция live interview + **Review Together** с рекрутером-другом. Interview и review dialogues хранятся локально. Debrief summary + Vocabulary Bank.

## Ограничения v1

- **Локально** на MacBook Air 13 M5 (32 GB / 512 GB)
- **Voice in + voice out** — пользователь и агент говорят голосом
- Язык сессии: **English only**

## Документация

| Документ | Содержание |
|----------|------------|
| [00-project-overview](docs/00-project-overview.md) | Контекст, цели, success criteria |
| [01-requirements](docs/01-requirements.md) | Функциональные и нефункциональные требования |
| [02-architecture](docs/02-architecture.md) | Компоненты, потоки данных, границы MVP |
| [03-voice-pipeline](docs/03-voice-pipeline.md) | STT / LLM / TTS loop, latency, локальные модели |
| [04-interview-orchestrator](docs/04-interview-orchestrator.md) | State machine, personas, question bank |
| [05-knowledge-base](docs/05-knowledge-base.md) | Профиль, CV, case study, debrief |
| [06-mvp-phases](docs/06-mvp-phases.md) | Фазы, scope, критерии готовности |
| [07-tech-stack](docs/07-tech-stack.md) | Стек под Apple Silicon, зависимости |
| [08-post-session-debrief](docs/08-post-session-debrief.md) | Обратная связь после каждой сессии |
| [09-agent-persona-and-tone](docs/09-agent-persona-and-tone.md) | Роль и тон: старший товарищ |
| [10-vocabulary-bank](docs/10-vocabulary-bank.md) | Вкладка полезных слов + перевод |
| [11-two-modes-review-dialogue](docs/11-two-modes-review-dialogue.md) | Два режима: интервью + разбор |
| [12-session-storage](docs/12-session-storage.md) | Хранение диалогов |
| [13-behavioral-contracts](docs/13-behavioral-contracts.md) | ABC-lite: контроль поведения агента |
| [14-llm-model-split](docs/14-llm-model-split.md) | Qwen + R1 model split |
| [15-api-websocket-spec](docs/15-api-websocket-spec.md) | REST + WebSocket API |
| [16-prompts-library](docs/16-prompts-library.md) | Prompt library |
| [17-ui-screens](docs/17-ui-screens.md) | UI screens & UX |
| [18-engineering-standards](docs/18-engineering-standards.md) | SOLID, DRY, tests, 500 LOC |
| [19-phase0-benchmark-results](docs/19-phase0-benchmark-results.md) | **Phase 0 latency tests** + limitations |
| [20-context-token-budget](docs/20-context-token-budget.md) | Token/context budget, R1 thinking rule, Phase 1 gate |

## Phase 0 benchmark (reproduce)

```bash
ollama serve   # terminal 1
bash scripts/download_models.sh
python3 -m venv /tmp/vic-spike-venv && source /tmp/vic-spike-venv/bin/activate
pip install -r scripts/spike/requirements.txt
python scripts/spike/benchmark_turn.py --stage full --runs 3
```

> **Note:** Python venv inside this repo fails if the parent folder name contains `:` (`Other:Another`). Use `/tmp/vic-spike-venv` or `brew install uv`.

## Источники контекста (workspace)

- `../VOICE_INTERVIEW_COACH_AGENT_BRIEF.md` — исходный brief
- `../ANTON_ASPIDOV_CV_EN.md`
- `../PORTFOLIO_LINKBUILDER_CASE.md`
- `../FOREIGN_MARKET_OUTREACH_PLAN.md`
