# Active delivery status

- **slug:** history-end-time
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** bugfix
- **repro_test:** frontend/src/lib/format.test.ts::формат строки History отличает закрытую сессию от брошенной
- **diagnosis:** active/diagnosis.md
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-12) reason=примеры D1–D5 предъявлены ДО кода с тремя оговорками: модель состояний не меняется (status остаётся in_progress), duration_sec не трогается, стенд в CI не ставится
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build` — правка фронта, собранное меняется (§6.5a)
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-ui (ветка fix/history-end-time)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=правка отображения и перенос уже написанного стенда; новых пакетов не требуется
- **runtime_paths:** delivery/evals/browser/
  <!-- §12.6: браузерный стенд — путь, чей отказ не виден ни сборке, ни тестам.
       Он сам исполняется вручную и в CI не гоняется (нужны Chromium, модели,
       ollama). Значит проверяется прогоном, а не чтением. -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** D1–D4 подтверждены; в History у сессии, закрытой разрывом,
  видно время окончания, а у брошенной — явная отметка вместо длительности
- **observe_until:** 2026-10-31
  <!-- Перенесено 2026-10-01 с 2026-08-26 решением human:anthony: наблюдение не проведено вовремя, и просрочка с 30.09 блокировала pre-push и job delivery в CI (приёмка 01.10). Сигнал выше не проверен — проверить в использовании и записать observed.md до новой даты. -->
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Два хвоста прошлых поставок, связанных одним предметом: **чем проверяется
приёмка UI и что она показывает**.

1. `HistoryPage` не показывает `ended_at` вовсе — только дату начала и
   длительность. А `duration_sec` берётся из метаданных последнего flush'а, то
   есть заполнен и у сессии, которую бросили. По списку History закрытую сессию
   от брошенной **не отличить** — это и оставило пример B6 прошлой поставки
   проверенным наполовину.
2. Браузерный стенд, которым найдены три дефекта при зелёном сьюте, живёт в
   scratchpad сессии и умирает вместе с ней.
