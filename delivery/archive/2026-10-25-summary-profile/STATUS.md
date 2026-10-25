# Active delivery status

- **slug:** summary-profile
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
- **class:** S
  <!-- Правка двух файлов промпта и одной строки общего загрузчика; repro ясен —
       тест на сообщения сводки. Документы и записи контура — сопровождение. -->
- **kind:** bugfix
- **repro_test:** backend/tests/test_summary.py::test_full_summary_sends_the_candidate_profile
- **diagnosis:** active/diagnosis.md
- **phase:** handoff
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
- **new_dependency:** none reason=подстановка профиля — существующим механизмом `PromptLibrary`; пакетов не добавляется
- **runtime_paths:** none reason=подумали и нет: профиль уходит в модель обычным текстом системного сообщения, путь исполняется тестами сводки на фейковой модели; отказа, невидимого тестам, здесь нет — меняется содержимое промпта, а не тракт
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; правка меняет текст промптов офлайн-разбора
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/api/ws_voice.py, backend/app/summary/**
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** U1 и U2 в живом использовании (после «запускай»): в debrief_json трёх сессий подряд балл `positioning` и хотя бы одна запись `consistency_flags` или `improvements` с category `positioning` опираются на правила `Positioning rules` профиля (builder/delivery, не SEO lead), а не на роль «AI automation engineer»; сводка 15-минутной сессии сохраняется как `full`, не деградирует в `minimal`
- **observe_until:** 2026-11-25
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
