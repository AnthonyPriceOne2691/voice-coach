# Active delivery status

- **slug:** talk-check-core
- **stack:** delivery@2.06, cqg@2.69, okf@1.21
- **class:** M
  <!-- D3a.2 по одной спеке: talk-check-core (эта: решение кода, вызов модели, eval),
       talk-check-wiring (проводка), talk-notes (экран), talk-tips (вслух). Разрез
       talk-check — по предохранителю: 1,044 строки при 800. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; решение кода о заметке к речи, оракулы спеки C1, C3–C9
- **diagnosis:** n/a reason=не багфикс
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-23)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=ядро проверки речи — бэкенд без экрана; экран заметок — поставка talk-notes
- **ci-oracles:** tooling
- **worktree:** none reason=ведущая сессия работает в основном клоне на ветке feat/talk-check-core; параллельные дорожки 2026-10-23 идут агентами в своих worktree
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=проверка речи собирается из того, что есть: клиент Ollama, енфорсер, оркестратор; тест-зависимость для свойств не добавляется — решение человека 2026-08-12, инварианты идут детерминированным перебором
- **runtime_paths:** none reason=ядро не входит в путь хода: проверку в WS подключает поставка talk-check-wiring
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; разговор пишется только в локальный app.db
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/orchestrator/tips.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/voice/language_check.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- Поправки добавляют к поверхности проверку речи: `voice/language_check.py`
       собирает то, что модель видит при проверке, `orchestrator/tips.py` решает,
       что из ответа модели прозвучит. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** eval C9 на живой модели проходит пороги спеки при каждом изменении просьбы `language_check.txt`; в живом разговоре Антона (после wiring) заметки ловят ошибки и бедные фразы, а естественная и разговорная речь — без заметок
- **observe_until:** 2026-11-24
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
