# Active delivery status

- **slug:** shutdown-leaks
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
  <!-- Ветка отведена от main c1e4952, до первого коммита сведена fast-forward на
       8d344d4 (#46 deps-refresh), на verify в неё влиты слиянием 5d7d7b7 (#48
       talk-check-wiring) и a97a621 (#42 talk-notes-rest); контур на всех базах один. -->
- **class:** M
  <!-- Не S, хотя repro ясен и правка мала: S канона — «багфикс ≤1 файла» (§2.2), а здесь
       два продуктовых файла, две двери гашения, и в одной из них меняется поведение —
       застрявшая уборка ws-сессии по сроку теперь отменяется. Так же проект вёл прежние
       многофайловые багфиксы гашения (ws-disconnect-hang, ws-disconnect-mid-turn — M).
       Класс определяется работой, а не тем, что человека рядом нет (§2.2b), — decisions D1. -->
- **kind:** bugfix
- **repro_test:** backend/tests/test_shutdown_cancellation.py::test_shutdown_waits_until_a_cancelled_summary_returns_its_connection, backend/tests/test_shutdown_cancellation.py::test_shutdown_cancels_a_stuck_ws_cleanup_and_waits_for_it
  <!-- §3.1c. До правки оба красные 5 из 5: в теле учёт соединений называет «1 соединени(й)
       выдано пулом и не возвращено…» и «1 соединени(й) открыто и не закрыто…», в teardown
       — страж канона и наш сторож. После — зелёные. -->
- **diagnosis:** active/diagnosis.md
- **phase:** verify
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** deferred (reason=исполнитель работает без человека — вопросы ему по условию запуска не задаются; примеры E1–E5 предъявляются на мерже через ведущую сессию, at=2026-10-25)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=фронт не тронут ни строкой; собранное поставкой не меняется (§6.5a)
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-acb118d08a01f0c55 reason=параллельные поставки в одном репозитории (§5.1a), у каждой сессии своё дерево; backend/.venv и frontend/node_modules поставлены в нём заново, не симлинками (L13), и пересобраны после слияния #46
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=правка — порядок шагов в двух функциях гашения; пакетов не добавляется
- **runtime_paths:** none reason=подумали: отказ этих путей теперь виден сьюту — E1/E2 исполняют настоящий lifespan, настоящую ws-сессию и настоящий пул SQLAlchemy над aiosqlite, судит учёт соединений; состояние «задача держит соединение в момент гашения» тест ставит сам, поэтому вердикт не зависит от планировщика и платформы (в отличие от августа: 6 из 10 на linux, 0 из 60 на macOS), вторая среда — CI на ubuntu
- **irreversible_surfaces:** none reason=локальный инструмент; поставка меняет порядок шагов гашения процесса, наружу ничего не уходит
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- Перечень поверхности проекта взят без изменений у deps-refresh. Дифф задевает
       backend/app/summary/service.py — путь поверхности, но не поведение модели: изменён
       только aclose(), промпты, SCHEMA_HINT, модели и параметры не тронуты (verify-report,
       «Изменение поверхности модели»). -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** knowledge/engineering/model-split.md reason=в backend/app/summary/service.py изменён только SummaryService.aclose() — порядок гашения: по сроку отменить фоновую задачу и дождаться её отмены до dispose(); инвариант D-8 не тронут — модели задаются типизированным конфигом, вывод R1 идёт через strip_thinking, бюджеты разбора отдельные, починка перевода на qwen, поля-списки приводит валидатор; правка концепта была бы ложным «обновлено» by=human:anthony at=2026-10-23
  <!-- Подпись передала исполнителю ведущая сессия, слова человека: «Сегодня, waiver
       подписываю»; сам исполнитель её не видел. backend/app/main.py не входит ни в один
       implementation: и waiver'а не требует. -->
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** E1, E2 в CI: прогоны workflow `CI` на `main` после мержа — `test_shutdown_cancellation.py` зелёный не меньше 10 прогонов подряд (по логу `gh run view --log`), и в тех же логах ни одного `non-checked-in connection`; E3 в использовании — гашение `./scripts/dev.sh` (Ctrl+C) у Антона после интервью с разбором: в логе backend `Application shutdown complete`, разбор виден в History, `SAWarning`/`ResourceWarning` aiosqlite нет
- **observe_until:** 2026-11-22
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
