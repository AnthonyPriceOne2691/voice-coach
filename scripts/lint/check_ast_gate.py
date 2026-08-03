#!/usr/bin/env python3
"""AST-гейты для конвенций, которые grep не выразит.

Правила:
  silent-except  — «глухой» broad-except: `except Exception/BaseException/голый:`
                   без raise / логирования / record в теле хендлера (ошибка обязана
                   оставить след). Осознанный fail-soft помечается комментарием
                   `# silent-ok: <причина>` внутри хендлера — тогда сайт легален.
  inline-prompt  — LLM-промпт инлайном в .py: не-docstring строка >= 8 строк,
                   начинающаяся с персона-маркера («Ты — …», "You are …", …).
                   Порог по маркеру, не по длине: длинные SQL/Lua/regex легитимны.

Механика — per-file baseline-ratchet: легаси в снимке (`<count>:<path>`, путь от
repo-root); файл проходит при count <= снимок; файл вне снимка (любой новый) — hard 0.
Пересъём вниз: --generate.

Настройка (env):
  LINT_PY_SRC — корневой каталог прод-Python для гейтов, от repo-root (дефолт: backend/features)

Запуск (скрипт лежит в <repo-root>/scripts/lint/):
  python scripts/lint/check_ast_gate.py --rule silent-except
  python scripts/lint/check_ast_gate.py --rule silent-except --generate
  STRICT=0 …  — soft-режим (warning, exit 0), аварийно.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path

FEATURES = Path(os.environ.get("LINT_PY_SRC", "backend/features"))
SKIP_PARTS = ("/tests/", "/migrations/")
SILENT_OK_MARKER = "# silent-ok:"

_LOG_BASES = {"logger", "logging", "log", "warnings"}
_LOG_ATTR_PREFIXES = ("log", "warn", "exception", "error", "record", "capture", "notify")
_PROMPT_MARKERS = ("ты —", "ты -", "you are", "you classify", "act as", "роль:", "system:")
_PROMPT_MIN_LINES = 8


def _is_broad(handler: ast.ExceptHandler) -> bool:
    t = handler.type
    if t is None:
        return True
    if isinstance(t, ast.Name) and t.id in ("Exception", "BaseException"):
        return True
    if isinstance(t, ast.Tuple):
        return any(isinstance(e, ast.Name) and e.id in ("Exception", "BaseException") for e in t.elts)
    return False


def _handler_leaves_trace(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                base = func.value
                if isinstance(base, ast.Name) and base.id in _LOG_BASES:
                    return True
                if func.attr.startswith(_LOG_ATTR_PREFIXES):
                    return True
            if isinstance(func, ast.Name) and func.id.startswith(("log", "record", "capture", "notify")):
                return True
    return False


def _handler_has_silent_ok(handler: ast.ExceptHandler, src_lines: list[str]) -> bool:
    end = handler.body[-1].end_lineno if handler.body else handler.lineno
    for i in range(handler.lineno - 1, min(end, len(src_lines))):
        if SILENT_OK_MARKER in src_lines[i]:
            return True
    return False


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def find_silent_except(tree: ast.AST, src_lines: list[str]) -> list[int]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and _is_broad(node) and not _handler_leaves_trace(node) and not _handler_has_silent_ok(node, src_lines):
            out.append(node.lineno)
    return out


def find_inline_prompt(tree: ast.AST, src_lines: list[str]) -> list[int]:  # noqa: ARG001
    doc_ids = _docstring_ids(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
            if node.value.count("\n") + 1 < _PROMPT_MIN_LINES:
                continue
            head = node.value.strip().lower()
            if head.startswith(_PROMPT_MARKERS):
                out.append(node.lineno)
    return out


_ROUTE_DECOR = ("get", "post", "put", "patch", "delete", "route", "api_route")
_BOUND_PARAMS = ("limit", "page_size", "per_page", "size", "count", "top", "first",
                 "max_results")
_LIST_TYPES = ("list", "List", "Sequence", "Iterable")
_UNBOUNDED_OK_MARKER = "# unbounded-ok:"


def _is_route(fn: ast.AST) -> bool:
    """Декоратор вида `@router.get(...)` / `@app.route(...)`."""
    for dec in fn.decorator_list:
        call = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(call, ast.Attribute) and call.attr in _ROUTE_DECOR:
            return True
    return False


def _returns_list(fn: ast.AST) -> bool:
    """Аннотация возврата — именно список, а не конверт со страницей."""
    ret = fn.returns
    if isinstance(ret, ast.Name):
        return ret.id == "list"
    if isinstance(ret, ast.Subscript):
        base = ret.value
        if isinstance(base, ast.Name):
            return base.id in _LIST_TYPES
        if isinstance(base, ast.Attribute):
            return base.attr in _LIST_TYPES
    return False


def _has_bound_param(fn: ast.AST) -> bool:
    """Граница объявлена И ИСПОЛЬЗУЕТСЯ в теле.

    Второе условие — не придирка, а защита от того, что проверка сама же
    подсказывает: приписать `limit: int = 50` в подпись и не передать его вниз.
    Такой эндпоинт отдаёт всё по-прежнему, но выглядит исправленным — и в OpenAPI
    параметр даже виден. Слабая форма ПРОВЕРЕНА подстановкой: без этого условия
    гейт печатал OK на `list_all(q)` с объявленным и проигнорированным `limit`.
    Цена ложного срабатывания тут низкая: параметр, который правда используется,
    в теле упоминается — иначе он не влияет ни на что.
    """
    a = fn.args
    declared = {x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)
                if x.arg.lower() in _BOUND_PARAMS}
    if not declared:
        return False
    used = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    # `**kwargs`-проброс: имя параметра в теле не появляется, но граница уходит вниз.
    if a.kwarg is not None and a.kwarg.arg in used:
        return True
    return bool(declared & used)


def _unbounded_ok(fn: ast.AST, src_lines: list[str]) -> bool:
    start = fn.decorator_list[0].lineno if fn.decorator_list else fn.lineno
    end = fn.body[-1].end_lineno if fn.body else fn.lineno
    return any(_UNBOUNDED_OK_MARKER in src_lines[i]
               for i in range(start - 1, min(end, len(src_lines))))


def find_unbounded_list(tree: ast.AST, src_lines: list[str]) -> list[int]:
    """Эндпоинт отдаёт список без границы — выборка растёт с корпусом.

    Признак составной, и каждая часть нужна:
      • это РОУТ — во внутреннем хелпере «отдать всё» законно;
      • аннотация возврата — список, а не конверт (`ItemsPage` с `total`/`items`
        обычно уже описывает страницу);
      • нет ни одного параметра границы из `_BOUND_PARAMS`.

    lab-12, ловушка T4: обе независимые арки написали ПОЧТИ ДОСЛОВНО одинаковый
    `list_all()` — при том что в том же приложении рядом лежал сосед с лимитом
    (`/sessions/interviews?limit=5` отдавал 5, новый `?limit=5` отдавал 300 и 137).
    То есть образец правильного кода в том же файле slip не предотвратил, а оракула
    этого класса в стеке не было ни одного вида. На живом проекте это ещё и вектор
    отказа, а не только медленный ответ.

    Осознанный случай называется словом: `# unbounded-ok: <причина>` — например
    перечисление статусов, которое по устройству не растёт.
    """
    out: list[int] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _is_route(fn) or not _returns_list(fn):
            continue
        if _has_bound_param(fn) or _unbounded_ok(fn, src_lines):
            continue
        out.append(fn.lineno)
    return out


_CPU_CALLS = {
    ("json", "loads"), ("json", "dumps"),
    ("re", "search"), ("re", "match"), ("re", "findall"), ("re", "finditer"),
    ("re", "compile"), ("re", "sub"),
    ("pickle", "loads"), ("pickle", "dumps"),
    ("yaml", "safe_load"), ("yaml", "load"),
    ("base64", "b64decode"), ("base64", "b64encode"),
    ("hashlib", "md5"), ("hashlib", "sha256"),
}
_OFFLOAD = ("to_thread", "run_in_executor", "run_in_threadpool", "run_sync", "gather")
_CPU_OK_MARKER = "# cpu-ok:"


def _offloaded(fn: ast.AST) -> bool:
    """В теле корутины есть перенос работы с цикла — правило не про неё."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr in _OFFLOAD:
                return True
            if isinstance(f, ast.Name) and f.id in _OFFLOAD:
                return True
    return False


def find_cpu_in_async(tree: ast.AST, src_lines: list[str]) -> list[int]:
    """CPU-работа в ЦИКЛЕ внутри `async def` — голодание event loop.

    Признак составной, и каждая часть нужна:
      • `async def` — в обычной функции это не дефект;
      • ЦИКЛ (`for`/`while`/comprehension) — один `json.loads` дёшев, беда в том,
        что стоимость растёт с размером выборки;
      • вызов из списка `_CPU_CALLS` — разбор/сериализация/регулярка/хеш.

    Не срабатывает, если в теле есть перенос на пул (`to_thread`,
    `run_in_threadpool`, …) или стоит `# cpu-ok: <причина>` — осознанный случай
    называется словом, как `# silent-ok:` у соседнего правила.

    lab-12: единственный класс, подтверждённый как slipped ОБЕИМИ арками. Обе
    независимо написали `for row in await list_all(): json.loads(row.…)` в
    async-хендлере; канарейка «чистый CPU в async» под конфигом обеих арен дала
    exit 0 — в стеке не было оракула этого класса ни одного вида. ASYNC-правила
    ruff ловят блокирующий IO (`open`, `sleep`), а чистый CPU — нет.
    """
    out: list[int] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.AsyncFunctionDef) or _offloaded(fn):
            continue
        for node in ast.walk(fn):
            loop_body: list[ast.AST]
            if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                loop_body = list(node.body)
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                loop_body = [node]
            else:
                continue
            for inner in loop_body:
                for call in ast.walk(inner):
                    if not isinstance(call, ast.Call):
                        continue
                    f = call.func
                    if not (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)):
                        continue
                    if (f.value.id, f.attr) not in _CPU_CALLS:
                        continue
                    line = src_lines[call.lineno - 1] if call.lineno <= len(src_lines) else ""
                    if _CPU_OK_MARKER in line:
                        continue
                    out.append(call.lineno)
    return sorted(set(out))


RULES = {
    "silent-except": {
        "find": find_silent_except,
        "baseline": "silent_except_baseline.txt",
        "label": "silent-except: broad-except без raise/лога",
        "hint": "Оставь след: logger.warning/exception с контекстом, либо пробрось. Осознанный fail-soft — пометь `# silent-ok: <причина>` в хендлере.",
    },
    "unbounded-list": {
        "find": find_unbounded_list,
        "baseline": "unbounded_list_baseline.txt",
        "label": "unbounded-list: эндпоинт отдаёт список без границы",
        "hint": "Добавь `limit` (и `offset`/курсор) с потолком по умолчанию — иначе объём ответа растёт вместе с корпусом, и это вектор отказа, а не медленный ответ. Набор, который по устройству не растёт, помечай `# unbounded-ok: <причина>`.",
    },
    "cpu-in-async": {
        "find": find_cpu_in_async,
        "baseline": "cpu_in_async_baseline.txt",
        "label": "cpu-in-async: разбор/регулярка в цикле внутри async def",
        "hint": "Стоимость растёт с размером выборки, а event loop встаёт на всё это время. Ограничь выборку (limit), перенеси разбор в БД/индекс, либо унеси в пул: `await asyncio.to_thread(...)`. Осознанно оставить — `# cpu-ok: <причина>` на строке вызова.",
    },
    "inline-prompt": {
        "find": find_inline_prompt,
        "baseline": "inline_prompt_baseline.txt",
        "label": "inline-prompt: LLM-промпт инлайном в .py",
        "hint": "Промпт — в отдельный <name>.md + lazy-load, не строкой в коде.",
    },
}


def iter_target_files(repo_root: Path):
    for path in sorted((repo_root / FEATURES).rglob("*.py")):
        rel = path.as_posix()
        if any(part in rel for part in SKIP_PARTS):
            continue
        if path.name.startswith("test_") or path.name == "conftest.py":
            continue
        yield path


def repo_rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def load_baseline(baseline_path: Path) -> dict[str, int]:
    snap: dict[str, int] = {}
    if not baseline_path.is_file():
        return snap
    for line in baseline_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or ":" not in line:
            continue
        count, _, p = line.partition(":")
        if count.isdigit():
            snap[p] = int(count)
    return snap


def main() -> int:
    parser = argparse.ArgumentParser()
    # --list-rules печатает правила этого скрипта: мета-гейт сверяет подключение
    # ПРАВИЛ, а не только файлов (F7). Поэтому --rule не required: список должен
    # быть доступен без выбора правила.
    parser.add_argument("--rule", choices=sorted(RULES))
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--list-rules", action="store_true")
    args = parser.parse_args()
    if args.list_rules:
        for name in sorted(RULES):
            print(name)
        return 0
    if not args.rule:
        parser.error("--rule обязателен (или --list-rules)")

    strict = os.environ.get("STRICT", "1") == "1"
    rule = RULES[args.rule]

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent  # <repo-root>/scripts/lint/ -> repo-root
    baseline_path = script_dir / rule["baseline"]

    counts: dict[str, int] = {}
    # `scanned` — число ПРОСМОТРЕННЫХ файлов, а не файлов с находками (§6). Считается
    # после успешного разбора: файл, который не прочитался или не распарсился, гейт
    # не смотрел, и записывать его в доказательство нельзя.
    scanned = 0
    for path in iter_target_files(repo_root):
        try:
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        scanned += 1
        hits = rule["find"](tree, src.splitlines())
        if hits:
            counts[repo_rel(path, repo_root)] = len(hits)

    if args.generate:
        lines = [
            f"# {rule['baseline']} — снимок AST-гейта. Генерируется --generate, НЕ руками.",
            f"# Правило: {rule['label']}",
            "# Формат: <count>:<path> (path от repo-root). Ратчет вниз: файл проходит при count <= снимок;",
            "# файл ВНЕ снимка (новый) — hard 0.",
        ]
        lines += [f"{c}:{p}" for p, c in sorted(counts.items())]
        baseline_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(
            f"baseline пересобран: {baseline_path.name} — просмотрено {scanned} файл(ов), "
            f"с находками {len(counts)}, сайтов {sum(counts.values())}"
        )
        return 0

    snap = load_baseline(baseline_path)
    violations = []
    for p, c in sorted(counts.items()):
        allowed = snap.get(p, 0)
        if c > allowed:
            violations.append((p, c, allowed))

    if violations:
        mark = "✗" if strict else "⚠"
        for p, c, allowed in violations:
            print(f"  {mark}  {p}: {c} нарушений (разрешено {allowed})")
        print(f"\n{'ERROR' if strict else 'WARNING'}: {len(violations)} файл(ов) нарушают правило {args.rule}.")
        print(rule["hint"])
        print("Легаси из baseline — ок до чистки; новый код держим на нуле. Пересъём вниз: --generate.")
        return 1 if strict else 0

    # Успешный путь обязан печатать число просмотренных файлов — иначе «код чист» и
    # «просканировано ноль» неотличимы, а приёмка §6 требует именно этого числа.
    # Класс закрывался трижды (grep-гейт 1.19, complexity 1.20/1.22), и трижды не
    # переносился на этот скрипт: пятое развёртывание нашло его тремя арками сразу —
    # он единственный не печатал НИЧЕГО ни на одном пути.
    if scanned == 0:
        print(f"{args.rule}: 0 файлов просмотрено — проверь LINT_PY_SRC (§6): "
              "гейт, который ничего не видит, хуже красного")
        return 0
    print(f"{args.rule}: OK — просмотрено {scanned} файл(ов), в снимке {len(snap)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())