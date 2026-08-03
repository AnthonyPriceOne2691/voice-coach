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

import json
import os
import re
import subprocess
import sys

LOCKFILES = (
    "poetry.lock",
    "package-lock.json",
    "Cargo.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Gemfile.lock",
    "uv.lock",
)


def git(*args: str) -> str:
    """git с подавлением ошибок: пустая строка = не смог (файла нет в ревизии)."""
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    return out.stdout if out.returncode == 0 else ""


def _toml(text: str):
    """dict или None. None = нет tomllib (python<3.11) либо TOML не парсится."""
    try:
        import tomllib
    except ImportError:
        return None
    try:
        return tomllib.loads(text)
    except Exception:  # noqa: BLE001 -- битый TOML: пусть работает фолбэк
        return None


def _req_name(spec: str) -> str:
    """'requests[socks] >= 2.0 ; python_version<"3.9"' -> 'requests'."""
    head = spec.split(";")[0].strip()
    m = re.match(r"[A-Za-z0-9._-]+", head)
    return m.group(0).lower() if m else ""


def _toml_dep_names_fallback(text: str) -> set[str]:
    """Без tomllib: только участки, относящиеся к зависимостям.

    Сканировать весь файл нельзя: `name = "..."` в [project] попал бы в набор и
    добавление любого поля метаданных читалось бы как новая зависимость.
    """
    out: set[str] = set()
    in_dep_table = False
    in_dep_array = False
    for raw in text.splitlines():
        line = raw.split("#")[0].strip()
        if line.startswith("["):
            in_dep_table = "dependencies" in line
            in_dep_array = False
            continue
        if re.match(r"^(optional-)?dependencies\s*=", line):
            in_dep_array = "]" not in line
            for m in re.finditer(r'["\']([A-Za-z0-9._-]+)', line):
                out.add(m.group(1).lower())
            continue
        if in_dep_array:
            for m in re.finditer(r'["\']([A-Za-z0-9._-]+)', line):
                out.add(m.group(1).lower())
            if "]" in line:
                in_dep_array = False
            continue
        if in_dep_table:
            m = re.match(r"^([A-Za-z0-9._-]+)\s*=", line)
            if m:
                out.add(m.group(1).lower())
    return out


def names_pyproject(text: str) -> set[str]:
    data = _toml(text)
    if data is None:
        return _toml_dep_names_fallback(text)
    out: set[str] = set()
    proj = data.get("project") or {}
    for spec in proj.get("dependencies") or []:
        out.add(_req_name(str(spec)))
    for group in (proj.get("optional-dependencies") or {}).values():
        for spec in group or []:
            out.add(_req_name(str(spec)))
    for group in (data.get("dependency-groups") or {}).values():
        for spec in group or []:
            if isinstance(spec, str):
                out.add(_req_name(spec))
    poetry = (data.get("tool") or {}).get("poetry") or {}
    for key in ("dependencies", "dev-dependencies"):
        out.update(n.lower() for n in (poetry.get(key) or {}))
    for group in (poetry.get("group") or {}).values():
        out.update(n.lower() for n in ((group or {}).get("dependencies") or {}))
    out.discard("python")  # требование к рантайму, а не зависимость
    return {n for n in out if n}


def names_cargo(text: str) -> set[str]:
    data = _toml(text)
    if data is None:
        return _toml_dep_names_fallback(text)
    out: set[str] = set()
    for key in ("dependencies", "dev-dependencies", "build-dependencies"):
        out.update(n.lower() for n in (data.get(key) or {}))
    for target in (data.get("target") or {}).values():
        for key in ("dependencies", "dev-dependencies", "build-dependencies"):
            out.update(n.lower() for n in ((target or {}).get(key) or {}))
    return out


def names_package_json(text: str) -> set[str]:
    try:
        data = json.loads(text)
    except ValueError:
        return set()
    out: set[str] = set()
    for key in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        section = data.get(key)
        if isinstance(section, dict):
            out.update(n.lower() for n in section)
    return out


def names_requirements(text: str) -> set[str]:
    out: set[str] = set()
    for raw in text.splitlines():
        line = raw.split("#")[0].strip()
        if not line or line.startswith("-"):  # -r / -e / --index-url
            continue
        name = _req_name(line)
        if name:
            out.add(name)
    return out


def names_go_mod(text: str) -> set[str]:
    out: set[str] = set()
    block = False
    for raw in text.splitlines():
        line = raw.split("//")[0].strip()
        if line.startswith("require") and line.endswith("("):
            block = True
            continue
        if block:
            if line == ")":
                block = False
            elif line:
                out.add(line.split()[0].lower())
            continue
        if line.startswith("require "):
            rest = line[len("require ") :].split()
            if rest:
                out.add(rest[0].lower())
    return out


def names_swift(text: str) -> set[str]:
    out: set[str] = set()
    for m in re.finditer(
        r'\.package\s*\(\s*(?:name:\s*"([^"]+)"|url:\s*"([^"]+)")', text
    ):
        name = m.group(1) or (m.group(2) or "").rstrip("/").rsplit("/", 1)[-1]
        if name.endswith(".git"):
            name = name[:-4]
        if name:
            out.add(name.lower())
    return out


EXTRACTORS = (
    ("pyproject.toml", names_pyproject),
    ("Cargo.toml", names_cargo),
    ("package.json", names_package_json),
    ("go.mod", names_go_mod),
    ("Package.swift", names_swift),
)


def extractor_for(path: str):
    base = path.rsplit("/", 1)[-1]
    if base in LOCKFILES:
        return None
    for name, fn in EXTRACTORS:
        if base == name:
            return fn
    if base.startswith("requirements") and base.endswith(".txt"):
        return names_requirements
    return None


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
            # Манифеста не было: это ОДНО решение, а не N. Иначе первый коммит с
            # тридцатью зависимостями требовал бы тридцати строк в STATUS.
            if head_text.strip():
                findings.append(path.lower())
            continue
        for name in sorted(fn(head_text) - fn(base_text)):
            findings.append(name)

    print(f"new-dependency: манифестов проверено {checked}, база {merge_base}")
    if not findings:
        print("new-dependency: OK — новых прямых зависимостей нет")
        return 0

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


if __name__ == "__main__":
    sys.exit(main())