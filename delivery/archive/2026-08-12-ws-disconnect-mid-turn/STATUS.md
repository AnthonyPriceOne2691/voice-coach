# Active delivery status

- **slug:** ws-disconnect-mid-turn
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** bugfix
- **repro_test:** backend/tests/test_ws_voice.py::test_disconnect_during_turn_finishes_session
- **diagnosis:** active/diagnosis.md
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-12) reason=примеры B1–B6 предъявлены ДО кода, вместе с двумя оговорками: B4/B5 — про «не сломать» и потому дороже, B6 держится на браузерном стенде, которого в CI нет
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=фронт не тронут; дефект целиком в обработке разрыва на бэкенде, собранное этой поставкой не меняется (§6.5a)
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-mid-turn (ветка fix/ws-disconnect-mid-turn)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=правка в существующем модуле, стандартная библиотека и уже установленный starlette
- **runtime_paths:** backend/app/api/ws_voice.py
  <!-- §12.6: путь завершения ws-сессии. Прошлая поставка доказала, что отказ на
       нём виден только исполнением — и она же оставила ЭТОТ вход незакрытым:
       её тесты рвут соединение в состоянии ожидания, а дефект живёт в разрыве
       ПОСЕРЕДИНЕ хода. Найден браузерным прогоном, 2 из 2. main.py на этот раз
       не тронут — порог §12.6 (1 путь) соблюдается без подписи. -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** B1–B3 подтверждены; в логе бэкенда при закрытии вкладки
  посередине хода нет `Exception in ASGI application` и нет `voice turn failed`
  (разрыв перестал считаться отказом хода)
- **observe_until:** 2026-10-31
  <!-- Перенесено 2026-10-01 с 2026-08-26 решением human:anthony: наблюдение не проведено вовремя, и просрочка с 30.09 блокировала pre-push и job delivery в CI (приёмка 01.10). Сигнал выше не проверен — проверить в использовании и записать observed.md до новой даты. -->
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Второй вход в инвариант «отключение клиента завершает сессию». Поставка
`ws-disconnect-hang` (слита 2026-08-12) закрыла разрыв в состоянии **ожидания**;
этот дефект живёт в разрыве **посередине хода** и ею не вносился — замер:
`git diff 6a6132e 70c6d15 -- backend/app/api/ws_voice.py` меняет 52 строки и ни
одной в `_on_utterance_end`, `_error`, `_send`.

Найден ручным прогоном в браузере — тем самым, который прошлая поставка честно
назвала незакрытым пробелом приёмки.
