# Tasks — contour-bootstrap-1.61

- [x] Замер ДО (`contour_doctor.py`, инвентарь sha256 по 21 скрипту)
- [x] `phase-2-acceptance` → `archive/2026-07-28-phase-2-acceptance` + пометка «не закрыта»
- [x] `archive/INDEX.md` с уроком L1 («CI красный» — не одно состояние)
- [x] STATUS новой поставки, `kind: bootstrap`
- [x] 21 скрипт + `scripts/stack_selftest.py`
- [x] `docs/canon/` и `Prepare/` + `SHA256SUMS` переснят
- [x] `.pre-commit-config.yaml`: канон дословно + `canon-vendor`/`smoke-evals` поверх
- [x] `pyproject`: шесть bandit-правил возвращены, пять комплексити в ignore, `norecursedirs`, `[tool.mutmut]`
- [x] инструменты в манифест `dev`, `uv sync`, объявления `new_dependency`
- [x] снимки: 6 grep + 4 ast + complexity + file_length + deps-audit
- [x] `S311` закрыт подавлением с причиной на строке
- [x] `npm audit fix` (два high), эскалация по `vitest` semver-major
- [x] env вшит в 22 `entry:` — гейты не зависят от шелла
- [x] baseline секретов по отслеживаемым файлам (не `--all-files`)
- [x] 28 хуков при чистом env, 91 тест, 93.51%
- [ ] `agent-permissions` в CONSTITUTION (WARNING `delivery_check`)
- [ ] мерж в main через `merge_guard.sh` — ПОКА bootstrap активен (§7.2 шаг 6)
