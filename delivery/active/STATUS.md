# Active delivery status

- **slug:** soft-skills
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** feature
- **repro_test:** n/a (kind=feature)
- **diagnosis:** n/a reason=не багфикс; предмет известен из спеки, гипотез не требовалось
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-12) reason=три решения предъявлены ДО кода и подтверждены: чередование в одном интервью вместо отдельного режима; своя ветка политики follow-up для behavioral (иначе «нет цифр» истинно всегда); три soft-вопроса из шести
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=фронт не тронут (spec, Out of scope); оракул бэкенда — pytest
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-soft-skills (ветка feat/soft-skills)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=банк вопросов — данные, политика — код; новых пакетов не требуется
- **runtime_paths:** none reason=подумали и нет: ни экрана, ни прав, ни железа, ни миграций. Единственное, что видно только человеку, — уместность самих вопросов, и это оракул S9 (живая сессия), а не рисковый путь платформы
- **canon_drift_waiver:** knowledge/engineering/sentence-streaming.md reason=тронут interview_flow.py — в buffer.append добавлен аргумент question_kind; ни темп стриминга, ни sentence-gating, ни latency не затронуты by=human:anthony
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** S1, S2, S9 подтверждены в живой сессии — в разговоре звучат
  и технические, и behavioral вопросы вперемежку, и Генри не задаёт лишних
  допросов к хорошо рассказанной истории
- **observe_until:** 2026-08-26
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Банк вопросов был один и весь технический, хотя слабым местом doc 00 называет и
behavioral-вопросы тоже. Поставка добавляет второй банк и **чередует** классы в
одной сессии (три и три), а заодно чинит побочный эффект, без которого добавление
банка выглядело бы придиркой: политика follow-up считала слабым ответ без цифр —
у behavioral-ответа цифр нет почти никогда.

Пункт 1 плана после 2026-08-12.
