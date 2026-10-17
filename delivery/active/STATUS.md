# Active delivery status

- **slug:** regenerate-mode-neutral
- **stack:** delivery@2.01, cqg@2.55, okf@1.19
  <!-- Ветка начата от main 24167fd (delivery@2.00, cqg@2.51) сессией local-web-agent и
       перенесена на main dac424a после того, как перенос двух окон наблюдения (#24) и
       обновление контура (#25) ушли в main: правила последней версии проверяют её на handoff. -->
- **class:** S
- **kind:** bugfix
- **repro_test:** `backend/tests/test_turn_runner.py::test_regenerate_hint_carries_no_interview_era_rules` — до правки красный: `AssertionError: в подсказке перегенерации остался 'interview rules'`; вместе с ним краснеет обновлённый `test_violation_on_first_sentence_regenerates`
- **diagnosis:** n/a reason=гипотез не было: дефект найден чтением кода при подготовке режима разговора — текст константы прямо противоречит контракту interview 2.0 и лимитам review, второй причины не искали, потому что расхождение видно в одной строке
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** n/a (class S — mini-spec в tasks.md, §2.2)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=правка текстовой константы бэкенда и тестов; фронт и сборка не затронуты
- **ci-oracles:** tooling
- **worktree:** none (S) — ветка fix/regenerate-mode-neutral в основном клоне
- **parallel_sessions:** merge-guard
  <!-- §5.1a: 17.10 над репозиторием работали две сессии (local-web-agent, затем
       voice-interview-coach), и от main было отведено три ветки параллельно. Интеграция —
       только через scripts/merge_guard.sh, по одной и на слитом состоянии: окна (#24),
       контур (#25), затем эта поставка. -->
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=правка текста подсказки и тестов; пакетов не добавляется
- **runtime_paths:** none reason=подумали и нет: подсказка уходит в LLM обычным сообщением чата, путь исполняется тестами TurnRunner на фейковой модели; отказа, невидимого тестам, здесь нет — меняется содержимое строки, а не тракт
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; правка меняет текст подсказки модели
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/voice/turn_runner.py, backend/app/api/ws_voice.py, backend/app/summary/**
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** knowledge/engineering/sentence-streaming.md, knowledge/ops/transcript-durability.md reason=в backend/app/voice/turn_runner.py изменён только текст STRICT_REGENERATE — что модель слышит при повторе после нарушения на первом предложении; стриминг по предложениям, проверка каждого предложения до синтеза, лестница восстановления (повтор → seed, R3 без изменений) и восстановимость хода не менялись. Правка концептов была бы ложным «обновлено» by=human:anthony at=2026-10-17
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** R1 подтверждён в живом разборе — после нарушения контракта (в метаданных сессии violation с recovery=regenerate) повторный ответ Генри сохраняет похвалу и совет и не урезан до трёх предложений
- **observe_until:** 2026-11-07
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
