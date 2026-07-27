#!/usr/bin/env bash
# Durable product smoke oracles (Delivery §6.1). Fails on the first red check.
# Живые AI не трогаются: ollama/whisper/piper — ручной прогон, active/eval-smoke.md.
#
# Два свойства, без которых оракул бесполезен в CI:
#   * КАЖДЫЙ чек под таймаутом (README обещает их по ID — здесь они реально
#     применяются). Зависший чек = красный за N секунд, а не молчаливый 6-часовой
#     прогон, жгущий CI-минуты;
#   * вывод упавшего чека ПЕЧАТАЕТСЯ. Раньше он глушился в /dev/null, и понять,
#     на чём именно встало, было нельзя — что и случилось на первом прогоне в CI.
set -uo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

# Портируемый таймаут: на macOS нет ни `timeout`, ни `gtimeout` (это coreutils).
# Запускаем в фоне, сторожим отдельным процессом, при просрочке бьём группу.
with_timeout() {
  local secs=$1; shift
  "$@" >"$LOG" 2>&1 &
  local pid=$!
  ( sleep "$secs"; kill -9 "$pid" 2>/dev/null ) >/dev/null 2>&1 &
  local watcher=$!
  wait "$pid" 2>/dev/null
  local rc=$?
  kill "$watcher" 2>/dev/null
  wait "$watcher" 2>/dev/null
  # 137 = SIGKILL от сторожа: отличаем «упал» от «завис».
  [ "$rc" = "137" ] && return 124
  return "$rc"
}

run_check() {          # run_check <id> <timeout-sec> <описание> <cmd...>
  local id=$1 secs=$2 desc=$3; shift 3
  printf '==> %s (%ss) %s\n' "$id" "$secs" "$desc"
  local rc=0
  with_timeout "$secs" "$@" || rc=$?
  if [ "$rc" = "0" ]; then
    printf '  ok  — %s\n' "$id"
    return 0
  fi
  if [ "$rc" = "124" ]; then
    printf '  \033[31mTIMEOUT\033[0m — %s не уложился в %ss\n' "$id" "$secs" >&2
  else
    printf '  \033[31mFAIL\033[0m — %s (exit %s)\n' "$id" "$rc" >&2
  fi
  printf '  --- вывод %s (последние 40 строк) ---\n' "$id" >&2
  tail -40 "$LOG" >&2
  exit 1
}

run_check S1 60  "module size (<= 500 LOC)" \
  python3 scripts/check_module_size.py

run_check S2 300 "backend suite + coverage gate" \
  bash -c 'cd backend && uv run pytest -q'

run_check S3 300 "frontend build (tsc -b + vite build)" \
  bash -c 'cd frontend && npm run build'

run_check S4 180 "frontend tests" \
  bash -c 'cd frontend && npm test'

# S5 ловит поломки окружения/путей, которые тесты не видят (см. README: переезд репо).
run_check S5 120 "app import + config paths resolve" \
  bash -c 'cd backend && uv run python -c "
import sys
from pathlib import Path
from app.config import get_settings
from app.main import app  # noqa: F401
s = get_settings()
# Только то, что коммитится: data/models/ в .gitignore, в CI его нет.
required = (\"prompts_dir\", \"knowledge_dir\", \"contracts_dir\", \"questions_dir\")
missing = [n for n in required if not Path(getattr(s, n)).is_dir()]
if missing:
    sys.exit(\"missing config dirs: \" + \", \".join(missing))
"'

run_check S6 120 "contracts + prompts parse" \
  bash -c 'cd backend && uv run python -c "
import sys
from pathlib import Path
import yaml
from app.config import get_settings
s = get_settings()
bad = []
for p in sorted(Path(s.contracts_dir).rglob(\"*.y*ml\")):
    try:
        yaml.safe_load(p.read_text(encoding=\"utf-8\"))
    except Exception as exc:
        bad.append(f\"{p.name}: {type(exc).__name__}\")
if bad:
    sys.exit(\"unparsable contracts: \" + \"; \".join(bad))
if not any(Path(s.prompts_dir).iterdir()):
    sys.exit(\"prompts dir is empty\")
"'

echo "==> S7 (15s) health endpoint — пропускается, если сервер не поднят"
if curl -sf --max-time 5 http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "  ok  — S7"
else
  echo "  skip — no server on :8000 (start it to exercise S7)"
fi

echo "smoke: all checks passed"
