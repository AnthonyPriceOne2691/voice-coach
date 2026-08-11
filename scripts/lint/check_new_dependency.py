#!/usr/bin/env python3
"""Гейт: новая зависимость — решение, а не деталь диффа.

Зачем. Объём диффа ограничен circuit breaker'ами (Delivery §3.4), а добавление
библиотеки не ограничено ничем — хотя это **самое долгоживущее решение, которое
агент принимает молча**: пакет остаётся в проекте на годы, тянет транзитивные
зависимости, свою лицензию, свой темп релизов и свои уязвимости.

Что делает. Сравнивает **МНОЖЕСТВА имён прямых зависимостей** в BASE и HEAD.
Именно множества, а не добавленные строки диффа: bump версии, переупорядочивание
и переформатирование манифеста новой зависимостью не являются, и гейт, который
ругался бы на них, сняли бы через неделю (Delivery §4.3b).

Требование. Каждое НОВОЕ имя объявлено строкой в `delivery/active/STATUS.md`:

    new_dependency: <pkg> reason=<зачем и что рассмотрено> by=<human:NAME|agent:NAME>

Форма — по образцу waiver'ов (Delivery §4.3a): видна в диффе PR, живёт одну
поставку, уходит в archive вместе с ней. `reason=` и `by=` обязательны: без них
это упоминание пакета, а не решение.

Что НЕ считается — сознательно:
  * **lock-файлы** (`poetry.lock`, `package-lock.json`, `Cargo.lock`, `yarn.lock`):
    транзитивный сдвиг решением агента не является;
  * **удаление** зависимости — уменьшение поверхности, объявлять нечего;
  * **смена версии** существующей — это `deps-audit`, не этот гейт;
  * **новый манифест целиком** — одно решение («вводим этот менеджер»), а не N;
    объявляется одной строкой с путём манифеста.

Настройка (env): BASE (дефолт `origin/main`), STRICT=0 — soft-режим.

Запуск (CI; на pre-commit не вешать — нужен remote-ref):
  python scripts/lint/check_new_dependency.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys


from dependency_manifests import extractor_for

def git(*args: str) -> str:
    """git с подавлением ошибок: пустая строка = не смог (файла нет в ревизии)."""
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    return out.stdout if out.returncode == 0 else ""



def declared(status: str) -> tuple[set[str], list[str]]:
    """(корректно объявленные имена, строки без reason=/by=)."""
    ok: set[str] = set()
    malformed: list[str] = []
    # `:\**` после имени обязателен: в STATUS поле пишут как `- **new_dependency:** x`,
    # то есть закрывающие звёздочки стоят ПОСЛЕ двоеточия. Без них в захват попадало
    # `** httpx …`, именем становилось `**`, и гейт был красным на верно оформленном
    # объявлении — то есть мёртвым (Delivery §4.3b). Форма скопирована с field()
    # в delivery_check.py, где она уже проверена.
    pattern = r"(?im)^[ \t]*[-*]?[ \t]*\**new_dependency\**[ \t]*:\**[ \t]*(.+)$"
    for m in re.finditer(pattern, status):
        val = re.sub(r"<!--.*?-->", "", m.group(1)).strip()
        if not val or val.startswith("<") or val.lower() in {"none", "n/a", "-", "…"}:
            continue
        low = val.lower()
        if "reason=" not in low or "by=" not in low:
            malformed.append(val[:70])
            continue
        ok.add(val.split()[0].strip("`\"',").lower())
    return ok, malformed



def scan_manifests(merge_base: str) -> tuple[list[str], int]:
    """→ (что появилось нового, сколько манифестов проверено).

    Манифест, которого в базе НЕ БЫЛО, даёт одну находку — путь целиком, а не по
    пакету на строку: появление файла это ОДНО решение, иначе первый коммит с
    тридцатью зависимостями требовал бы тридцати строк в STATUS.
    """
    findings: list[str] = []
    checked = 0
    for path in git("ls-files").splitlines():
        fn = extractor_for(path)
        if fn is None:
            continue
        checked += 1
        head_text = git("show", f"HEAD:{path}")
        base_text = git("show", f"{merge_base}:{path}")
        if not base_text.strip():
            if head_text.strip():
                findings.append(path.lower())
            continue
        findings.extend(sorted(fn(head_text) - fn(base_text)))
    return findings, checked


def report(findings: list[str], strict: bool) -> int:
    """Сверка находок с объявлениями в STATUS и починка словами."""
    status = ""
    try:
        with open("delivery/active/STATUS.md", encoding="utf-8") as fh:
            status = fh.read()
    except OSError:
        pass
    ok, malformed = declared(status)

    for bad in malformed:
        print(
            f"ERROR: new_dependency без reason= и/или by=: {bad!r} — упоминание "
            "пакета решением не является",
            file=sys.stderr,
        )
    undeclared = [f for f in findings if f not in ok]
    for name in undeclared:
        print(f"ERROR: новая зависимость не объявлена: {name}", file=sys.stderr)

    if not undeclared and not malformed:
        print(f"new-dependency: объявлено в STATUS — {', '.join(sorted(ok))}")
        return 0

    print(
        "\nПочинка: строка в delivery/active/STATUS.md на каждую новую зависимость:\n"
        "  new_dependency: <pkg> reason=<зачем; что рассмотрели вместо> by=<human:NAME>\n"
        "Это самое долгоживущее решение поставки — оно обязано быть видно в PR\n"
        "(Delivery §4.3a). Не нужна — удали из манифеста, это дешевле, чем потом.",
        file=sys.stderr,
    )
    if not strict:
        print("WARNING (STRICT=0)", file=sys.stderr)
        return 0
    return 1


def main() -> int:
    base = os.environ.get("BASE", "origin/main")
    strict = os.environ.get("STRICT", "1") != "0"
    root = git("rev-parse", "--show-toplevel").strip()
    if root:
        os.chdir(root)

    if not git("rev-parse", "--verify", "--quiet", base).strip():
        # Честный WARNING, а не тишина: тот же приём, что в check_ci_status.sh.
        print(f"WARNING: new-dependency: ref '{base}' недоступен — гейт пропущен")
        return 0

    merge_base = git("merge-base", base, "HEAD").strip() or base
    findings, checked = scan_manifests(merge_base)
    print(f"new-dependency: манифестов проверено {checked}, база {merge_base}")
    if not findings:
        print("new-dependency: OK — новых прямых зависимостей нет")
        return 0
    return report(findings, strict)


if __name__ == "__main__":
    sys.exit(main())
