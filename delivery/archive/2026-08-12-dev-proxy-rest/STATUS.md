# Active delivery status

- **slug:** dev-proxy-rest
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** bugfix
- **repro_test:** frontend/src/lib/api.test.ts::dev-proxy покрывает все префиксы api.ts
- **diagnosis:** active/diagnosis.md
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-12) reason=примеры C1–C6 предъявлены ДО кода вместе с тремя оговорками: правка шире одной строки намеренно (сторож + громкая ошибка), правится строка канона doc 15, из прокси убирается неиспользуемое правило /api
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build` — правка касается конфига сборщика, поэтому собранное этой поставкой обязано проверяться (§6.5a)
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-proxy (ветка fix/dev-proxy)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none reason=escalation.md разрешён человеком в пользу варианта B (drift-waiver ниже); файл оставлен в поставке как запись о том, как решение принималось
- **waivers:** none
- **new_dependency:** none reason=правка конфига и одна проверка в существующем клиенте; новых пакетов не требуется
- **runtime_paths:** frontend/vite.config.ts
  <!-- §12.6: конфиг dev-сервера — путь, чей отказ не виден ни сборке, ни
       тестам: сборка зелёная, юнит-тесты зелёные, а в браузере две вкладки
       мертвы. Ровно так дефект и прожил незамеченным. Проверяется исполнением
       в настоящем браузере, не рассуждением. -->
- **canon_drift_waiver:** reason=таяние долга задело три концепта, но ни один инвариант не изменился и это проверяется диффом: в llm/ollama_client.py (model-split) — только комментарии и пометка `# cpu-ok` на строке json.loads, модели и разбор стрима не тронуты; в orchestrator/interview.py (orchestrator-owns-structure) — одна строка raise получила контекст, логика выбора вопросов та же; в contracts/enforcer.py (sentence-streaming) — if/elif заменён таблицей методов без единого изменённого условия, per-sentence семантика прежняя, тесты контрактов держат 100%. Правка самих концептов была бы ложным «обновлено» by=human:anthony at=2026-08-12
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** C1–C4 подтверждены; в браузере вкладки History и Useful
  Words показывают данные, а не «Failed to load»
- **observe_until:** 2026-08-26
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

History и Useful Words не работают в единственном поддерживаемом запуске
(`./scripts/dev.sh`). Найдено ручным прогоном в браузере 2026-08-12 —
им же, что нашёл предыдущий дефект.

Корень — **противоречие внутри канона**: doc 15 в строке Base URLs обещает
`proxy /api, /ws`, а ниже перечисляет эндпоинты как `/sessions/...` и
`/vocabulary/...`. Код пошёл за списком эндпоинтов, `vite.config.ts` — за
строкой про прокси. Поэтому правится не только конфиг, но и doc 15.
