#!/usr/bin/env bash
# Измеряющие половины гейта сложности: python (ruff) и ts (eslint).
#
# Часть `check_complexity_gate.sh` (`cqg@1.85`) — гейт разрезан по планке 300
# строк (Delivery §9.1a п.5). Здесь только СЧЁТ: сколько функций нарушают пороги
# и сколько файлов при этом просмотрено. Пороги, снимок, вердикт и печать
# остались во входном скрипте — резать надо по вопросу, а не по размеру.
#
# Подключается через `source`; переменные (`PY_SRC`, `TS_SRC`, `RUFF`, `ESLINT`,
# `py_live`, `ts_live`, `RULES`, `TS_RULES`) задаёт вход до вызова функций.
# Самостоятельно файл не запускается: гейт — это `check_*`, а это его часть.

# Просмотренное считается по ОБЕИМ живым половинам. «Просмотрено N» — это
# доказательство §6, и на fullstack-репо оно обязано складываться: иначе число
# врёт в меньшую сторону ровно там, где вторая половина как раз работает.
count_seen() {
  local n=0 half
  if (( py_live )); then
    half=$(git ls-files -- "$PY_SRC" 2>/dev/null | grep -cE "${LINT_SRC_EXT_RE:-\.py$}") || true
    n=$(( n + ${half:-0} ))
  fi
  if (( ts_live )); then
    half=$(git ls-files -- "$TS_SRC" 2>/dev/null \
             | grep -cE "${LINT_TS_EXT_RE:-\.(ts|tsx|js|jsx|mts|cts)$}") || true
    n=$(( n + ${half:-0} ))
  fi
  printf '%d' "$n"
}

py_counts() {
  local out rc
  out=$("$RUFF" check --no-cache --quiet --output-format=concise \
          --select "$RULES" --config 'lint.ignore=[]' -- "$PY_SRC" 2>"$errf")
  rc=$?
  if (( rc > 1 )); then
    printf '%sERROR%s: ruff вышел с кодом %d — снимок НЕ снят и старый не тронут.\n' \
      "$red" "$reset" "$rc" >&2
    sed 's/^/  ruff: /' "$errf" >&2
    printf 'Пустой снимок при живом ruff неотличим от «нарушений нет» (находка 8:\n' >&2
    printf '1 прогон из 5 дал 0 находок при факте 1). Починить вызов, потом снимать.\n' >&2
    return 2
  fi
  printf '%s\n' "$out" \
    | awk -F: 'NF>=4 { c[$1]++ } END { for (f in c) printf "%d:%s\n", c[f], f }' \
    | sort -t: -k2
}

# TS-половина. Три её свойства ЗАМЕРЕНЫ, и каждое иначе стоило бы тихого зелёного.
#
# 1. Правила НАВЯЗЫВАЮТСЯ флагом `--rule`, а не берутся из конфига проекта. Замер:
#    проект, поставивший себе `complexity: off`, гейтом всё равно ловится. Это тот
#    же смысл, что `lint.ignore=[]` у ruff-половины: порог принадлежит гейту.
#    Конфиг проекта при этом НУЖЕН — он даёт парсер; гейт даёт пороги.
# 2. Ошибка РАЗБОРА неотличима от находки по коду возврата: eslint без парсера
#    TypeScript печатает «Parsing error» и выходит ЕДИНИЦЕЙ — ровно как при
#    настоящем нарушении. Дискриминатор только в JSON: `fatal: true` /
#    `ruleId: null`. Такой файл НЕ проанализирован, и засчитать его за «ноль
#    нарушений» — это выдать непроверенное за чистое (класс F17).
# 3. JSON читается НЕСТРОГО (`strict=False`): сообщение об ошибке разбора несёт
#    сырой управляющий символ, и строгий `json.loads` падает трейсбеком ровно на
#    том случае, который гейт обязан диагностировать.
# ⚠ АДАПТАЦИЯ ПРОЕКТА (объявлена в `scripts/lint/adapted.json`), одна строка.
# Гейт зовёт eslint из КОРНЯ репозитория, а flat-config ищется от cwd — здесь
# `eslint.config.js` лежит во фронт-каталоге, и eslint выходил кодом 2
# («couldn't find an eslint.config.(js|mjs|cjs) file»), то есть TS-половина
# роняла гейт вместо того, чтобы судить. Флаг `--config` заодно чинит и базу
# glob'ов: с ним `files: ['src/**']` считается от каталога конфига, как и задумано
# автором конфига. Ищется по кандидатам, отсутствие — не ошибка: тогда поведение
# ровно канонное. `LINT_ESLINT_CONFIG` переопределяет, если раскладка изменится.
_ts_config_flag() {
  local c
  for c in "${LINT_ESLINT_CONFIG:-}" "$FE_DIR/eslint.config.js" \
           "$FE_DIR/eslint.config.mjs" "$FE_DIR/eslint.config.cjs"; do
    [[ -n "$c" && -f "$c" ]] && { printf -- '--config\n%s\n' "$c"; return 0; }
  done
}

ts_counts() {
  local out rc body prc
  local cfg=(); while IFS= read -r line; do cfg+=("$line"); done < <(_ts_config_flag)
  out=$("$ESLINT" "$TS_SRC" "${cfg[@]}" --format json --no-color --rule "$TS_RULES" 2>"$errf")
  rc=$?
  if (( rc > 1 )); then
    printf '%sERROR%s: eslint вышел с кодом %d — снимок НЕ снят и старый не тронут.\n' \
      "$red" "$reset" "$rc" >&2
    sed 's/^/  eslint: /' "$errf" >&2
    printf 'Код 2 у eslint — это ошибка конфига или CLI, а не находки.\n' >&2
    return 2
  fi
  body=$(printf '%s' "$out" | python3 -c '
import json, os, sys
raw = sys.stdin.read()
try:
    data = json.loads(raw, strict=False)
except Exception:
    sys.stderr.write("вывод eslint не разобран как JSON\n")
    raise SystemExit(3)
root = os.getcwd().rstrip(os.sep) + os.sep
counts, fatal = {}, []
for entry in data:
    path = entry.get("filePath", "")
    if path.startswith(root):
        path = path[len(root):]
    for m in entry.get("messages", []):
        if m.get("fatal") or m.get("ruleId") is None:
            head = (str(m.get("message", "")).splitlines() or [""])[0]
            fatal.append(path + ": " + head)
            continue
        counts[path] = counts.get(path, 0) + 1
if fatal:
    sys.stderr.write("файлы НЕ разобраны — это не «ноль нарушений»:\n")
    for line in fatal[:5]:
        sys.stderr.write("  " + line + "\n")
    raise SystemExit(4)
for p in sorted(counts):
    sys.stdout.write("%d:%s\n" % (counts[p], p))
' 2>>"$errf")
  prc=$?
  if (( prc != 0 )); then
    printf '%sERROR%s: TS-половина НЕ проверена — снимок не снят и старый не тронут.\n' \
      "$red" "$reset" >&2
    sed 's/^/  eslint: /' "$errf" >&2
    printf 'Нет парсера TS в конфиге проекта? Гейт берёт оттуда разбор, а пороги\n' >&2
    printf 'навязывает сам. Починить конфиг, потом снимать (§3.2b).\n' >&2
    return 2
  fi
  [[ -n "$body" ]] && printf '%s\n' "$body"
  return 0
}

# Обе половины — в ОДИН снимок и один формат. Порядок фиксируем сортировкой,
# иначе сверка двух прогонов в `--generate` ловила бы перестановку как расхождение.
current_counts() {
  local acc="" half
  if (( py_live )); then
    acc=$(py_counts) || return 2
  fi
  if (( ts_live )); then
    half=$(ts_counts) || return 2
    acc="$acc${acc:+$'\n'}$half"
  fi
  [[ -n "$acc" ]] && printf '%s\n' "$acc" | sort -t: -k2
  return 0
}
