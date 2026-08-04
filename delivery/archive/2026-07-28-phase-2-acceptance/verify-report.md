# Verify report

**Date:** YYYY-MM-DD
**Verifier:** human:anthony
<!-- Должен отличаться от `builder:` в STATUS (§5.2). Builder — agent:claude-code. -->

**Пусто до фазы verify.**

## Shape oracles
- [ ] PASS/FAIL — pre-commit run --all-files

## Behavior oracles
- [ ] PASS/FAIL — ./scripts/run_checks.sh (pytest, coverage ≥ 85)
- [ ] PASS/FAIL — frontend: npm run build && npm test
- [ ] PASS/FAIL — check_diff_coverage.sh

## Product oracles
- [ ] PASS/FAIL — delivery/evals/smoke/run.sh
- [ ] PASS/FAIL — active/eval-smoke acceptance (ручной прогон, живые AI)

## Spec coverage gaps
- …

## Verdict
- [ ] READY FOR HANDOFF
- [ ] NEED CONVERGE (new tasks)
- [ ] BLOCKED
