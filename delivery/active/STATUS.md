# Active delivery status

- **slug:** talk-wiring
- **stack:** delivery@2.01, cqg@2.57, okf@1.21
- **class:** M
  <!-- Весь режим «друг-наставник» — эпик из трёх поставок (D3a.1 разговор, D3a.2
       поправки, D3b память); каждая — класс M со своей спекой на подпись человека. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; новый режим разговора, оракулы спеки T1–T10
- **diagnosis:** n/a reason=не багфикс
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-17)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=сессия разговора на бэкенде; фронт и сборка не затронуты — экран Talk идёт следующей поставкой
- **ci-oracles:** tooling
- **worktree:** none reason=одна сессия в репозитории, основной клон на ветке feat/talk-mode; worktree одолжил бы backend/.venv и node_modules симлинками, а они дважды уезжали в коммит (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=новый режим собирается из того, что уже есть: FastAPI, SQLAlchemy, оркестратор, енфорсер, React; пакетов не добавляется
- **runtime_paths:** backend/app/api/ws_voice.py
  <!-- §12.6: голосовой цикл разговора. Тесты исполняют его через WS на фейковых
       модели, STT и TTS; настоящий голос, микрофон и модель — браузерный стенд в
       поставке экрана, только по «запускай» человека. -->
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; разговор пишется только в локальный app.db
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- Разговор добавил к поверхности: данные `data/talk/` и `orchestrator/talk.py`
       (talk-core) и окно истории `voice/talk_flow.py` — то, что модель видит. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** (снимается после поставки экрана Talk — до неё режим недоступен человеку) Антон проговорил с Генри в режиме Talk не меньше 10 минут: Генри отвечает по сути сказанного и держит разговор вопросом, тема меняется по просьбе, оценок нет ни разу, короткие реплики со словами «slow»/«fast» не меняют темп
- **observe_until:** 2026-11-17
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
