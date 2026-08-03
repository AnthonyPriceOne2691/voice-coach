#!/usr/bin/env bash
# Ратчет по сложности ФУНКЦИЙ: цикломатика, ветвления, операторы, аргументы, return'ы.
#
# Зачем отдельным гейтом, если правила уже есть в ruff. Обычный ruff-хук даёт
# бинарное «да/нет» на весь пакет. На легаси это означает сотни срабатываний в
# первый же день — и правила отправляются в `ignore` целиком, после чего сложность
# не контролируется НИГДЕ. Ратчет снимает это противоречие: старое зафиксировано
# снимком, новый код держим на нуле, снимок только тает.
#
# Почему это важнее длины файла: file-length смотрит на файл, а плохой код живёт
# в функции. Функция на 400 строк внутри файла на 480 строк проходит file-length
# свободно.
#
# Пороги берутся из pyproject проекта ([tool.ruff.lint.mccabe] / [.pylint]) —
# один источник правды. `lint.ignore=[]` сбрасывает ignore, чтобы правила
# отработали даже если в конфиге они заглушены для основного хука.
#
# Настройка (env): LINT_PY_SRC, LINT_VENV, STRICT=0 — soft.
#
# Режимы:
#   check_complexity_gate.sh             # проверка
#   check_complexity_gate.sh --generate  # пере-снять baseline
#   check_complexity_gate.sh --report    # показать текущие нарушения по файлам

set -uo pipefail

STRICT=${STRICT:-1}
PY_SRC=${LINT_PY_SRC:-backend/features}
VENV=${LINT_VENV:-backend/.venv}
# Значение, данное «относительно backend» (так его описывала §6 до cqg@1.33),
# тоже принимается: одно написание не могло удовлетворить обе трактовки, и
# документированное `.venv` глушило этот гейт мягким пропуском (lab-9 №7).
[[ -d "$VENV" || ! -d "backend/$VENV" ]] || VENV="backend/$VENV"
RULES=${LINT_COMPLEXITY_RULES:-C901,PLR0911,PLR0912,PLR0913,PLR0915}
MODE=${1:-check}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BASELINE="$SCRIPT_DIR/complexity_baseline.txt"

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT" || exit 1

red=$(printf '\033[31m'); yellow=$(printf '\033[33m'); green=$(printf '\033[32m'); reset=$(printf '\033[0m')

RUFF="$VENV/bin/ruff"
[[ -x "$RUFF" ]] || RUFF=$(command -v ruff 2>/dev/null || true)
if [[ -z "$RUFF" ]]; then
  printf '%s⚠ ruff не найден — гейт сложности пропущен. Установка: pip install ruff%s\n' \
    "$yellow" "$reset"
  exit 0
fi
if [[ ! -d "$PY_SRC" ]]; then
  printf '%s⚠ нет каталога %s — гейт сложности пропущен (настрой LINT_PY_SRC, §6)%s\n' \
    "$yellow" "$PY_SRC" "$reset"
  exit 0
fi

# "<count>:<path>" — тот же формат, что у остальных снимков, поэтому
# check_baseline_ratchet.sh автоматически следит и за этим файлом.
current_counts() {
  "$RUFF" check --no-cache --quiet --output-format=concise \
      --select "$RULES" --config 'lint.ignore=[]' -- "$PY_SRC" 2>/dev/null \
    | awk -F: 'NF>=4 { c[$1]++ } END { for (f in c) printf "%d:%s\n", c[f], f }' \
    | sort -t: -k2
}

tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
current_counts >"$tmp"

if [[ "$MODE" == "--generate" ]]; then
  {
    echo "# complexity_baseline.txt — снимок нарушений сложности ФУНКЦИЙ по файлам."
    echo "# Формат: <число нарушений>:<путь>. Правила: $RULES"
    echo "# Пороги — в pyproject ([tool.ruff.lint.mccabe] / [.pylint])."
    echo "# Снимок только ТАЕТ: тронул файл — раздели функцию и пере-сними вниз."
    cat "$tmp"
  } >"$BASELINE"
  # Просмотренное и «с находками» — РАЗНЫЕ числа, и печатать надо оба (F6).
  # `grep -cv '^#'` считает файлы С НАРУШЕНИЯМИ; на чистом проекте это «0», что
  # неотличимо от «ruff смотрел не туда». Тот же класс L2, что уже правился в
  # check-режиме этого же гейта, — в ветке `--generate` остался.
  n_seen=$(git ls-files -- "$PY_SRC" 2>/dev/null | grep -c '\.py$' || true)
  printf '%sbaseline пересобран:%s %s — просмотрено %s файл(ов), с находками %d\n' \
    "$green" "$reset" "$BASELINE" "$n_seen" "$(grep -cv '^#' "$BASELINE")"
  if [[ "$n_seen" == "0" ]]; then
    printf '%s⚠ просмотрено 0 файлов — проверь LINT_PY_SRC (§6): пустой снимок на\n' "$yellow"
    printf 'непустом проекте значит «гейт смотрел не туда».%s\n' "$reset"
  fi
  exit 0
fi

if [[ "$MODE" == "--report" ]]; then
  printf 'Нарушения сложности по файлам (правила %s):\n' "$RULES"
  "$RUFF" check --no-cache --quiet --output-format=concise \
    --select "$RULES" --config 'lint.ignore=[]' -- "$PY_SRC" 2>/dev/null
  exit 0
fi

violations=0
# `scanned` — число ПРОСМОТРЕННЫХ файлов, а не файлов с находками. Первая версия
# счётчика (cqg@1.20) считала итерации цикла ниже, а цикл идёт по НАХОДКАМ ruff:
# на чистом проекте выходило «просмотрено 0 файл(ов)», что по смыслу §6 читается
# как «гейт ничего не видел». Хуже — одна и та же фраза в двух гейтах канона
# значила разное. Найдено независимым развёртыванием (lab-4).
scanned=$(git ls-files "$PY_SRC/" 2>/dev/null | grep -cE "${LINT_SRC_EXT_RE:-\.py$}") || true
scanned=${scanned:-0}
flagged=0
while IFS=: read -r count path; do
  [[ -n "$path" ]] || continue
  allowed=0
  if [[ -f "$BASELINE" ]]; then
    allowed=$(awk -F: -v p="$path" '!/^#/ && $2 == p { print $1; exit }' "$BASELINE")
    allowed=${allowed:-0}
  fi
  flagged=$((flagged + 1))
  if (( count > allowed )); then
    printf '%s  ✗  %s: %d нарушений сложности (разрешено %d)%s\n' \
      "$red" "$path" "$count" "$allowed" "$reset"
    violations=$((violations + 1))
  fi
done <"$tmp"

if (( violations == 0 )); then
  # Число просмотренного — обязательная часть вывода (приёмка §6), иначе «OK»
  # неотличимо от «нечего было смотреть».
  if (( scanned == 0 )); then
    printf '%scomplexity: 0 файлов просмотрено%s — проверь LINT_PY_SRC (§6)\n' \
      "$yellow" "$reset"
    exit 0
  fi
  printf '%scomplexity: OK%s — просмотрено %d файл(ов), с находками %d\n' \
    "$green" "$reset" "$scanned" "$flagged"
  exit 0
fi

printf '\n%sERROR%s: %d файл(ов) превышают снимок сложности.\n' "$red" "$reset" "$violations" >&2
printf 'Дели функцию (§2.1: thin orchestrator + phase-helpers), не поднимай порог.\n' >&2
printf 'Что именно длинное/ветвистое: %s --report\n' "$0" >&2
printf 'Легаси-файл впервые попал под гейт? --generate (снимок только вниз).\n' >&2
[[ "$STRICT" == "0" ]] && { printf '%sWARNING (STRICT=0)%s\n' "$yellow" "$reset" >&2; exit 0; }
exit 1