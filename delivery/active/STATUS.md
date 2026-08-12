# Active delivery status

- **slug:** ci-runs-delivery-check
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** S
- **kind:** bugfix
- **repro_test:** n/a reason=предмет — условие в YAML workflow; оракул здесь прогон самой джобы на ветке без активной поставки, а не unit-тест (§3.1c)
- **diagnosis:** n/a reason=причина найдена сразу и однозначна — `if [ -f delivery/active/STATUS.md ]` в quality.yml; гипотез не перебиралось
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** process:ci
- **human_ok_spec:** n/a
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=правка workflow; собранного артефакта не касается
- **ci-oracles:** tooling
- **worktree:** none (S)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=правка условия в существующей джобе
- **runtime_paths:** .github/workflows/quality.yml
  <!-- §12.6: конфиг CI — путь, чей отказ не виден ни сборке, ни тестам:
       пропущенная джоба выглядит как зелёная. Проверяется прогоном самой
       джобы в обоих состояниях, а не чтением YAML. -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** на `main` без активной поставки джоба `quality / delivery`
  печатает вывод `delivery_check` (строку `idle:`), а не `no active delivery — skip`
- **observe_until:** 2026-08-26
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
