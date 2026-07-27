#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
# Интерпретатор резолвим, а не хардкодим: на macOS бинаря `python` нет вовсе.
PY=$(command -v python3 || command -v python)
if [[ -f scripts/delivery_check.py ]]; then
  "$PY" scripts/delivery_check.py || {
    echo "delivery_check failed — cannot declare done" >&2
    exit 1
  }
fi
if [[ -x delivery/evals/smoke/run.sh ]]; then
  bash delivery/evals/smoke/run.sh || {
    echo "smoke evals failed — cannot declare done" >&2
    exit 1
  }
fi
# CQG развёрнут — гейты формы кода обязательны перед объявлением done.
if [[ -f .pre-commit-config.yaml ]] && command -v pre-commit >/dev/null 2>&1; then
  pre-commit run --all-files || {
    echo "pre-commit failed — cannot declare done" >&2
    exit 1
  }
elif [[ -x backend/.venv/bin/pre-commit ]]; then
  backend/.venv/bin/pre-commit run --all-files || {
    echo "pre-commit failed — cannot declare done" >&2
    exit 1
  }
fi
exit 0
