#!/usr/bin/env bash
# Ручной оракул приёмки UI: настоящий браузер, настоящий голосовой тракт.
#
# Зачем существует: этот стенд нашёл ТРИ дефекта, которых не видел ни один
# зелёный гейт — вис при разрыве посреди хода, незакрытую сессию и мёртвые
# вкладки History/Words. Все три жили при зелёных сборке, тестах и линтерах.
#
# Почему НЕ в CI: нужны Chromium, ollama с моделью, whisper.cpp и голос Piper.
# На раннере он был бы вечно пропущенным, а пропущенный оракул хуже
# отсутствующего: он выглядит как проверка (урок L3 в archive/INDEX.md).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="${BROWSER_EVAL_OUT:-$HERE/out}"
APP="${APP_URL:-http://localhost:5273}"
API="${API_URL:-http://127.0.0.1:8000}"

usage() {
  cat <<'USAGE'
Использование: delivery/evals/browser/run.sh [сценарий]

Сценарии:
  mid-turn   (по умолчанию) начать интервью, ответить голосом, закрыть вкладку
             посередине хода. Проверяет: сессия завершена, ended_at заполнен.
  tabs       открыть History и Useful Words, снять экран. Проверяет: REST
             доходит через dev-прокси, состояние сессии читается с экрана.
  mic        выбор микрофонного входа на экране Settings. Проверяет: имена
             устройств, сохранение выбора, ВИДИМЫЙ отказ при пропаже входа
             (настоящее имя ошибки Chromium) и живую полоску уровня.
             Голосового стека не требует — только vite и backend.
  all        все по очереди.

Переменные: APP_URL (по умолчанию http://localhost:5273), API_URL, BROWSER_EVAL_OUT.

Чего стенд НЕ проверяет: качество речи и распознавания, поведение на других
браузерах, вёрстку на узких экранах. Микрофон имитируется подменой
getUserMedia — настоящий тракт начинается сразу после него.
USAGE
}

fail=0
need() {
  if ! eval "$2" >/dev/null 2>&1; then
    printf '  ОТСУТСТВУЕТ: %s\n     %s\n' "$1" "$3"
    fail=1
  else
    printf '  ok: %s\n' "$1"
  fi
}

CHROME="${CHROME_BIN:-$HOME/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing}"
PY="${PYTHON:-$ROOT/backend/.venv/bin/python}"

preflight() {
  echo "Проверка предпосылок:"
  need "python из backend/.venv" "[ -x '$PY' ]" \
    "нет $PY — выполни: cd backend && uv sync --all-extras"
  need "websockets в venv" "'$PY' -c 'import websockets'" \
    "нет пакета websockets (обычно приезжает с uvicorn[standard])"
  need "piper в venv (синтез реплики кандидата)" "'$PY' -c 'import piper'" \
    "нет пакета piper-tts"
  need "Chromium" "[ -x '$CHROME' ]" \
    "нет Chromium по пути CHROME_BIN; подойдёт любой из кеша Playwright"
  need "голос Piper" "[ -f '$ROOT/data/models/piper/en_US-ryan-medium.onnx' ]" \
    "нет data/models/piper/en_US-ryan-medium.onnx"
  need "бэкенд на $API" "curl -s --max-time 3 '$API/health'" \
    "подними: ./scripts/dev.sh (или uvicorn app.main:app --port 8000)"
  need "фронт на $APP" "curl -s --max-time 3 '$APP/'" \
    "подними: cd frontend && npm run dev"
  need "ollama" "curl -s --max-time 3 http://127.0.0.1:11434/api/tags" \
    "подними: ollama serve"
  [ "$fail" = "0" ] || { echo; echo "Стенд не запущен: не хватает перечисленного выше."; exit 2; }
}

make_wav() {
  [ -f "$OUT/answer.wav" ] && return 0
  mkdir -p "$OUT"
  echo "Синтезирую реплику кандидата (Piper)..."
  "$PY" - "$ROOT" "$OUT" <<'PYGEN'
import sys, wave, pathlib, subprocess
from piper import PiperVoice, SynthesisConfig
root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
voice = PiperVoice.load(str(root / "data/models/piper/en_US-ryan-medium.onnx"))
text = ("Sure. I built an internal tool that turns speech into text, sends it to a local "
        "language model, and speaks the answer back. The hard part was latency, so I stream "
        "each sentence to the speaker as soon as it is ready.")
raw = out / "answer_raw.wav"
with wave.open(str(raw), "wb") as w:
    voice.synthesize_wav(text, w, syn_config=SynthesisConfig(length_scale=1.0))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(out / "answer.wav")], check=True)
print("  готово:", out / "answer.wav")
PYGEN
}

# Сценарию `mic` не нужны ни ollama, ни whisper, ни Piper: он не говорит и не
# слушает агента, а проверяет выбор входа. Полный preflight отказал бы ему в
# запуске из-за инструментов, которые он не трогает.
preflight_light() {
  echo "Проверка предпосылок (облегчённая):"
  need "python из backend/.venv" "[ -x '$PY' ]" \
    "нет $PY — выполни: cd backend && uv sync --all-extras"
  need "websockets в venv" "'$PY' -c 'import websockets'" \
    "нет пакета websockets (обычно приезжает с uvicorn[standard])"
  need "Chromium" "[ -x '$CHROME' ]" \
    "нет Chromium по пути CHROME_BIN; подойдёт любой из кеша Playwright"
  need "бэкенд на $API" "curl -s --max-time 3 '$API/health'" \
    "подними: uvicorn app.main:app --port 8000"
  need "фронт на $APP" "curl -s --max-time 3 '$APP/'" \
    "подними: cd frontend && npm run dev"
  [ "$fail" = "0" ] || { echo; echo "Стенд не запущен: не хватает перечисленного выше."; exit 2; }
}

case "${1:-mid-turn}" in
  -h|--help|help) usage; exit 0 ;;
  mid-turn) preflight; make_wav; BROWSER_EVAL_OUT="$OUT" "$PY" "$HERE/stand.py" ;;
  tabs)     preflight; BROWSER_EVAL_OUT="$OUT" "$PY" "$HERE/tabs.py" History
            BROWSER_EVAL_OUT="$OUT" "$PY" "$HERE/tabs.py" "Useful Words" ;;
  mic)      preflight_light; BROWSER_EVAL_OUT="$OUT" "$PY" "$HERE/mic.py" ;;
  all)      preflight; make_wav; BROWSER_EVAL_OUT="$OUT" "$PY" "$HERE/stand.py"
            BROWSER_EVAL_OUT="$OUT" "$PY" "$HERE/tabs.py" History
            BROWSER_EVAL_OUT="$OUT" "$PY" "$HERE/tabs.py" "Useful Words"
            BROWSER_EVAL_OUT="$OUT" "$PY" "$HERE/mic.py" ;;
  *) echo "неизвестный сценарий: $1"; echo; usage; exit 64 ;;
esac
