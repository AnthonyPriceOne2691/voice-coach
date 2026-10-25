"""Гейт на стадии `manual` обязан исполняться в CI (поставка deps-refresh, V2, V3).

`deps-audit` стоял в `.pre-commit-config.yaml` со `stages: [manual]` с самого
развёртывания контура: по бюджету pre-push (CQG §8.6) он CI-only, а шага в
`quality.yml` не было. `check_gate_coverage.sh` стадий не читает и считал гейт
подключённым — гейт молчал при critical=2 high=6, и сказать об этом было некому.

Сторож на класс, а не на случай: у КАЖДОГО хука, который стоит только на стадии
`manual`, есть шаг CI, зовущий тот же скрипт, и стоит этот шаг с `if: always()` —
иначе упавший шаг выше уносит гейт из прогона молча (Delivery §3.1a).
"""

import re
from typing import Any

import pytest
import yaml

from app.config import REPO_ROOT

PRE_COMMIT = REPO_ROOT / ".pre-commit-config.yaml"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SCRIPT_RE = re.compile(r"scripts/[\w./-]+\.(?:sh|py)")
DEPS_AUDIT = "scripts/lint/check_deps_audit.sh"

Step = dict[str, Any]


def _manual_only_hooks() -> dict[str, list[str]]:
    """id хука → скрипты из его `entry` — для хуков, которые стоят ТОЛЬКО на `manual`."""
    config = yaml.safe_load(PRE_COMMIT.read_text(encoding="utf-8"))
    default = config.get("default_stages", [])
    hooks: dict[str, list[str]] = {}
    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            if set(hook.get("stages", default)) == {"manual"}:
                hooks[hook["id"]] = SCRIPT_RE.findall(str(hook.get("entry", "")))
    return hooks


def _ci_steps() -> list[tuple[str, str, Step]]:
    """(файл workflow, джоба, шаг) — каждый шаг с `run:` во всех workflow."""
    found: list[tuple[str, str, Step]] = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        data = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
        for job_name, job in (data.get("jobs") or {}).items():
            found.extend(
                (workflow.name, job_name, step) for step in job.get("steps") or [] if "run" in step
            )
    return found


def _runs_always(step: Step) -> bool:
    return "always()" in str(step.get("if", ""))


MANUAL_HOOKS = _manual_only_hooks()


def test_deps_audit_runs_in_quality_gates_job() -> None:
    """V2: аудит зависимостей — шаг джобы `gates`, и упавший сосед его не уносит."""
    steps = [
        step
        for workflow, job, step in _ci_steps()
        if (workflow, job) == ("quality.yml", "gates") and DEPS_AUDIT in str(step["run"])
    ]
    assert steps, f"в джобе gates (quality.yml) нет шага, зовущего {DEPS_AUDIT}"
    assert any(_runs_always(step) for step in steps), "шаг аудита без if: always()"


def test_manual_sweep_is_not_blind() -> None:
    """V3: сторож судит не пустоту — хук `deps-audit` виден ему как manual-only."""
    assert MANUAL_HOOKS.get("deps-audit") == [DEPS_AUDIT]


@pytest.mark.parametrize("hook_id", sorted(MANUAL_HOOKS))
def test_manual_only_hook_runs_in_ci(hook_id: str) -> None:
    """V3: хук только на стадии `manual` исполняется шагом CI с `if: always()`."""
    scripts = MANUAL_HOOKS[hook_id]
    assert scripts, f"{hook_id}: в entry нет пути scripts/… — искать в CI нечего"
    for script in scripts:
        steps = [step for _, _, step in _ci_steps() if script in str(step["run"])]
        assert steps, f"{hook_id}: {script} не зовёт ни один шаг CI — гейт не исполняется нигде"
        assert any(_runs_always(step) for step in steps), (
            f"{hook_id}: шаг CI с {script} без if: always() — упавший шаг выше унесёт его молча"
        )
