#!/usr/bin/env bash
# Durable product smoke oracles (Delivery §6.1). Fails on the first red check.
# Живые AI не трогаются: ollama/whisper/piper — ручной прогон, active/eval-smoke.md.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

fail() { echo "SMOKE FAIL: $1" >&2; exit 1; }
ok()   { echo "  ok  — $1"; }

echo "==> S1 module size (<= 500 LOC)"
python3 scripts/check_module_size.py >/dev/null || fail "S1 module size"
ok "S1"

echo "==> S2 backend suite + coverage gate"
(cd backend && uv run pytest -q >/dev/null) || fail "S2 pytest"
ok "S2"

echo "==> S3 frontend build (tsc -b + vite build)"
(cd frontend && npm run build >/dev/null 2>&1) || fail "S3 frontend build"
ok "S3"

echo "==> S4 frontend tests"
(cd frontend && npm test >/dev/null 2>&1) || fail "S4 vitest"
ok "S4"

echo "==> S5 app import + config paths resolve"
# Ловит поломки окружения/путей, которые тесты не видят (см. README: переезд репо).
(cd backend && uv run python -c "
import sys
from pathlib import Path
from app.config import get_settings
from app.main import app  # noqa: F401
s = get_settings()
# Только то, что коммитится: data/models/ в .gitignore, в CI его нет.
required = ('prompts_dir', 'knowledge_dir', 'contracts_dir', 'questions_dir')
missing = [n for n in required if not Path(getattr(s, n)).is_dir()]
if missing:
    sys.exit('missing config dirs: ' + ', '.join(missing))
") || fail "S5 app import / config paths"
ok "S5"

echo "==> S6 contracts + prompts parse"
(cd backend && uv run python -c "
import sys
from pathlib import Path
import yaml
from app.config import get_settings
s = get_settings()
bad = []
for p in sorted(Path(s.contracts_dir).rglob('*.y*ml')):
    try:
        yaml.safe_load(p.read_text(encoding='utf-8'))
    except Exception as exc:
        bad.append(f'{p.name}: {type(exc).__name__}')
if bad:
    sys.exit('unparsable contracts: ' + '; '.join(bad))
if not any(Path(s.prompts_dir).iterdir()):
    sys.exit('prompts dir is empty')
") || fail "S6 contracts/prompts"
ok "S6"

echo "==> S7 health endpoint (skipped if server is down)"
if curl -sf --max-time 5 http://127.0.0.1:8000/health >/dev/null 2>&1; then
  ok "S7"
else
  echo "  skip — no server on :8000 (start it to exercise S7)"
fi

echo "smoke: all checks passed"
