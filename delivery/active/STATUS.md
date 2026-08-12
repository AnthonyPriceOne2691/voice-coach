# Active delivery status

- **slug:** ws-disconnect-hang
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** bugfix
- **repro_test:** backend/tests/test_ws_voice.py::test_disconnect_without_end_session_finishes_flow
- **diagnosis:** active/diagnosis.md
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-12) reason=примеры B1–B5 предъявлены человеку целиком, вместе с двумя оговорками: B5 без машинного оракула и B1 с намеренно противоречивой парой `in_progress` + непустой `ended_at`. Подпись дана на handoff, а не до implement (§2.2b): спека написана по факту воспроизведения
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=фронт не тронут ни одной строкой; собранное этой поставкой не меняется (§6.5a)
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-ws-fix (ветка fix/ws-disconnect)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=починка укладывается в стандартную библиотеку (asyncio.shield/wait) и уже установленные пакеты
- **runtime_paths:** backend/app/api/ws_voice.py,backend/app/main.py
  <!-- §12.6: путь завершения ws-сессии и гашение приложения — ровно тот класс,
       где отказ виден только на целевой среде: на macOS 0 из 60, на linux 6 из
       10. Поэтому исполнялся, а не обсуждался: прогоны в linux-контейнере до и
       после фикса, см. verify-report → «Исполнение рисковых путей». -->
- **breaker_override:** `max_runtime_paths=2` reason=деление проверено исполнением, а не оценено: три варианта дерева × 10 прогонов в linux-контейнере дали 0 зелёных из 10 у ОБЕИХ половин (только ws_voice.py — 10 красных на B1, `ended_at` = None; только main.py — 7 висов, хуже исходных 6). Пути связаны одним проводом `live_ws_cleanups`: ws_voice.py пишет, main.py читает — порознь это два конца одной правки, и «по одной» означало бы смержить в main заведомо нерабочую половину с живым висом. Перебор, от которого бережёт §12.6, выполнен ДО мержа и записан таблицей в verify-report by=human:anthony at=2026-08-12
- **canon_drift_waiver:** reason=в summary/service.py добавлен только aclose() — ожидание фоновых задач при гашении; инвариант D-8 (концепт knowledge/engineering/model-split.md) не тронут: модели задаются типизированным конфигом, вывод R1 идёт через strip_thinking, токен-бюджеты summary отдельные by=human:anthony at=2026-08-12
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** прогоны `CI` и `quality` на `main` зелёные БЕЗ подавления
  `skipif(CI)` в `test_ws_voice.py`; в логе гашения нет строк
  `did not finish in time` / `cancelled by timeout`
- **observe_until:** 2026-08-26
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Починка виса, который предшествует контуру и держался с 2026-07-05. Это первая
продуктовая поставка после обновления контура, и она же — проверка, что контур
не мешает работать.

**Ключ к дефекту оказался не в коде, а в воспроизведении.** На macOS вис не
ловился (0 из 60), и поэтому год он жил как «падает через раз в CI». Прогон в
Linux-контейнере дал 6 висов из 10 и цикл диагностики в 40 секунд — после этого
причина нашлась за один дамп задач.

## Что именно чинится

1. **Уборка сессии под `shield` + таймаут.** Отмена от гашения приложения больше
   не рвёт запись статуса на середине, а значит соединение возвращается в пул.
2. **`_warmup_task` — задача-сирота.** Отменяется и **дожидается** на всех путях
   завершения. Здесь она не была причиной виса, но это тот же класс.
3. **Гашение ждёт живые уборки и фоновые суммаризации** до `db.dispose()`.
4. **Подавление снято**, добавлен регрессионный тест на инвариант.

## Замер

| | до фикса | после |
|---|---|---|
| висов на 10 прогонов (linux) | **6** | **0** |
| новый тест на старом коде (6 прогонов) | 6 красных/висов | — |
| сьют backend | 91 тест, 93.79% | **92 теста, 93.25%** |
