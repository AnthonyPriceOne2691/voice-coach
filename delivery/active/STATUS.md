# Active delivery status

- **slug:** talk-notes-rest
- **stack:** delivery@2.06, cqg@2.69, okf@1.21
- **class:** M
  <!-- D3a.2 — три поставки по одной спеке: talk-check (C1–C9, ведущая сессия),
       talk-notes (C10–C13), talk-tips (C14–C17). talk-notes собранной весила 1,044
       строки при пределе 800 и разрезана по слоям без waiver (решение ведущей сессии
       2026-10-23 по правилу спеки): talk-notes-rest (эта) и talk-notes-screen.
       talk-check и talk-notes идут параллельно; граница — контракт данных в spec.md. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; экран заметок разговора, оракулы спеки C10–C13
- **diagnosis:** n/a reason=не багфикс
- **phase:** verify
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-23)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=поставка только серверная; экран и сборка фронта — talk-notes-screen
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-a260dc0585f391a84 reason=параллельная сессия: основной клон ведёт talk-check; venv и node_modules свои (uv sync, npm ci), не симлинки (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=REST на FastAPI и SQLAlchemy, перевод — существующий SummaryService.translate_term; пакетов не добавляется
- **runtime_paths:** none reason=ws_voice.py и useVoiceSession.ts не тронуты; новые пути — REST, его исполняют тесты на TestClient с настоящей SQLite и управляемой моделью; отказ модели или голоса — код ответа 502/500, а не падение процесса
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; запись только в локальный app.db (банк слов)
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/api/ws_voice.py, backend/app/summary/**, backend/app/api/routes_talks.py
  <!-- Поставка добавляет к поверхности `api/routes_talks.py`: он собирает, что модель
       видит при переводе фразы из заметки (термин — лучший вариант, Usage — фраза
       Антона с исправленным фрагментом). Промпт перевода не меняется. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** C10–C13 REST-частью подтверждены в использовании после разговора Антона с заметками (через экран talk-notes-screen): заметки отдаются по порядку разговора, Add кладёт фразу с русским переводом и повтором не дублирует, Listen звучит его темпом, разговор виден в списке с длительностью и числом заметок; переводов фраз, отвергнутых S-H6, — не больше одного из десяти
- **observe_until:** 2026-11-24
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
