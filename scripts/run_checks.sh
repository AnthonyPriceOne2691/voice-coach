#!/usr/bin/env bash
# Local quality gate — mirrors Phase 1+ engineering exit criteria.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Module size (<= 500 LOC)"
python3 scripts/check_module_size.py

echo "==> Backend: ruff"
cd backend
uv run ruff check app tests
uv run ruff format --check app tests

echo "==> Backend: mypy"
uv run mypy app

echo "==> Backend: pytest + coverage"
uv run pytest

echo "==> All checks passed"
