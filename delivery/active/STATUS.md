# Active delivery status

- **slug:** memory-guard
- **stack:** delivery@2.07, cqg@2.74, okf@1.21
- **class:** M
  <!-- D3b — память Генри между разговорами; одна спека на три поставки по слоям:
       memory-guard (эта: K3–K8, K10, K12 — что может попасть в память),
       memory-write (K2, K9, K11, K13–K18, K19 — список), memory-recall (K1, K19
       целиком, K20–K25). Разрез — по предохранителю объёма, как у D3a. -->
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; новая функция — проверки памяти кодом, оракулы спеки K3–K8, K10, K12
- **diagnosis:** n/a reason=не багфикс
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-23) reason=«Подписать с рекомендациями» — приняты все шесть рекомендаций раздела «Открытые вопросы к Антону»
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=проверки памяти — бэкенд без экрана; экран «What Henry remembers» — поставка memory-recall
- **ci-oracles:** tooling
- **worktree:** .claude/worktrees/agent-a4f54d21e471ed425
- **parallel_sessions:** merge-guard
  <!-- Ведущая сессия параллельно сливает другие PR (D3a.2 и обслуживание контура);
       интеграция — по одной через scripts/merge_guard.sh, в main эта сессия не мержит. -->
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=проверки собираются из того, что есть: енфорсер разговора, разбор слов tips.py, PyYAML; тест-зависимость для свойств не добавляется — решение человека 2026-08-12, инварианты идут детерминированным перебором
- **runtime_paths:** none reason=проверки памяти — чистые функции без ввода-вывода, кроме чтения своих данных; путь после разговора (фон, отмена, Ollama) приходит с memory-write и объявит backend/app/memory/service.py
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; эта поставка ничего не пишет — заметок и таблиц ещё нет, их приносит memory-write
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, data/talk/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/orchestrator/talk.py, backend/app/orchestrator/tips.py, backend/app/voice/turn_runner.py, backend/app/voice/talk_flow.py, backend/app/voice/language_check.py, backend/app/voice/session_factory.py, backend/app/api/ws_voice.py, backend/app/summary/**, backend/app/memory/**
  <!-- Память добавляет к поверхности то, что решает, какие слова модели станут
       заметкой и позже прозвучат: `backend/app/memory/` и данные
       `data/contracts/memory*`. Промпт извлечения и вызов модели — memory-write. -->
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** K3, K4, K5, K6, K7, K8, K10, K12 на живых заметках после memory-write: за первые пять разговоров Антона — 0 заметок с контактами, деньгами, судом, здоровьем, семьёй или Ally, у каждой заметки цитата — его слова дословно, ни одной второй заметки об одном и том же, в логе отказов только причина, категория и число; ложные отказы (заметка о деле, отброшенная из-за слова мимоходом) — считать и решать с Антоном, не ослаблять список молча
- **observe_until:** 2026-12-07
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
