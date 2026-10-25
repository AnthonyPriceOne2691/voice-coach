# Active delivery status

- **slug:** contract-keys
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
- **class:** S
  <!-- Один сторож на класс (тест), комментарии в трёх YAML и правка двух доков;
       продуктовый код не меняется. Repro ясен: сторож красный на main. -->
- **kind:** bugfix
- **repro_test:** backend/tests/test_contract_keys.py::test_every_contract_key_is_executed_or_declared
- **diagnosis:** active/diagnosis.md
- **phase:** verify
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** n/a (class S — mini-spec в tasks.md, §2.2)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=фронт не тронут ни строкой; собранное поставкой не меняется (§6.5a)
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-a98e3306c368a0d23 reason=параллельные поставки в одном репозитории, у каждой сессии своё дерево; backend/.venv и frontend/node_modules поставлены в нём заново, не симлинками (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=сторож на `ast` и `yaml` — оба уже в окружении сьюта
- **runtime_paths:** none reason=продуктовый код не тронут ни строкой: дифф — новый тест, комментарии YAML (значения не меняются) и доки; путь исполнения контрактов тот же
- **irreversible_surfaces:** none reason=локальный инструмент; поставка меняет тест, комментарии и документы
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/api/ws_voice.py, backend/app/summary/**
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
