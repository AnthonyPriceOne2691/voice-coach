# Active delivery status

- **slug:** talk-check-wiring
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
- **class:** M
  <!-- D3a.2 по одной спеке: talk-check-core ✅, talk-check-wiring (эта: фоновая
       проверка, поток, WS, запись в базу), talk-notes-rest, talk-notes-screen, talk-tips. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; проводка проверки речи в разговор, оракулы спеки C1–C8 сквозь WS
- **diagnosis:** n/a reason=не багфикс
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-23)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=проводка — бэкенд; экран заметок — поставка talk-notes-screen
- **ci-oracles:** tooling
- **worktree:** none reason=ведущая сессия работает в основном клоне на ветке feat/talk-check-wiring; параллельные дорожки 2026-10-23 идут агентами в своих worktree
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=проверка речи собирается из того, что есть: клиент Ollama, енфорсер, оркестратор; тест-зависимость для свойств не добавляется — решение человека 2026-08-12, инварианты идут детерминированным перебором
- **runtime_paths:** backend/app/api/ws_voice.py
  <!-- §12.6: ход разговора запускает проверку речи после ответа и отменяет её следующей репликой, концом и уборкой сессии. Тесты исполняют это через WS на управляемой модели (RoutingLlm: ответ, JSON или зависание); живой разговор — по «запускай». -->
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; разговор пишется только в локальный app.db
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/orchestrator/tips.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/voice/language_check.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- Поправки добавляют к поверхности проверку речи: `voice/language_check.py`
       собирает то, что модель видит при проверке, `orchestrator/tips.py` решает,
       что из ответа модели прозвучит. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** после 10-минутного разговора Антона в `metadata_json.language_notes` есть заметки на ошибки и бедные фразы с фрагментом из сказанного, а на естественную и разговорную речь — нет; `checks_failed` 0, первый звук каждого хода ≤ 3 s
- **observe_until:** 2026-11-24
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
