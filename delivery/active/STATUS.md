# Active delivery status

- **slug:** talk-tips
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
- **class:** M
  <!-- D3a.2 по одной спеке: talk-check-core ✅, talk-check-wiring ✅, talk-notes-rest ✅,
       talk-notes-screen (готова локально), talk-tips (эта: подсказка вслух, C14–C17).
       Починка загрузчика контрактов (запрещённые фразы по правилу, 72a2f7b) приехала
       сюда cherry-pick'ом: без неё второе правило forbid_patterns (I3-H4) проверяло бы
       чужой список. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; подсказка вслух после ответа по сути, оракулы спеки C14–C17
- **diagnosis:** n/a reason=не багфикс
- **phase:** plan
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-23)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=экран не меняется: подсказка приходит прежними сообщениями `audio` и `transcript` (doc 15), её звук и текст судят WS-тесты
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-a1b07e279b597e401 reason=параллельная сессия: ведущая сливает другие PR; venv и node_modules свои (uv sync, npm ci), не симлинки (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=подсказка собирается из того, что есть: проверка речи, енфорсер, шаблоны в data/talk; длительность звука читает stdlib `wave`
- **runtime_paths:** backend/app/api/ws_voice.py
  <!-- §12.6: ход разговора после ответа ждёт проверку речи до конца звука + 1.5 s и
       произносит подсказку до `listening`. Тесты исполняют это через WS на управляемой
       модели (RoutingLlm: ответ, JSON, задержка или зависание); живой разговор — по
       «запускай». -->
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; разговор пишется только в локальный app.db
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/orchestrator/tips.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/voice/language_check.py, backend/app/api/ws_voice.py, backend/app/summary/**, backend/app/api/routes_talks.py
  <!-- Поверхность не растёт: подсказку говорит код, и в историю модели она не
       попадает (`TalkFlow.on_tip`). Поведение модели меняет новое правило контракта
       I3-H4 (`data/contracts/**`) — енфорсер режет её поправки до озвучки. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** после 10-минутного разговора Антона на ошибках и бедных фразах после ответа по сути звучит одна подсказка по шаблону, у таких заметок `spoken: true`, а `spoken: false` (проверка не успела к концу ответа + 1.5 s) — не больше одной из пяти; сам Генри не поправляет и не объясняет грамматику; первый звук хода после подсказки ≤ 3 s
- **observe_until:** 2026-11-24
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
