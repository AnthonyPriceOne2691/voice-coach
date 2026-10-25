# Active delivery status

- **slug:** talk-notes-screen
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
- **class:** M
  <!-- D3a.2 — три поставки по одной спеке: talk-check (C1–C9), talk-notes (C10–C13),
       talk-tips (C14–C17). talk-notes собранной весила 1,044 строки при пределе 800
       и разрезана по слоям без waiver: talk-notes-rest (в main, squash a97a621) и
       talk-notes-screen (эта) — экран тех же примеров. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; экран заметок разговора, оракулы спеки C10–C13
- **diagnosis:** n/a reason=не багфикс
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-23)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build`
  <!-- §6.5a. Гейт этого поля в проекте молчит: `declares_build` ищет `scripts.build`
       только в корневом package.json, а фронт живёт в frontend/ — находка
       verify-report. -->
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-a83fad904ac8715eb reason=над репозиторием параллельно работают несколько сессий; основной клон держит ведущая, у этой поставки свой worktree со своими backend/.venv и frontend/node_modules — настоящими, не симлинками (L13)
- **parallel_sessions:** merge-guard
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=экран на React и существующем клиенте fetch; пакетов не добавляется
- **runtime_paths:** frontend/src/components/LanguageNotes.tsx
  <!-- §12.6: Listen — `new Audio(url).play()` в настоящем браузере: декодирование
       WAV, политика автозапуска, звук через прокси `/sessions`. jsdom проверяет форму
       вызова, видимый отказ и уборку, а не звук; раскладка styles/notes.css — того же
       экрана и того же отложенного снимка. -->
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; экран пишет только через существующий REST в локальный app.db (банк слов)
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/orchestrator/tips.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/voice/language_check.py, backend/app/voice/session_factory.py, backend/app/api/ws_voice.py, backend/app/api/routes_talks.py, backend/app/summary/**, backend/app/memory/**
  <!-- Объединение объявлений talk-notes-rest (routes_talks.py) и memory-guard
       (tips.py, language_check.py, session_factory.py, memory/**). Поставка
       поверхности модели не касается: только фронт, доки и концепт. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** C10–C13 подтверждены в использовании после разговора Антона с заметками: Language notes видны после конца разговора и в детали разговора в History, ни одной оценки; Listen звучит лучшим вариантом его темпом и смолкает при старте нового разговора сразу после нажатия (колонки, не наушники); Add кладёт фразу с русским переводом в Useful Words (`fluency`), повтор — «Already in Useful Words»; History — секции Interviews и Talks, у разговора длительность или «not finished» и число заметок; Listen без «Can't play right now» — 10 нажатий из 10
- **observe_until:** 2026-11-24
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
