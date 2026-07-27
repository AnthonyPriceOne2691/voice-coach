# Durable smoke oracles

Repo-level product checks. Гоняются в verify и в CI (`bash delivery/evals/smoke/run.sh`).

Здесь **только то, что работает без живых AI**: `data/models/` gitignored, ollama в CI
нет. Живой прогон (whisper → qwen → piper) — ручной, он в `delivery/active/eval-smoke.md`.

| ID | Command | Expected | Timeout |
|---|---|---|---|
| S1 | `python3 scripts/check_module_size.py` | exit 0 — все файлы ≤ 500 LOC | 60s |
| S2 | `cd backend && uv run pytest -q` | exit 0 — сьют зелёный, coverage ≥ 85 | 300s |
| S3 | `cd frontend && npm run build` | exit 0 — tsc -b + vite build | 300s |
| S4 | `cd frontend && npm test` | exit 0 — vitest | 180s |
| S5 | app import + резолв путей конфига | `app.main:app` импортируется; `prompts/knowledge/contracts/questions` существуют | 120s |
| S6 | контракты и промпты парсятся | каждый YAML в `data/contracts/` — валидный; `data/prompts/` непустой | 120s |
| S7 | health endpoint | HTTP 200 на `/health` (пропускается, если сервер не поднят) | 15s |

**Таймауты применяются, а не только задекларированы.** Первая версия скрипта их не
enforce'ила и глушила вывод в `/dev/null` — в CI шаг завис молча и был неотличим от
долгой сборки. Теперь каждый чек идёт через портируемый `with_timeout` (на macOS нет
`timeout` из coreutils), просрочка = `TIMEOUT` за N секунд, и вывод упавшего чека
печатается последними 40 строками.

**S5 не декоративен.** Переезд репозитория 2026-07-27 сломал ровно это: шебанги
console-скриптов venv указывали на старый путь, и весь Python-тулинг умирал с
`bad interpreter`. Оракул ловит этот класс поломки (пути/окружение), который тесты
не видят — они уже импортированы к моменту прогона.

`run.sh` гоняет S1–S7 по порядку и падает на первом красном.
