# Active delivery status

- **slug:** test-leaks
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
- **class:** M
- **kind:** bugfix
  <!-- Не `fix`: гейт поставки узнаёт `bugfix` и только с ним требует repro_test и
       diagnosis (§3.1c, §12.1). Значение вне перечня канона пропустило бы обе
       проверки молча. -->
- **repro_test:** backend/tests/test_storage.py::test_interview_lifecycle
  <!-- §3.1c. До починки под сторожем — красный в teardown на каждом прогоне
       («1 соединени(й) открыто и не закрыто: движок без dispose()»), вместе с ещё
       17 тестами того же класса; после — зелёный. Без сторожа тот же дефект
       ронял не его, а случайный чужой тест, в том числе test_tts_piper.py. -->
- **diagnosis:** active/diagnosis.md
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-23) reason=примеры W1–W7 подписаны на мерже, как решил человек; подпись передала исполнителю ведущая сессия, сам исполнитель её не видел
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=фронт не тронут ни строкой; собранное поставкой не меняется (§6.5a)
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-a30a52584f9fc3c47 reason=параллельные поставки в одном репозитории, у каждой сессии своё дерево; backend/.venv и frontend/node_modules поставлены в нём заново, не симлинками (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=починка — владелец у каждого движка в тестах и учёт событий пула SQLAlchemy; всё нужное уже установлено
- **runtime_paths:** none reason=продуктовый код не тронут ни строкой — дифф состоит из тестов, конфига pytest и записей контура; пути гашения приложения, где сторож нашёл две скрытые утечки, переданы следующей поставке
- **irreversible_surfaces:** none reason=локальный инструмент; поставка меняет только тесты и конфиг сьюта
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- Перечень поверхности проекта взят без изменений у talk-screen. Дифф этой
       поставки её не задевает: тесты читают поверхность, но не меняют её. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** W2 в CI: прогоны workflow `CI` на `main` после мержа — ни одного красного от `ResourceWarning`, `PytestUnraisableExceptionWarning` или сторожа соединений («соединени(й) … не закрыто/не возвращено») в логе `gh run view --log`, не меньше 10 прогонов подряд; локальный `./scripts/run_checks.sh` у Антона зелёный
- **observe_until:** 2026-11-20
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
