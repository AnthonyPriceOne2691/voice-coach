# Active delivery status

- **slug:** dependency-gate-after-archiving
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** S
- **kind:** bugfix
- **repro_test:** `backend/tests/test_gate_defects.py::TestDeclarationSurvivesArchiving`
- **diagnosis:** урок L50a в `delivery/archive/INDEX.md` — воспроизведение задокументировано полем
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-15) reason=из двух правок гейтов человек оставил ТОЛЬКО эту (починка невыполнимого требования, §4.3b); вторую — сужение breaker'а объёма на lock-файлы — отклонил: менять поведение проверки там, где это суждение агента, а не исправление лжи, нельзя
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd backend && uv run pytest`
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-gates (ветка fix/gate-defects)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **runtime_paths:** none reason=предмет — скрипт гейта; его отказ виден коду возврата, а не глазу, и проверяется тестами плюс прогоном на живом дереве
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** следующий push после архивации поставки проходит БЕЗ ручного `BASE=HEAD~1`
- **observe_until:** 2026-10-31
  <!-- Перенесено 2026-10-01 с 2026-08-29 решением human:anthony: наблюдение не проведено вовремя, и просрочка с 30.09 блокировала pre-push и job delivery в CI (приёмка 01.10). Сигнал выше не проверен — проверить в использовании и записать observed.md до новой даты. -->
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

`check_new_dependency.py` искал объявления только в `delivery/active/STATUS.md`.
Объявление живёт одну поставку и на handoff уезжает в `archive/` — а окно диффа
(`merge-base origin/main..HEAD`) всё ещё содержит коммит, где зависимость
появилась. Первый push после архивации падал на пакетах, которые час назад были
объявлены и проверены этим же гейтом; обходили руками через `BASE=HEAD~1`.

Расхождение с каноном объявлено в `scripts/lint/adapted.json` и помечено как
кандидат в апстрим: пока правка живёт здесь, её придётся портировать руками при
каждом обновлении канона (CQG §5.5).
