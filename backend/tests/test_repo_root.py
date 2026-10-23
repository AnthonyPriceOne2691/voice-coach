"""Корень репозитория узнаётся по данным, а не по глубине пути (M1–M4).

Мутационный гейт копирует пакет в `backend/mutants/app/` и гоняет сьют оттуда.
Счёт `parents[2]` давал там `backend/`: сьют не находил `data/contracts`, и гейт
не просудил ни одного мутанта (замер 2026-10-23). Раскладки строятся в `tmp_path`;
настоящий каталог `mutants/` тест не трогает.
"""

import importlib.util
import shutil
from pathlib import Path
from types import ModuleType

import pytest

from app.config import REPO_ROOT, RepoRootNotFoundError, Settings, find_repo_root


def _with_data(root: Path, *markers: str) -> Path:
    for name in markers:
        (root / "data" / name).mkdir(parents=True)
    return root


def _file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
    return path


def test_real_layout_resolves_to_the_repo_with_data() -> None:
    """M1: из настоящего `backend/app/config.py` — корень, где лежат данные приложения."""
    assert (REPO_ROOT / "data" / "prompts").is_dir()
    assert (REPO_ROOT / "data" / "contracts").is_dir()
    assert (REPO_ROOT / "backend" / "app" / "config.py").is_file()
    assert Settings.model_fields["contracts_dir"].default == REPO_ROOT / "data" / "contracts"


def _import_copy(source: Path, copy: Path) -> ModuleType:
    """Исполнить копию модуля так, как её исполнил бы сьют внутри `mutants/`."""
    copy.parent.mkdir(parents=True)
    shutil.copyfile(source, copy)
    spec = importlib.util.spec_from_file_location("config_copy", copy)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mutants_copy_resolves_to_the_same_root(tmp_path: Path) -> None:
    """M2: `config.py`, разложенный как у mutmut (`backend/mutants/app/`), видит тот же корень.

    Копируется настоящий исходник, а не вызывается функция: сломался именно
    модульный `REPO_ROOT`, и проверять надо его. На `parents[2]` тест красный —
    корнем выходит `backend/`.
    """
    repo = _with_data(tmp_path / "repo", "prompts", "contracts")
    source = REPO_ROOT / "backend" / "app" / "config.py"
    plain = _import_copy(source, repo / "backend" / "app" / "config.py")
    mutant = _import_copy(source, repo / "backend" / "mutants" / "app" / "config.py")
    assert repo.resolve() == plain.REPO_ROOT
    assert repo.resolve() == mutant.REPO_ROOT


def test_worktree_inside_the_repo_reads_its_own_data(tmp_path: Path) -> None:
    """M3: данные есть и у worktree, и у основного клона — побеждает ближайший."""
    repo = _with_data(tmp_path / "repo", "prompts", "contracts")
    worktree = _with_data(repo / ".claude" / "worktrees" / "agent-x", "prompts", "contracts")
    config = _file(worktree / "backend" / "app" / "config.py")
    assert find_repo_root(config) == worktree.resolve()


@pytest.mark.parametrize("markers", [(), ("prompts",), ("contracts",)])
def test_missing_data_is_a_named_error(tmp_path: Path, markers: tuple[str, ...]) -> None:
    """M4: нет хотя бы одного из двух каталогов — ошибка с путём старта и именами обоих."""
    _with_data(tmp_path, *markers)
    config = _file(tmp_path / "backend" / "app" / "config.py")
    with pytest.raises(RepoRootNotFoundError) as caught:
        find_repo_root(config)
    message = str(caught.value)
    assert str(config) in message
    assert "data/prompts и data/contracts" in message
