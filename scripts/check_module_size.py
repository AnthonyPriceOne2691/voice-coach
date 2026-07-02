#!/usr/bin/env python3
"""Fail if any production source file exceeds the LOC limit.

Usage:
    python scripts/check_module_size.py
    python scripts/check_module_size.py --max-lines 500 --strict-blanks

See docs/18-engineering-standards.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_MAX_LINES = 500
DEFAULT_ROOTS = (
    ("backend/app", {".py"}),
    ("frontend/src", {".ts", ".tsx"}),
)
SKIP_DIR_NAMES = {"__pycache__", "node_modules", ".git", "dist", "build"}


def count_lines(path: Path, *, strict_blanks: bool) -> int:
    text = path.read_text(encoding="utf-8")
    if not strict_blanks:
        return len(text.splitlines())
    return sum(
        1
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def iter_source_files(root: Path, suffixes: set[str]) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in suffixes:
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def check(
    repo_root: Path,
    *,
    max_lines: int,
    strict_blanks: bool,
) -> list[tuple[Path, int]]:
    violations: list[tuple[Path, int]] = []
    for rel_root, suffixes in DEFAULT_ROOTS:
        for path in iter_source_files(repo_root / rel_root, suffixes):
            line_count = count_lines(path, strict_blanks=strict_blanks)
            if line_count > max_lines:
                violations.append((path, line_count))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce per-file LOC limit.")
    parser.add_argument(
        "--max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help=f"Maximum lines per file (default: {DEFAULT_MAX_LINES})",
    )
    parser.add_argument(
        "--strict-blanks",
        action="store_true",
        help="Exclude blank lines and Python comment-only lines from count",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: voice-interview-coach/)",
    )
    args = parser.parse_args()

    violations = check(
        args.repo_root,
        max_lines=args.max_lines,
        strict_blanks=args.strict_blanks,
    )

    if not violations:
        mode = "strict" if args.strict_blanks else "all lines"
        print(f"OK: all files <= {args.max_lines} LOC ({mode})")
        return 0

    print(f"FAIL: {len(violations)} file(s) exceed {args.max_lines} LOC:\n")
    for path, count in violations:
        rel = path.relative_to(args.repo_root)
        print(f"  {rel}: {count} lines")
    return 1


if __name__ == "__main__":
    sys.exit(main())
