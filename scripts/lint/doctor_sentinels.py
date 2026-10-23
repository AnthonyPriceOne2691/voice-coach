#!/usr/bin/env python3
"""Стражи исполнения подключены ли: pytest грузит плагин, и mutmut его найдёт.

Часть доктора (`cqg@2.72`, вход — `contour_doctor.py`). Плагин `run_sentinels.py`
держит три строки §2 только там, где pytest его ГРУЗИТ: файл без строки в конфиге —
рецепт, а не механика. Так фикстура пула и прожила до `cqg@2.72`: §2.9 числил её
«инструментом в CI», а поставили её 0 из 4 python-проектов флота (замер 21.10).

Три вопроса, все про НАСТРОЙКУ: есть ли конфиг pytest; грузит ли он плагин; находит
ли его `pythonpath` — и из `mutants/` тоже, если проект гоняет mutmut: копия конфига
лежит на уровень глубже, и без второго пути mutmut падает импортом (замер 21.10,
mutmut 3.7: «No module named 'run_sentinels'» — мутационный гейт ломался целиком).
"""

from __future__ import annotations

import os
import re

from doctor_core import AUTO, SKIP, WEAK

PLUGIN = "run_sentinels"
#: Конфиг pytest: раскладка канона (`backend/`) и плоская.
PYPROJECTS = ("backend/pyproject.toml", "pyproject.toml")


class SentinelChecks:
    def _pytest_options(self) -> tuple[str, dict, bool] | None:
        """(путь конфига, `[tool.pytest.ini_options]`, гоняет ли mutmut) — или None."""
        try:
            import tomllib
        except ImportError:  # silent-ok: python<3.11 — вызывающий скажет SKIP
            return None
        for rel in PYPROJECTS:
            path = self.root / rel
            if not path.is_file():
                continue
            try:
                tool = tomllib.loads(path.read_text(encoding="utf-8")).get("tool", {})
            except (tomllib.TOMLDecodeError, UnicodeDecodeError):
                continue
            if "ini_options" in tool.get("pytest", {}):
                return rel, tool["pytest"]["ini_options"], "mutmut" in tool
        return None

    def check_run_sentinels(self) -> None:
        point = "стражи исполнения"
        if not (self.root / "scripts/lint" / f"{PLUGIN}.py").is_file():
            self.add(SKIP, point, "плагина нет в дереве — развёрнут ли он, скажет состав")
            return
        found = self._pytest_options()
        if found is None:
            self.add(SKIP, point, "конфиг pytest не найден или не прочитан (python<3.11) — "
                                  "грузит ли pytest плагин, не проверено")
            return
        rel, opts, mutmut = found
        addopts = opts.get("addopts", [])
        line = " ".join(addopts) if isinstance(addopts, list) else str(addopts)
        if not re.search(rf"-p\s*{PLUGIN}\b", line):
            self.add(WEAK, point, f"{rel}: pytest плагин не грузит (нет `-p {PLUGIN}` в "
                                  "addopts) — текст в логах, секреты и пул не держит никто, §2.7c")
            return
        self._judge_plugin_path(point, rel, opts.get("pythonpath", []), mutmut)

    def _judge_plugin_path(self, point: str, rel: str, paths, mutmut: bool) -> None:
        """Плагин обязан находиться из каталога конфига — и из `mutants/`, если mutmut."""
        paths = [paths] if isinstance(paths, str) else list(paths)
        base = os.path.dirname(rel)

        def finds(start: str) -> bool:
            return any((self.root / os.path.normpath(os.path.join(start, p, f"{PLUGIN}.py"))
                        ).is_file() for p in paths)

        if not finds(base):
            self.add(WEAK, point, f"{rel}: `-p {PLUGIN}` есть, а `pythonpath` его не находит "
                                  "— pytest упадёт импортом")
        elif mutmut and not finds(os.path.join(base, "mutants")):
            self.add(WEAK, point, f"{rel}: из `mutants/` плагин не найти — mutmut упадёт "
                                  "импортом; добавь в pythonpath путь на уровень глубже (§2.7c)")
        else:
            self.add(AUTO, point, f"{rel}: pytest грузит плагин"
                                  + (", mutmut его найдёт" if mutmut else ""))
