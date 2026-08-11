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


from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path

from ast_rules import find_inline_prompt, find_silent_except
from ast_web_rules import find_cpu_in_async, find_unbounded_list

FEATURES = Path(os.environ.get("LINT_PY_SRC", "backend/features"))
SKIP_PARTS = ("/tests/", "/migrations/")


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




def scan(repo_root: Path, rule: dict) -> tuple[dict[str, int], int]:
    """→ ({путь: сколько находок}, сколько файлов ПРОСМОТРЕНО).

    `scanned` считается после успешного разбора: файл, который не прочитался или
    не распарсился, гейт не смотрел, и записывать его в доказательство нельзя.
    """
    counts: dict[str, int] = {}
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
    return counts, scanned


def write_baseline(baseline_path: Path, rule: dict, counts: dict[str, int],
                   scanned: int) -> int:
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


def judge(rule_name: str, rule: dict, counts: dict[str, int], snap: dict[str, int],
          scanned: int, strict: bool) -> int:
    """Сверка со снимком и печать. Успех обязан назвать число просмотренного.

    Иначе «код чист» и «просканировано ноль» неотличимы, а приёмка §6 требует
    именно этого числа. Класс закрывался трижды (grep-гейт 1.19, complexity
    1.20/1.22) и трижды не переносился сюда: пятое развёртывание нашло его тремя
    арками сразу — этот скрипт единственный не печатал НИЧЕГО ни на одном пути.
    """
    violations = [(p, c, snap.get(p, 0)) for p, c in sorted(counts.items())
                  if c > snap.get(p, 0)]
    if violations:
        mark = "✗" if strict else "⚠"
        for p, c, allowed in violations:
            print(f"  {mark}  {p}: {c} нарушений (разрешено {allowed})")
        print(f"\n{'ERROR' if strict else 'WARNING'}: {len(violations)} файл(ов) нарушают правило {rule_name}.")
        print(rule["hint"])
        print("Легаси из baseline — ок до чистки; новый код держим на нуле. Пересъём вниз: --generate.")
        return 1 if strict else 0
    if scanned == 0:
        print(f"{rule_name}: 0 файлов просмотрено — проверь LINT_PY_SRC (§6): "
              "гейт, который ничего не видит, хуже красного")
        return 0
    # Маска печатается вместе с числом (`cqg@1.88`): без неё доктор мог только
    # подозревать частичную слепоту, а с ней — считает расхождение.
    print(f"{rule_name}: OK — просмотрено {scanned} файл(ов), в снимке {len(snap)}, "
          f"по маске: {FEATURES}/**/*.py")
    return 0


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

    rule = RULES[args.rule]
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent  # <repo-root>/scripts/lint/ -> repo-root
    baseline_path = script_dir / rule["baseline"]

    counts, scanned = scan(repo_root, rule)
    if args.generate:
        return write_baseline(baseline_path, rule, counts, scanned)
    return judge(args.rule, rule, counts, load_baseline(baseline_path), scanned,
                 os.environ.get("STRICT", "1") == "1")


if __name__ == "__main__":
    sys.exit(main())
