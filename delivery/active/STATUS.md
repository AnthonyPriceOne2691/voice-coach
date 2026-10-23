# Active delivery status

- **slug:** mutation-gate
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
- **class:** M
  <!-- Остаток обновления 2.69 из STACK-ACCEPTANCE: мутационный гейт объявлен
       ролью, а на этом проекте не судил ни разу. Чинится сам гейт на проекте
       (корень репозитория, затенение, покрытие), а не канонный скрипт. -->
- **kind:** bugfix
- **repro_test:** backend/tests/test_repo_root.py::test_mutants_copy_resolves_to_the_same_root
- **diagnosis:** active/diagnosis.md
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** deferred (reason=человек подписывает примеры на мерже — решение human:anthony 2026-10-23; at=2026-10-23)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=фронт не тронут ни одной строкой; собранное этой поставкой не меняется (§6.5a)
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-ad938971a5a5f44a4 reason=над репозиторием параллельно работают несколько сессий; основной клон держит ведущая, у этой поставки свой worktree со своими backend/.venv и frontend/node_modules — настоящими, не симлинками (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=mutmut уже в dev-зависимостях манифеста (`mutmut>=3.6`, в замке 3.7.0) и ставится тем же `uv sync --all-extras`; пакетов не добавляется
- **runtime_paths:** frontend/src/hooks/useVoiceSession.ts
  <!-- §12.6: голосовая петля на клиенте. Этим диффом не задета. -->
- **irreversible_surfaces:** none reason=локальный инструмент; дифф меняет тесты, конфиг гейта и шаг CI, наружу ничего не отправляет
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/api/ws_voice.py, backend/app/summary/**
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** knowledge/engineering/model-split.md, knowledge/engineering/sentence-streaming.md reason=в backend/app/config.py изменено только то, как находится корень репозитория (по данным, а не по глубине пути) — модели, температуры, бюджеты токенов и num_ctx те же, D-8 не тронут; в backend/app/contracts/enforcer.py TurnEnforcer из dataclass стал обычным классом с тем же __init__ — проверки, их порядок и per-sentence семантика прежние, тесты контрактов те же. Правка концептов была бы ложным «обновлено» by=agent:claude-code (подпись human:anthony — на мерже вместе с примерами)
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** M13 — на пяти следующих PR в main с python-диффом шаг «Mutation testing (changed files, budgeted)» печатает «убито N из M» и решает по порогу 60%; ни одного «не просудил» по причине среды (корень, сбор, покрытие); время шага в логе — в пределах бюджета 300 s
- **observe_until:** 2026-11-23
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
