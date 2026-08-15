# Active delivery status

- **slug:** shutdown-summary-oracle
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** S
- **kind:** test-gap
- **repro_test:** `backend/tests/test_shutdown_summary.py` (мутация: снятый `aclose()` роняет оба теста — проверено)
- **diagnosis:** n/a reason=не багфикс; поведение верное, отсутствовал оракул
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** n/a (class S — mini-spec в tasks.md, §2.2)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd backend && uv run pytest`
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-b5 (ветка test/shutdown-summary)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **runtime_paths:** none reason=продуктовый код не меняется вовсе; предмет поставки — тест, и он же оракул
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 0
- **observe_signal:** n/a reason=поставка не меняет поведения; наблюдать нечего
- **observe_until:** n/a
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Последний остаток Phase 2. Пример **B5** («гашение при живой фоновой
суммаризации») с 2026-08-12 стоял с отметкой «НЕ ПРОВЕРЕН машиной — сценарий
требует настоящей LLM в полёте». Требовал он не настоящей, а **управляемой**:
подставной клиент останавливается ровно в середине хода и отпускается по
команде, чего живая модель как раз не умеет.
