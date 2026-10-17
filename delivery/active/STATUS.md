# Active delivery status

- **slug:** talk-check
- **stack:** delivery@2.03, cqg@2.63, okf@1.21
- **class:** M
  <!-- D3a.2 — три поставки по одной спеке: talk-check (эта, C1–C9), talk-notes
       (C10–C13), talk-tips (C14–C17); решение человека 2026-10-17 «сначала список
       после, потом вслух», разрез — по предохранителю объёма. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; проверка речи в разговоре, оракулы спеки C1–C9
- **diagnosis:** n/a reason=не багфикс
- **phase:** specify
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** no
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=проверка речи — только бэкенд; экран заметок — поставка talk-notes
- **ci-oracles:** tooling
- **worktree:** none reason=одна сессия в репозитории, основной клон на ветке feat/talk-check; worktree одолжил бы backend/.venv и node_modules симлинками, а они дважды уезжали в коммит (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=новый режим собирается из того, что уже есть: FastAPI, SQLAlchemy, оркестратор, енфорсер, React; пакетов не добавляется
- **runtime_paths:** backend/app/api/ws_voice.py
  <!-- §12.6: ход разговора запускает проверку речи после ответа и отменяет её
       следующей репликой. Тесты исполняют это через WS на управляемой фейковой
       модели; живая модель — eval и замер по «запускай». -->
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; разговор пишется только в локальный app.db
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/orchestrator/tips.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/voice/language_check.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- Поправки добавляют к поверхности проверку речи: `voice/language_check.py`
       собирает то, что модель видит при проверке, `orchestrator/tips.py` решает,
       что из ответа модели прозвучит. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** после 10-минутного разговора Антона заметки разговора (REST до экрана talk-notes) содержат ошибки и бедные фразы со сказанным фрагментом, а на естественную и разговорную речь заметок нет; первый звук каждого хода ≤ 3 s
- **observe_until:** 2026-11-24
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
