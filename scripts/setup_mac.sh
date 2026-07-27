#!/usr/bin/env bash
# One-time Mac setup for Voice Interview Coach (Phase 0+)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Homebrew dependencies"
brew install ollama ffmpeg

# whisper.cpp CLI (Metal on Apple Silicon)
if ! command -v whisper-cli &>/dev/null; then
  echo "==> Installing whisper-cpp (provides whisper-cli on recent brew)"
  brew install whisper-cpp
fi

if ! command -v uv &>/dev/null; then
  echo "==> Installing uv (Python package manager)"
  brew install uv
fi

echo "==> Ollama models (skip if already pulled)"
ollama pull qwen2.5:14b-instruct
# deepseek-r1:14b — user may already have it
ollama pull deepseek-r1:14b || true

echo "==> Spike Python deps"
# Throwaway venv for spike scripts — kept outside the repo, separate from backend/.venv
SPIKE_VENV="${TMPDIR:-/tmp}/vic-spike-venv"
python3 -m venv "$SPIKE_VENV"
source "$SPIKE_VENV/bin/activate"
pip install -q -r "$ROOT/scripts/spike/requirements.txt"

echo "==> Download voice models (whisper + piper)"
bash "$ROOT/scripts/download_models.sh"

echo ""
echo "Done. Next:"
echo "  1. Terminal A: ollama serve"
echo "  2. Terminal B: source ${TMPDIR:-/tmp}/vic-spike-venv/bin/activate"
echo "     python scripts/spike/benchmark_turn.py --all"
