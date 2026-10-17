# Active delivery status

- **slug:** profile-refresh
- **stack:** delivery@2.01, cqg@2.55, okf@1.19
  <!-- Спека написана сессией local-web-agent на main 24167fd (delivery@2.00, cqg@2.51);
       ветка перенесена на main 3972942 после окон (#24), контура (#25) и фикса (#26, #27). -->
- **class:** M
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; предмет — содержимое знания агента, оракулы спеки проверяют покрытие проектов, цифры, бюджет и инжект
- **diagnosis:** n/a reason=не багфикс: профиль не сломан, а отстал от положения кандидата на три недели
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-10-17)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=правка данных знания, тестов и дока; фронт и сборка не затронуты
- **ci-oracles:** tooling
- **worktree:** none reason=правка markdown знания и одного теста в основном клоне на ветке feat/profile-refresh; кода продукта не трогает
- **parallel_sessions:** merge-guard
  <!-- §5.1a: 17.10 над репозиторием работали две сессии; интеграция только через
       scripts/merge_guard.sh, по одной и на слитом состоянии. -->
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=правка markdown в data/knowledge, теста и дока; пакетов не добавляется
- **runtime_paths:** none reason=подумали и нет: знание попадает в промпт через существующий `{{profile_condensed}}`, путь исполняется тестами промптов и ws; отказ виден тестам
- **irreversible_surfaces:** none reason=локальный инструмент без отправки наружу; правка содержимого промпта
- **model_surface:** data/prompts/**, data/knowledge/**, data/questions/**, data/contracts/**, backend/app/config.py, backend/app/llm/**, backend/app/knowledge/prompts.py, backend/app/orchestrator/interview.py, backend/app/voice/turn_runner.py, backend/app/api/ws_voice.py, backend/app/summary/**
- **rule_enforcers:** delivery/rule_enforcers.md
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** P7 подтверждён в живом разговоре — Генри называет нынешнюю работу Антона (SEO-агентство, звонки западным клиентам) и цифру одного из новых проектов так, как она измерена; серию YouTube Shorts описывает как ролики об автоматизации, а не как автоматизацию YouTube (строка переписана после P7 и живьём не перепроверена)
- **observe_until:** 2026-11-14
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
