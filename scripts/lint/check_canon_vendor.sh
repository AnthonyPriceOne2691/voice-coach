#!/usr/bin/env bash
# Vendored canon guard (AGENT_STACK.md §7.1, вариант C).
#
# Каноны живут у человека в Prepare/ и НЕ коммитятся, поэтому в CI их физически
# нет и `stack_selftest` там проверять нечего. Копия в docs/canon/ закрывает ровно
# эту дыру. Этот гейт следит за копией:
#   1. SHA256SUMS сходится      — копию не правили на месте;
#   2. stack_selftest на копии  — фенсы парсятся, версии в шапках == таблица §1;
#   3. diff с upstream Prepare/ — ТОЛЬКО локально; в CI upstream отсутствует.
#
# Шаг 3 в CI непроверяем — это записанный остаток варианта C, см.
# docs/canon/VENDORED.md и delivery/STACK-ACCEPTANCE.md → «Остатки».
#
# Настройка (env): CANON_DIR (дефолт docs/canon), CANON_UPSTREAM (дефолт Prepare).
#
# Режимы:
#   check_canon_vendor.sh            # проверка; exit 1 при расхождении
#   STRICT=0 check_canon_vendor.sh   # soft (warning, exit 0)

set -uo pipefail

STRICT=${STRICT:-1}
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1

CANON_DIR=${CANON_DIR:-docs/canon}
UPSTREAM=${CANON_UPSTREAM:-Prepare}
SUMS="$CANON_DIR/SHA256SUMS"

fail() {
  if [ "$STRICT" = "0" ]; then
    echo "WARNING (soft): $1" >&2
    exit 0
  fi
  echo "FAIL: $1" >&2
  exit 1
}

[ -d "$CANON_DIR" ] || fail "нет каталога $CANON_DIR — вендоренная копия канонов отсутствует"
[ -f "$SUMS" ] || fail "нет $SUMS — манифест копии отсутствует, дрейф не отследить"

# --- 1. Контрольные суммы ----------------------------------------------------
# shasum есть на macOS и в ubuntu-runner'ах; sha256sum — только в GNU coreutils.
if command -v shasum >/dev/null 2>&1; then
  SUMCMD="shasum -a 256 -c"
elif command -v sha256sum >/dev/null 2>&1; then
  SUMCMD="sha256sum -c"
else
  fail "нет ни shasum, ни sha256sum — проверить манифест нечем"
fi

if ! (cd "$CANON_DIR" && $SUMCMD --status SHA256SUMS); then
  echo "Копия канонов разошлась с манифестом. Что именно:" >&2
  (cd "$CANON_DIR" && $SUMCMD SHA256SUMS) >&2 || true
  fail "docs/canon/ правили на месте. Канон правится в $UPSTREAM/, затем — инструкция в docs/canon/VENDORED.md"
fi
n_canon=$(grep -c . "$SUMS")
echo "canon-vendor: манифест сходится ($n_canon файлов)"

# --- 2. stack_selftest на копии ---------------------------------------------
PY=$(command -v python3 || command -v python)
[ -n "$PY" ] || fail "нет python3/python — stack_selftest не запустить"
if [ -f scripts/stack_selftest.py ]; then
  "$PY" scripts/stack_selftest.py "$CANON_DIR" || fail "stack_selftest упал на $CANON_DIR"
else
  fail "нет scripts/stack_selftest.py — payload канонов ничем не проверяется"
fi

# --- 3. Дрейф от upstream (только там, где upstream есть) --------------------
if [ -d "$UPSTREAM" ]; then
  drift=0
  for f in "$CANON_DIR"/*.md; do
    base=$(basename "$f")
    [ "$base" = "VENDORED.md" ] && continue
    if [ ! -f "$UPSTREAM/$base" ]; then
      echo "  drift: $base есть в копии, но нет в $UPSTREAM/" >&2
      drift=1
    elif ! cmp -s "$f" "$UPSTREAM/$base"; then
      echo "  drift: $base отличается от $UPSTREAM/$base" >&2
      drift=1
    fi
  done
  if [ "$drift" = "1" ]; then
    fail "копия разошлась с upstream $UPSTREAM/ — пересними: см. docs/canon/VENDORED.md"
  fi
  echo "canon-vendor: копия совпадает с upstream $UPSTREAM/"
else
  # Не тихий skip: отсутствие upstream — ожидаемое состояние CI, и оно печатается,
  # чтобы «шаг 3 не выполнялся» было видно в логе, а не подразумевалось.
  echo "canon-vendor: upstream $UPSTREAM/ отсутствует (ожидаемо в CI) — шаг 3 (дрейф) НЕ проверен"
fi

echo "canon-vendor: OK"
