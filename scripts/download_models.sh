#!/usr/bin/env bash
# Download Whisper + Piper assets into data/models/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODELS="$ROOT/data/models"
WHISPER_DIR="$MODELS/whisper"
PIPER_DIR="$MODELS/piper"

mkdir -p "$WHISPER_DIR" "$PIPER_DIR"

WHISPER_MODEL="$WHISPER_DIR/ggml-small.en.bin"
PIPER_VOICE="$PIPER_DIR/en_US-lessac-medium.onnx"
PIPER_JSON="$PIPER_DIR/en_US-lessac-medium.onnx.json"

download() {
  local url="$1"
  local dest="$2"
  if [[ -f "$dest" ]]; then
    echo "  skip (exists): $(basename "$dest")"
    return
  fi
  echo "  download: $(basename "$dest")"
  curl -L --fail --progress-bar -o "$dest" "$url"
}

echo "==> Whisper small.en (ggml)"
download \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin" \
  "$WHISPER_MODEL"

echo "==> Piper voice (lessac medium)"
download \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" \
  "$PIPER_VOICE"
download \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" \
  "$PIPER_JSON"

echo "==> Piper voice (hfc_male medium — Henry's default voice)"
download \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx" \
  "$PIPER_DIR/en_US-hfc_male-medium.onnx"
download \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx.json" \
  "$PIPER_DIR/en_US-hfc_male-medium.onnx.json"

echo "==> Piper binary (macOS arm64)"
PIPER_RUNTIME="$PIPER_DIR/piper"
PIPER_BIN="$PIPER_RUNTIME/piper"
if [[ ! -x "$PIPER_BIN" ]]; then
  ARCH="$(uname -m)"
  if [[ "$ARCH" == "arm64" ]]; then
    download \
      "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_macos_aarch64.tar.gz" \
      "$PIPER_DIR/piper_macos_aarch64.tar.gz"
    tar -xzf "$PIPER_DIR/piper_macos_aarch64.tar.gz" -C "$PIPER_DIR"
    chmod +x "$PIPER_BIN" "$PIPER_RUNTIME/piper_phonemize" 2>/dev/null || true
  else
    echo "  WARN: Piper auto-download only for arm64. Install piper manually."
  fi
fi
if [[ ! -x "$PIPER_BIN" ]]; then
  echo "  ERROR: Piper binary not found at $PIPER_BIN"
  exit 1
fi

echo "==> Piper runtime"
echo "  Voice: $PIPER_VOICE"
echo "  CLI:   $PIPER_BIN (optional — macOS tarball lacks dylibs)"
echo "  Recommended TTS for benchmark + app: pip package piper-tts"
