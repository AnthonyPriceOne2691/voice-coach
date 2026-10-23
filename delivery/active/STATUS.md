# Active delivery status

- **slug:** talk-notes
- **stack:** delivery@2.06, cqg@2.69, okf@1.21
- **class:** M
  <!-- D3a.2 — три поставки по одной спеке: talk-check (C1–C9, ведущая сессия),
       talk-notes (эта, C10–C13), talk-tips (C14–C17). talk-check и talk-notes идут
       параллельно; граница между ними — контракт данных в spec.md. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; экран заметок разговора, оракулы спеки C10–C13
- **diagnosis:** n/a reason=не багфикс
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-23)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build`
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-a260dc0585f391a84 reason=параллельная сессия: основной клон ведёт talk-check; venv и node_modules свои (uv sync, npm ci), не симлинки (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** breaker max_loc_diff — собранная поставка net 1,044 без доков (~1,115 с доками) при пределе 800; разрез или waiver — решение человека, active/escalation.md
- **waivers:** none
- **new_dependency:** none reason=REST на FastAPI и SQLAlchemy, экран на React, перевод — существующий SummaryService.translate_term; пакетов не добавляется
- **runtime_paths:** none reason=ws_voice.py и useVoiceSession.ts не тронуты; новые пути — REST (исполняют тесты на TestClient) и экран (jsdom); отказ проигрывания Listen — отклонённый промис play(), который экран показывает, а не падение процесса
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; запись только в локальный app.db (банк слов)
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/api/ws_voice.py, backend/app/summary/**, backend/app/api/routes_talks.py
  <!-- Поставка добавляет к поверхности `api/routes_talks.py`: он собирает, что модель
       видит при переводе фразы из заметки (термин — лучший вариант, Usage — фраза
       Антона с исправленным фрагментом). Промпт перевода не меняется. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** после разговора Антона с заметками C10–C13 подтверждены в использовании: экран Language notes показывает каждую заметку «you said → better — why», Listen звучит его темпом, Add to Useful Words кладёт фразу с русским переводом и повтором не дублирует, разговор виден в History с числом заметок; переводов фраз, отвергнутых S-H6, — не больше одного из десяти
- **observe_until:** 2026-11-24
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
