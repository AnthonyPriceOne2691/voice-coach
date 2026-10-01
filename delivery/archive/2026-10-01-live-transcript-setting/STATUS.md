# Active delivery status

- **slug:** live-transcript-setting
- **stack:** delivery@1.95, cqg@2.43, okf@1.19
- **class:** S
- **kind:** bugfix
- **repro_test:** `frontend/src/pages/InterviewPage.test.tsx` › «InterviewPage · переключатель живого транскрипта › выключен → во время сессии транскрипта на экране нет» — до правки красный: `expected <div class="bubble bubble-agent">…(1)</div> to be null`
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
- **worktree:** ../voice-coach-wt-transcript (ветка fix/live-transcript-setting)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=страница читает существующую настройку существующим запросом; пакетов не добавляется
- **runtime_paths:** frontend/src/pages/InterviewPage.tsx
  <!-- §12.6: страница отказывает разметкой, а не кодом ошибки. Тест сторожит
       решение «показывать или нет» на подменённой сессии; что пузырей нет на
       живой странице во время настоящей сессии, подтверждает прогон браузера. -->
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/voice/turn_runner.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- §14.1, как в vad-silence-setting. Дифф поставки поверхность не задевает. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** с выключенным переключателем во время живой сессии на экране
  только орб и полоска уровня, после конца сессии транскрипт виден; со включённым — как прежде
- **observe_until:** 2026-10-15
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Переключатель **Live transcript** на экране Settings с 2026-08-13 сохраняет и
показывает значение, но экран интервью его не читает: транскрипт виден во время
сессии всегда. Второй экземпляр класса, найденного поставкой
`2026-10-01-vad-silence-setting` (H5 её диагноза, урок L69).
