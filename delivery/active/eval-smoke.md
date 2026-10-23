# Eval smoke — test-leaks

Derived from spec acceptance (W1–W7). Run during verify, 2026-10-23. Машина под
нагрузкой соседних сессий (load average 19 → 210 за день): время прогонов — не
показатель, детерминизм — показатель.

## Оракулы поставки

- [x] **W1** строгий рантайм: `filterwarnings = ["error"]` и одна строка ignore канона;
      сбор проходит во всех модулях, сьют без единого предупреждения. Строка ignore
      снята (мутация M4b) — `Interrupted: 7 errors during collection`: `test_rest_api`,
      `test_shutdown_summary`, `test_ws_meta`, `test_ws_pace`, `test_ws_prosody`,
      `test_ws_talk`, `test_ws_voice`
- [x] **W2** 10 полных прогонов подряд с coverage: macOS — **10 из 10 зелёных**
      (58–151 s на прогон под load average 100–200); linux-контейнер
      `python:3.12-slim` (Python 3.12.15) — **10 из 10 зелёных**; везде 277 passed,
      покрытие 95.64%
- [x] **W3** пул не закрыт при возвращённых соединениях — тест сторожа
      `test_engine_without_dispose_is_named`; мутация M1 (фикстура `db` без владельца)
      — ровно 16 тестов красные в teardown на 3 прогонах из 3, набор одинаковый
- [x] **W4** соединение выдано и не возвращено —
      `test_connection_taken_and_not_returned_is_named`; мутация учёта MG2 его роняет
- [x] **W5** `StaticPool` (`:memory:`) без `checkedout()` —
      `test_in_memory_engine_without_dispose_is_named`
- [x] **W6** чистая работа — тишина, слушатели снимаются —
      `test_owned_database_leaves_nothing_and_ledger_detaches`; мутация MG3 (не
      снимать слушателей) его роняет
- [x] **W7** другой поток и цикл — `test_connection_opened_in_another_thread_is_seen`;
      мутация M2 (lifespan без `db.dispose()`) — 44 теста с приложением красные, набор
      одинаковый на 2 прогонах

## Repro (§3.1c)

- [x] `backend/tests/test_storage.py::test_interview_lifecycle` на коммите сторожа
      `9fe3eac` (тесты ещё не починены) — ERROR в teardown «1 соединени(й) открыто и не
      закрыто: движок без `dispose()`…»; сьют на нём `277 passed, 18 errors` — ровно
      18 виновников. На `8b4fbf0` (починка) — зелёный.

## Продуктовые оракулы (не должны шелохнуться)

- [x] `bash delivery/evals/smoke/run.sh` — S1–S6 ok, S7 skip (сервер не поднят)
- [x] `backend/app/**` не тронут ни строкой — `git diff --stat origin/main -- backend/app`
      пуст; фронт не тронут — сборка не меняется
