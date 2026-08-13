# Active delivery status

- **slug:** glass-history-words
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** feature
- **repro_test:** n/a (kind=feature)
- **diagnosis:** n/a reason=не багфикс; предмет — вторая часть разреза, объявленного в поставке 1
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-13) reason=ожидания H1–H9 предъявлены до кода; визуальное направление утверждено макетом ещё в поставке 1, здесь оно применяется. Отдельно проговорено, что удаление legacy — самый рисковый шаг и снимки снимаются ПОСЛЕ него
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build` — правка фронта, собранное меняется (§6.5a)
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-ui2 (ветка feat/glass-history-words)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=только CSS и разметка; новых пакетов не требуется
- **runtime_paths:** frontend/src/styles/
  <!-- §12.6: экран отказывает пикселями, а не кодом ошибки. Удаление legacy —
       самый рискованный шаг: потерянный класс не увидит ни один тест. -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** H1, H5, H8 подтверждены в использовании — History читается
  строкой, слова и разбор в новом языке, ни один экран не потерял стилей
- **observe_until:** 2026-08-27
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Вторая из трёх поставок переработки интерфейса. History, Useful Words и разбор
переезжают на язык, введённый поставкой 1, и вместе с ними снимается временный
долг: legacy-часть `styles.css` удаляется целиком.
