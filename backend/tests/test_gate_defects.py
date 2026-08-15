"""Гейт зависимостей после архивации поставки (урок L50a).

Гейт требовал невыполнимого: объявление живёт в `delivery/active/STATUS.md`, на
handoff уезжает в `archive/` вместе с поставкой, а окно диффа всё ещё содержит
коммит, где зависимость появилась. Первый же push ПОСЛЕ архивации падал на
пакетах, которые час назад были объявлены и проверены этим же гейтом.

Второй дефект того же класса (breaker объёма считает сгенерированные lock-файлы,
урок L48) **сознательно НЕ чинится**: решение человека 2026-08-15 — не менять
поведение проверок там, где это суждение, а не починка лжи. Он остаётся долгом и
кандидатом в апстрим-канон.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"


def _load(path: Path, name: str) -> ModuleType:
    """Скрипты контура лежат вне пакета — грузим по пути, как их грузит CI."""
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Регистрация ДО exec обязательна: модуль тянет dataclass'ы, а они на
    # разборе аннотаций лезут в `sys.modules[cls.__module__]`. Без строки ниже
    # тест падает не на своём предмете, а на устройстве загрузки.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def new_dependency() -> ModuleType:
    return _load(SCRIPTS / "lint" / "check_new_dependency.py", "check_new_dependency")


class TestDeclarationSurvivesArchiving:
    """L50a: объявление уезжает в archive вместе с поставкой, а окно диффа — нет."""

    def test_archived_status_of_this_window_counts(
        self, new_dependency: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        archived = tmp_path / "delivery" / "archive" / "2026-08-15-x"
        archived.mkdir(parents=True)
        (archived / "STATUS.md").write_text(
            "- **new_dependency:** jsdom reason=нужен DOM by=human:anthony\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            new_dependency,
            "git",
            lambda *a: "delivery/archive/2026-08-15-x/STATUS.md\n",
        )

        assert new_dependency.report(["jsdom"], True, "base..HEAD") == 0

    def test_archived_status_outside_the_window_does_not(
        self, new_dependency: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Иначе прошлогоднее объявление молча оправдывало бы сегодняшний пакет."""
        old = tmp_path / "delivery" / "archive" / "2026-01-01-old"
        old.mkdir(parents=True)
        (old / "STATUS.md").write_text(
            "- **new_dependency:** jsdom reason=когда-то by=human:anthony\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(new_dependency, "git", lambda *a: "")  # окно пустое

        assert new_dependency.report(["jsdom"], True, "base..HEAD") == 1


def test_gate_scripts_still_run_on_this_repo() -> None:
    """Мета-проверка: правка не сломала запуск самого гейта на живом дереве."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "lint" / "check_new_dependency.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "BASE": "HEAD"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
