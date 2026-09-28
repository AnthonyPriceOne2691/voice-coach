#!/usr/bin/env bash
# One-command dev environment: ollama + backend (auto-reload) + frontend (HMR).
# Usage: ./scripts/dev.sh    Stop: Ctrl+C (kills everything it started).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"

if [ ! -x "$ROOT/backend/.venv/bin/uvicorn" ]; then
  echo "==> backend venv missing — running uv sync..."
  (cd "$ROOT/backend" && uv sync --all-extras)
fi
if [ ! -x "$ROOT/frontend/node_modules/.bin/vite" ]; then
  echo "==> frontend deps missing — running npm install..."
  (cd "$ROOT/frontend" && npm install)
fi

# Ollama: reuse a running daemon, otherwise start our own
if curl -s --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "==> ollama already running"
else
  echo "==> starting ollama serve (log: /tmp/vic-ollama.log)"
  nohup ollama serve >/tmp/vic-ollama.log 2>&1 &
  for _ in $(seq 1 20); do
    curl -s --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null && break
    sleep 0.5
  done
fi

cleanup() {
  echo ""
  echo "==> shutting down..."
  kill $(jobs -p) 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> backend  : http://127.0.0.1:${BACKEND_PORT}  (auto-reload on app/ changes)"
(cd "$ROOT/backend" && exec .venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT") &

echo "==> frontend : http://localhost:5273  (HMR)"
(cd "$ROOT/frontend" && exec ./node_modules/.bin/vite) &

echo ""
echo "    Open http://localhost:5273 and press Start interview. Ctrl+C stops everything."
echo ""
wait
