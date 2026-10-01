# Active delivery status

- **slug:** vad-silence-setting
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
  <!-- Версии origin/main (2567a09). Обновление контура до delivery@1.95 · cqg@2.43 ·
       okf@1.19 лежит неотправленным в локальном main основного клона — поставка на
       него не опирается и ветвится от origin/main намеренно: пуш ветки не должен
       увозить чужую незаконченную работу. -->
- **class:** S
- **kind:** bugfix
- **repro_test:** `frontend/src/hooks/useVoiceSession.test.tsx` › «useVoiceSession · порог тишины из Settings › 'сохранённые 0.9 s' → ход кончается через 900 мс тишины» — до правки красный: `expected "spy" to be called 1 times, but got 0 times`
- **diagnosis:** `delivery/active/diagnosis.md`
- **phase:** verify
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
       анализаторе (L52). Что пауза посреди живой фразы переживает выставленный
       порог, подтверждает только разговор: R4, человек. -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** R4 подтверждён на живом голосе — при пороге 3.0 s пауза
  посреди фразы не обрывает ход, при 0.8 s ход кончается заметно быстрее
- **observe_until:** 2026-10-15
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Ползунок **Silence before end-of-turn** на экране Settings с 2026-08-13 сохраняет
значение и показывает его, но голосовой цикл его не видит: детектор тишины
строится с умолчаниями, и ход всегда кончается через 2 s тишины. Найдено чтением
кода 2026-10-01, когда тренер разбирали как основу для другого голосового проекта.
