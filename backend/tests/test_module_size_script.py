"""Smoke test for the LOC gate script (meta-check)."""

import subprocess
import sys

from app.config import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "check_module_size.py"


def test_check_module_size_passes_on_current_tree() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
