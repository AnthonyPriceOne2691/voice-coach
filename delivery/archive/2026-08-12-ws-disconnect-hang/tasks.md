# Tasks

- [x] T1. Worktree `fix/ws-disconnect` от `main`
- [x] T2. **Воспроизвести** вис вне CI: Linux-контейнер, тот же Python 3.12 →
      6 висов из 10 (macOS: 0 из 60). Цикл диагностики 40 с вместо 6 ч
- [x] T3. Дамп незавершённых задач в момент `_cancel_all_tasks` → причина:
      `AsyncAdapt_aiosqlite_connection._terminate_graceful_close`, соединение
      вне пула. Журнал гипотез — `diagnosis.md` (H1 отвергнута замером)
- [x] T4. Уборка сессии под `shield` + таймаут; ссылка на задачу — в состоянии
      приложения, чтобы гашение её дождалось
- [x] T5. `_warmup_task` получает владельца: отмена + `await` на всех путях
      (disconnect, `end_session`, естественный конец)
- [x] T6. Lifespan ждёт живые уборки и `summaries.aclose()` до `db.dispose()`
- [x] T7. Снять `skipif(CI)` с двух тестов; добавить регрессионный тест на
      инвариант «отключение завершает сессию»
- [x] T8. **Проверить repro**: новый тест на СТАРОМ коде → 6 красных/висов из 6
      (`assert row.ended_at is not None` → `None`)
- [x] T9. Замер после фикса: 10 прогонов сьюта на linux — 0 висов; полный сьют
      92 теста / 93.25%; ruff, ruff format, mypy strict, module size — зелёные
- [x] T10. Приёмка: pre-commit целиком, smoke-оракулы, `verify-report.md`
      + блок метрик (§9.2) с заполненными MANUAL-полями
- [ ] T11. PR #4, `quality` + `CI` зелёные на `97e05ba`; остаётся
      `human_ok_spec: yes` (подпись человека) и мерж через `merge_guard`
