#!/usr/bin/env python
"""Разовая чистка банка слов: переводы, которые не по-русски (S-H6).

Поставка `vocab-ru` чинит ИСТОЧНИК — записи, которые появятся дальше. Пять
записей, попавших в банк до неё, этим не лечатся: их правит этот скрипт.

По умолчанию НИЧЕГО не пишет — печатает, что изменилось бы. Запись только с
`--apply`. Удалять записи скрипт не умеет вовсе: удаление — решение человека,
и делается оно с экрана Useful Words.

    python scripts/repair_vocabulary.py            # посмотреть
    python scripts/repair_vocabulary.py --apply    # починить

Чинит ТОЙ ЖЕ функцией, что продуктовый путь (`SummaryService.translate_term`):
второй перевод «почти так же» разъехался бы с первым на первой же правке.
"""

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import Settings  # noqa: E402
from app.container import build_container  # noqa: E402
from app.summary.validate import translation_problem  # noqa: E402


async def repair(apply: bool) -> int:
    container = build_container(Settings())
    entries = await container.vocabulary.list(limit=1000)
    broken = [e for e in entries if translation_problem(e.translation_ru) is not None]
    print(f"записей в банке: {len(entries)}, с негодным переводом: {len(broken)}")
    if not broken:
        return 0

    failed = 0
    for entry in broken:
        problem = translation_problem(entry.translation_ru)
        fixed = await container.summaries.translate_term(
            entry.term_en, example=entry.example_en
        )
        verdict = translation_problem(fixed)
        if verdict is not None:
            print(f"  ✗ {entry.term_en!r}: {entry.translation_ru!r} ({problem}) — "
                  f"починка вернула {fixed!r} ({verdict}); оставлено как есть")
            failed += 1
            continue
        print(f"  {'→' if apply else '?'} {entry.term_en!r}: "
              f"{entry.translation_ru!r} ({problem}) → {fixed!r}")
        if apply and not await container.vocabulary.set_translation(entry.id, fixed):
            print(f"    ! запись {entry.id} исчезла между чтением и записью")
            failed += 1

    if not apply:
        print("\nничего не записано — это dry-run. Повтори с --apply")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="записать починенные переводы")
    return asyncio.run(repair(parser.parse_args().apply))


if __name__ == "__main__":
    raise SystemExit(main())
