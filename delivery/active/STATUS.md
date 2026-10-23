# Active delivery status

- **slug:** deps-refresh
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
  <!-- Ветка отведена от main 73342b3 (delivery@2.06 · cqg@2.69) и 2026-10-23 перебазирована
       на a4a0dce (накат 2.74/2.07). Шаг «Vulnerable dependencies» в каноне 2.74 тот же,
       дайджест check_deps_audit.sh в payload.lock.json не изменился (8cbe1573). -->

- **class:** M
  <!-- Остаток обновления контура 2.69 (STACK-ACCEPTANCE «Остатки обновления 2.69»):
       аудит уязвимых зависимостей красный и не исполняется нигде. vitest 2 → 5 —
       три мажорные версии тестового раннера, поэтому M, а не S. -->
- **kind:** refactor
  <!-- §3.1b: поведение продукта не меняется — меняются версии зависимостей. Цена
       weak здесь ровно рефакторная: тихая регрессия в работавшем, «собирается»
       ничего не доказывает. Закрыто differential-проверкой (бандл до и после
       побайтно одинаков, те же 57 тестов фронта и 275 бэкенда) и наблюдаемой
       (dev-сервер на 5273). -->
- **repro_test:** n/a reason=не багфикс; уязвимости живут в чужом коде, состояние «до» — красный прогон гейта на main 73342b3 (eval-smoke V1)
- **diagnosis:** n/a reason=не багфикс
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-23)
  <!-- Примеры V1–V8 подписаны на мерже, как решил человек 2026-10-23: до подписи
       поставка шла под `deferred` (§2.2b). -->

- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build`
- **ci-oracles:** tooling
- **worktree:** /Users/anthony/Documents/voice-interview-coach/.claude/worktrees/agent-aa3d737f55163b435 reason=параллельные сессии на одном репозитории (§5.1a): основной клон у ведущей сессии, соседние агенты в своих деревьях; venv и node_modules настоящие, внутри дерева, не симлинки (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=только смена версий существующих пакетов: vitest и vite во frontend, anyio, urllib3, certifi, virtualenv в backend/uv.lock; packaging и python-discovery — транзитивные (их требует virtualenv), новых прямых зависимостей нет
- **runtime_paths:** frontend/package.json
  <!-- §12.6: версия vite — это dev-сервер (`scripts/dev.sh`, порт 5273, прокси на
       :8000). Ни сборка, ни тесты его не поднимают, а забытый прокси отвечает
       страницей приложения с кодом 200 (L11). Исполняется запуском vite и пробой
       маршрутов прокси. -->
- **irreversible_surfaces:** none reason=локальный инструмент; поставка меняет версии пакетов и шаг CI, наружу уходят только имена и версии пакетов к реестрам уязвимостей — то же, что делают npm ci и uv sync
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- Поставка поверхности модели не касается: ни промптов, ни кода хода. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** V2 в использовании: шаг «Vulnerable dependencies» исполняется на каждом PR в main и печатает «мерена по uv.lock»; первый красный от нового advisory закрыт обновлением пакета или подписанным deps_audit_waiver, а не снятием шага; `./scripts/dev.sh` поднимает фронт на 5273 с рабочими History и Settings (V6)
- **observe_until:** 2026-11-23
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
