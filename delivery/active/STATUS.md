# Active delivery status

- **slug:** talk-memory
- **stack:** delivery@2.06, cqg@2.69, okf@1.21
- **class:** M
  <!-- D3b — память Генри между разговорами; одна спека на три поставки по слоям:
       memory-guard (K3–K8, K10, K12), memory-write (K2, K9, K11, K13–K18, K19 — список),
       memory-recall (K1, K19 целиком, K20–K25). Разрез — по предохранителю объёма, как у D3a. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; новая функция — память разговора, оракулы спеки K1–K25
- **diagnosis:** n/a reason=не багфикс
- **phase:** specify
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** no
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build`
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-ab2e975f6c510f09e — спека пишется параллельно с D3a.2; у каждой поставки D3b будет свой worktree (§5.1)
- **parallel_sessions:** merge-guard
  <!-- D3a.2 (talk-check → talk-notes → talk-tips) строится параллельно в других
       деревьях и трогает те же файлы разговора; интеграция — по одной через
       scripts/merge_guard.sh, порядок — в разделе «Поставки» спеки. -->
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=память собирается из того, что уже есть: FastAPI, SQLAlchemy, клиент Ollama, енфорсер, React; пакетов не добавляется
- **runtime_paths:** backend/app/memory/service.py
  <!-- §12.6: фоновое извлечение после разговора и его отмена стартом новой сессии.
       Тесты исполняют отмену на зависающей фейковой модели, но остановит ли
       закрытый стрим генерацию в настоящей Ollama и освободит ли слот для прогрева
       новой сессии — видно только на живом стеке: замер K14 по «запускай» человека. -->
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; заметки живут в локальной app.db, физическое удаление — действие человека на экране; тесты и стенд работают на своей базе, живую app.db агент не трогает
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/voice/session_factory.py, backend/app/api/ws_voice.py, backend/app/summary/**, backend/app/memory/**
  <!-- Что модель увидит из-за памяти. В разговоре — строку-воспоминание в истории
       (заметку выбирают `orchestrator/talk.py` и `voice/session_factory.py`, шаблон —
       `data/talk/`), новую строку `talk_system.txt` и правило I3-H4 со списком в
       `data/contracts/`. После разговора — промпт извлечения
       `data/prompts/memory_notes_system.txt` и беседу, которую собирает
       `backend/app/memory/`, с параметрами из `config.py`. Пути D3a.2
       (`orchestrator/tips.py`, `voice/language_check.py`) войдут в список, когда
       D3a.2 попадёт в main. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** после пяти разговоров Антона (K2, K14, K17–K20, K23): у каждого разговора с рассказом о себе — 1–3 заметки с его словами дословно; ни одной заметки с контактами, деньгами, судом, семьёй, здоровьем; Генри открыл разговор вопросом о заметке и ни разу не «вспомнил» того, чего в заметках нет; стёртая заметка не вернулась; первый звук ≤ 3 s, в том числе у сессии, начатой сразу после разговора
- **observe_until:** 2026-12-07
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
