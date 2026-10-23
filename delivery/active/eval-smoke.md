# Eval smoke — test-leaks

Derived from spec acceptance (W1–W7). Run during verify, 2026-10-23, дважды: на базе
`73342b3` (cqg@2.69) и после слияния с `main` на `a4a0dce` (cqg@2.74, страж пула
канона в `addopts`). Числа ниже — с дерева после слияния с `main`, если не сказано иное.
Первая половина дня — под нагрузкой соседних сессий (load average до 210), вторая —
в тихой машине: время прогонов не показатель, детерминизм — показатель.

## Оракулы поставки

- [x] **W1** строгий рантайм: `filterwarnings = ["error"]` и одна строка ignore канона;
      сбор проходит во всех модулях, сьют без единого предупреждения — и вместе со
      стражами канона (`-p run_sentinels`). Строка ignore снята (мутация M4b) —
      `Interrupted: 8 errors during collection`: `test_rest_api`,
      `test_shutdown_summary`, `test_ws_meta`, `test_ws_pace`, `test_ws_prosody`,
      `test_ws_sentinels`, `test_ws_talk`, `test_ws_voice` (до наката — 7)
- [x] **W2** 10 полных прогонов подряд с coverage: macOS на дереве после слияния с `main` —
      **10 из 10**, 280 passed, 95.64%; до слияния с `main` — macOS **10 из 10** и
      linux-контейнер `python:3.12-slim` (Python 3.12.15) **10 из 10**, 277 passed.
      После слияния с `main` linux — workflow `CI` на ubuntu (контейнер повторить не
      удалось: демон Docker остановился во время сессии)
- [x] **W3** пул не закрыт при возвращённых соединениях — тест сторожа
      `test_engine_without_dispose_is_named`; мутация M1 (фикстура `db` без владельца)
      — ровно 16 тестов красные в teardown на 3 прогонах из 3, набор одинаковый
- [x] **W4** соединение выдано и не возвращено —
      `test_connection_taken_and_not_returned_is_named`; мутация учёта MG2 его роняет.
      В полном сьюте при такой утечке срабатывает и страж канона: отчёт teardown один,
      сообщение канона («не вернулось в пул») заменяет наше (временный тест, удалён)
- [x] **W5** `StaticPool` (`:memory:`) без `checkedout()` —
      `test_in_memory_engine_without_dispose_is_named`
- [x] **W6** чистая работа — тишина, слушатели снимаются —
      `test_owned_database_leaves_nothing_and_ledger_detaches`; мутация MG3 (не
      снимать слушателей) его роняет
- [x] **W7** другой поток и цикл — `test_connection_opened_in_another_thread_is_seen`;
      мутация M2 (lifespan без `db.dispose()`) — 47 тестов с приложением красные, набор
      одинаковый на 3 прогонах (до наката — 44)

## Repro (§3.1c)

- [x] `backend/tests/test_storage.py::test_interview_lifecycle` на коммите сторожа
      (тесты ещё не починены) — ERROR в teardown «1 соединени(й) открыто и не закрыто:
      движок без `dispose()`…»; сьют на нём — ровно 18 виновников. После починки —
      зелёный. На дереве после слияния с `main` повторено: три модуля возвращены к виду до
      починки — `280 passed, 18 errors`, те же 18.

## Страж пула канона на тех же утечках (H7)

- [x] Дерево после слияния с `main`, три модуля до починки, наш сторож заглушён: **0
      красных**, итог стража канона «пул: взято 537, не вернулось 0 · утечек 0». Наш
      сторож на том же дереве — 18.

## Продуктовые оракулы (не должны шелохнуться)

- [x] `bash delivery/evals/smoke/run.sh` — S1–S6 ok, S7 skip (сервер не поднят)
- [x] `backend/app/**` диффом поставки не тронут — `git diff --stat origin/main --
      backend/app` пуст; фронт не тронут — сборка не меняется
