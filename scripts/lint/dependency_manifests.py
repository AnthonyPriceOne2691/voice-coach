#!/usr/bin/env python3
"""Разбор манифестов: какие ПРЯМЫЕ зависимости объявлены в файле.

Часть `check_new_dependency.py` (`cqg@1.83`) — гейт разрезан по планке 300 строк
(Delivery §9.1a п.5). Здесь только чтение форматов: по одной функции на экосистему
плюс выбор нужной по имени файла. Гейт (что считать новым и как об этом отчитаться)
остался во входном скрипте.

Лок-файлы сознательно не разбираются: они перечисляют ТРАНЗИТИВНЫЕ пакеты, и
решение «взяли новую зависимость» там утонет в шуме обновлений.
"""

from __future__ import annotations

import json
import re

LOCKFILES = (
    "poetry.lock",
    "package-lock.json",
    "Cargo.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Gemfile.lock",
    "uv.lock",
)


def _toml(text: str):
    """dict или None. None = нет tomllib (python<3.11) либо TOML не парсится."""
    try:
        import tomllib
    except ImportError:
        return None
    try:
        return tomllib.loads(text)
    except Exception:  # noqa: BLE001  # silent-ok: битый TOML — ниже фолбэк на regex
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




def _names_from_specs(specs) -> set[str]:
    """`["httpx>=0.27", …]` → `{"httpx", …}`. `None` и пустое — пустое множество."""
    return {_req_name(str(spec)) for spec in (specs or [])}


def _table_names(table) -> set[str]:
    """Имена КЛЮЧЕЙ таблицы зависимостей (форма poetry). `None` — пустое."""
    return {name.lower() for name in (table or {})}


def _pep621_names(data: dict) -> set[str]:
    """PEP 621: `[project]` + optional-dependencies + PEP 735 dependency-groups."""
    proj = data.get("project") or {}
    out = _names_from_specs(proj.get("dependencies"))
    for group in (proj.get("optional-dependencies") or {}).values():
        out |= _names_from_specs(group)
    for group in (data.get("dependency-groups") or {}).values():
        # PEP 735 разрешает в группе не только строки, но и `{include-group: …}`:
        # это ссылка на другую группу, а не зависимость, и имени в ней нет.
        out |= _names_from_specs(s for s in (group or []) if isinstance(s, str))
    return out


def _poetry_names(data: dict) -> set[str]:
    """`[tool.poetry]`: dependencies, dev-dependencies и именованные группы."""
    poetry = (data.get("tool") or {}).get("poetry") or {}
    out = _table_names(poetry.get("dependencies")) | _table_names(poetry.get("dev-dependencies"))
    for group in (poetry.get("group") or {}).values():
        out |= _table_names((group or {}).get("dependencies"))
    return out


def names_pyproject(text: str) -> set[str]:
    """Обе раскладки разом: PEP 621 и poetry живут в одном файле и обе законны.

    Разобрано на две функции (`cqg@1.83`): вместе это была самая ветвистая функция
    контура при двадцати двух строках — читать её приходилось целиком, чтобы
    понять, какая половина форматов сейчас важна.
    """
    data = _toml(text)
    if data is None:
        return _toml_dep_names_fallback(text)
    out = _pep621_names(data) | _poetry_names(data)
    out.discard("python")  # требование к рантайму, а не зависимость
    return {n for n in out if n}


def _cargo_section_names(table) -> set[str]:
    """Имена зависимостей из трёх секций ОДНОЙ таблицы Cargo.toml.

    Шов по сложности, а не по длине: те же три секции читаются и в корне
    манифеста, и в каждой `[target.*]`, и каждое чтение стоило ветвления —
    одиннадцать при пороге десять. Наружу выборка отдаёт одно множество имён.
    """
    return {n.lower()
            for key in ("dependencies", "dev-dependencies", "build-dependencies")
            for n in ((table or {}).get(key) or {})}


def names_cargo(text: str) -> set[str]:
    data = _toml(text)
    if data is None:
        return _toml_dep_names_fallback(text)
    out = _cargo_section_names(data)
    for target in (data.get("target") or {}).values():
        out |= _cargo_section_names(target)
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

