# Active delivery status

- **slug:** henry-coach-persona
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; инвертируется намеренно принятое решение, а не чинится дефект. Оракулы — контрактные тесты ниже
- **diagnosis:** n/a reason=не багфикс; причина известна и записана: doc 09 «Mode 1: zero coaching» и контракт I1-H2 запрещали помощь машиной
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-12) reason=человек подписал границу выбором варианта «помогать можно, баллы и итоговый разбор остаются вне интервью»; примеры G1–G6 — её механическое выражение и предъявлены до кода
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=правка данных, промптов и доков; фронт не тронут
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-henry (ветка feat/henry-coach)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=правка YAML-контракта, списка паттернов, промпта и доков
- **runtime_paths:** data/contracts/interview.contract.yaml
  <!-- §12.6: контракт исполняется ПЕРЕД озвучкой каждой фразы. Ошибка в нём не
       видна ни сборке, ни типам: слишком строгий режет живую речь, слишком
       слабый пропускает то, что решили не пускать. Проверяется прогоном
       енфорсера на живых фразах и сессией в браузере. -->
- **canon_drift_waiver:** reason=тронут data/prompts/interviewer_system.txt из implementation концепта orchestrator-owns-structure, но инвариант I1-H6 не изменился: концепт про то, КТО выбирает вопрос, а дифф меняет только КАК агент говорит и помогает. Правило «не выбирать следующий вопрос» сохранено дословно и вдобавок усилено новой строкой «You never choose what comes next». Правка концепта была бы ложным «обновлено» by=human:anthony at=2026-08-12
- **observability:** 1
- **observe_signal:** G1–G6 подтверждены; в живой сессии Генри подсказывает
  направление и хвалит, при этом в транскрипте нет баллов и итогового разбора
- **observe_until:** 2026-08-26
- **baseline_growth_waiver:** no
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Первая из четырёх поставок по просьбе человека 2026-08-12: «добрый
тренер-помощник», задача — не дрючить, а раскрепостить, убрать барьер.

**Помогать сейчас запрещено машиной, а не только промптом.** Контракт
`I1-H2_no_coaching` режет фразы до озвучки, `interview_forbidden.txt` содержит
ровно то, что человек просит разрешить: «you should», «try saying»,
«great answer», «well done». Поэтому правка промпта в одиночку не работает —
инвертируется контракт.

**Подписанная граница:** помогать, подсказывать, хвалить, наталкивать — можно.
Баллы, рубрики и итоговый разбор внутри интервью — **нельзя**: они живут в
Mode 2 «Review Together» и в debrief, иначе тренироваться станет негде.
