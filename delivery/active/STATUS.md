# Active delivery status

- **slug:** vocab-ru
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** bugfix
- **repro_test:** `backend/tests/test_summary.py::test_cjk_leak_in_translation_is_caught` (V1, из живой записи банка)
- **diagnosis:** `delivery/active/diagnosis.md`
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-15) reason=спека утверждена; отдельно выбрана ПОЧИНКА вместо простого отбрасывания записи и заказана разовая чистка пяти записей, уже лежащих в банке
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd backend && uv run pytest`
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-vocab (ветка fix/vocab-ru)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **runtime_paths:** none reason=предмет поставки — чистая функция проверки и один вызов LLM в офлайн-пути; оба закрываются тестами на подставном клиенте, экрана и железа поставка не трогает
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** после следующего полного разбора в банке слов нет ни одной
  записи с иероглифами; если починка срабатывала — в логе видно, какой термин
- **observe_until:** 2026-08-29
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

`translation_ru` не проверяет **ничто**: `S-H2_en_body` это поле явно исключает,
`S-H4` смотрит только непустоту. В банке слов из-за этого лежит
`выразительный陳述` — утечка китайского у `deepseek-r1:14b`. Поставка закрывает
дыру инвариантом `S-H6`, чинит запись повторным переводом на qwen2.5 и теряет её
только вслух.
