# Active delivery status

- **slug:** vad-silence-setting
- **stack:** delivery@1.95, cqg@2.43, okf@1.19
  <!-- Ветка начата от origin/main (2567a09, delivery@1.68) и перенесена на main
       55625ed после того, как обновление контура и перенос сроков наблюдений
       ушли в main: правила последней версии проверяют её на handoff. -->
- **class:** S
- **kind:** bugfix
- **repro_test:** `frontend/src/hooks/useVoiceSession.test.tsx` › «useVoiceSession · порог тишины из Settings › 'сохранённые 0.9 s' → ход кончается через 900 мс тишины» — до правки красный: `expected "spy" to be called 1 times, but got 0 times`
- **diagnosis:** `delivery/active/diagnosis.md`
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** n/a (class S — mini-spec в tasks.md, §2.2)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build`
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-silence (ветка fix/vad-silence-setting)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=проводка существующей настройки в существующий детектор; пакетов не добавляется
- **runtime_paths:** frontend/src/hooks/useVoiceSession.ts
  <!-- §12.6: конец реплики на настоящем голосе. Тест исполняет проводку целиком —
       настройки → детектор → остановка записи, — но на подставных часах и
       анализаторе (L52). Конец реплики в настоящем браузере исполнен стендом
       `run.sh silence` (R4) по решению human:anthony 2026-10-01; живой голос
       человека остаётся сигналом наблюдения. -->
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/voice/turn_runner.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- §14.1, восемь категорий: промпты и их сборка кодом (prompts, knowledge,
       questions, prompts.py, build_user_message в interview.py); пины моделей и
       параметры сэмплирования (config.py, ollama_client, turn_runner, ws_voice,
       summary); схемы инструментов, извлечение и судья — нет; схема выхода —
       контракт и валидатор суммаризации; версия демона Ollama живёт вне репо.
       Дифф поставки поверхность не задевает. -->
- **rule_enforcers:** delivery/rule_enforcers.md
  <!-- §14.2a: реестр «правило промпта → исполнитель ниже модели | advisory»
       составлен в этой поставке впервые — требование пришло с delivery@1.95. -->

- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** R4 подтверждён на живом голосе — при пороге 3.0 s пауза
  посреди фразы не обрывает ход, при 0.8 s ход кончается заметно быстрее
- **observe_until:** 2026-10-31
  <!-- Перенесено 2026-10-17 с 2026-10-15 решением human:anthony: живых голосовых сессий с 30.09 не было (data/sessions/app.db не менялась), а сигнал требует живого голоса и глаз человека. Просрочка с 16.10 блокировала pre-push delivery-gate, job delivery и merge_guard — три ветки 17.10 не могли уехать. Новая дата — та же пачка, что у девятнадцати окон на 31.10: закрываются одной живой сессией. Сигнал выше не проверен — проверить в использовании и записать observed.md до новой даты. -->
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Ползунок **Silence before end-of-turn** на экране Settings с 2026-08-13 сохраняет
значение и показывает его, но голосовой цикл его не видит: детектор тишины
строится с умолчаниями, и ход всегда кончается через 2 s тишины. Найдено чтением
кода 2026-10-01, когда тренер разбирали как основу для другого голосового проекта.
