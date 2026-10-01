# Active delivery status

- **slug:** settings-have-readers
- **stack:** delivery@1.95, cqg@2.43, okf@1.19
- **class:** S
- **kind:** test-gap
- **repro_test:** `backend/tests/test_settings_readers.py` (мутация: хук и экран интервью из `55625ed`, до правок 2026-10-01 — краснеют ровно `show_live_transcript` и `silence_threshold_ms`, остальные три ключа зелёные; проверено)
- **diagnosis:** n/a reason=не багфикс; оба дефекта класса уже исправлены (поставки vad-silence-setting и live-transcript-setting), отсутствовал оракул на класс
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** n/a (class S — mini-spec в tasks.md, §2.2)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=продуктовый код и сборка не меняются; предмет — тест
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-readers (ветка test/settings-have-readers)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=тест на стандартной библиотеке и pytest
- **runtime_paths:** none reason=продуктовый код не меняется вовсе; предмет поставки — тест, и он же оракул
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/voice/turn_runner.py, backend/app/api/ws_voice.py, backend/app/summary/**
  <!-- §14.1, как в прошлых поставках. Дифф поверхность не задевает. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** новый ключ в `DEFAULTS` без читателя роняет `backend` в CI с
  именем ключа в сообщении — проверить на первой поставке, добавляющей настройку
- **observe_until:** 2026-10-31
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Оракул на класс, который дал два дефекта подряд: ключ настроек хранится,
отдаётся и показывается на экране Settings, но поведения не меняет — читателя у
него нет (уроки L69, L71). Сторож связки стоял на один ключ и закрыл случай, а не
класс; этот тест — на перечень всех ключей `DEFAULTS`.
