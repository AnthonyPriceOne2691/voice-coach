# Verify report: test-leaks

**Date:** 2026-10-23
**Builder:** agent:claude-code (worktree `.claude/worktrees/agent-a30a52584f9fc3c47`, ветка `fix/test-leaks`)
**Verifier:** human:anthony
**asserts_reviewed_by:** n/a (все 15 новых утверждений ведут к примерам W3–W7 — дайджест ниже; сами примеры человек подписывает на мерже, `human_ok_spec: deferred`)
**CI run:** заполняется после push (PR в `main`)
**Commit:** код — `82b7848` (сторож `9fe3eac`, починка `8b4fbf0`, строгий рантайм `82b7848`), записи контура — `24c8f29`

Машина весь день под нагрузкой соседних сессий: load average 19 → 210, swap 6.2 из
7 GB. Время прогонов поэтому не показатель (сьют с coverage — от 8 до 151 s);
показатель — детерминизм, и нагрузка для него скорее строже, чем тише.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| W1 | сбор под `error`; мутация M4b (строка ignore снята) | **PASS** — сбор проходит во всех модулях, предупреждений 0; без строки — `Interrupted: 7 errors during collection` (`test_rest_api`, `test_shutdown_summary`, `test_ws_meta`, `test_ws_pace`, `test_ws_prosody`, `test_ws_talk`, `test_ws_voice`) |
| W2 | 10 полных прогонов подряд с coverage | **PASS** — linux-контейнер `python:3.12-slim` (Python 3.12.15, SQLAlchemy 2.0.51, aiosqlite 0.22.1, pytest 9.1.1): **10 из 10**, 277 passed, 95.64% в каждом; macOS (Python 3.12, тот же `uv.lock`): **10 из 10**, 277 passed, 95.64% в каждом, 58–151 s на прогон под load average 100–200 |
| W3 | `test_engine_without_dispose_is_named`; мутация M1 | **PASS** — M1 (фикстура `db` без владельца): ровно 16 тестов красные в teardown, 3 прогона из 3, набор одинаковый |
| W4 | `test_connection_taken_and_not_returned_is_named`; мутация MG2 | **PASS** |
| W5 | `test_in_memory_engine_without_dispose_is_named` | **PASS** — у `StaticPool` нет `checkedout()`, сторож видит утечку |
| W6 | `test_owned_database_leaves_nothing_and_ledger_detaches`; мутация MG3 | **PASS** |
| W7 | `test_connection_opened_in_another_thread_is_seen`; мутация M2 | **PASS** — M2 (lifespan без `db.dispose()`): 44 теста с приложением красные, 2 прогона, набор одинаковый |
| repro | `test_storage.py::test_interview_lifecycle` на `9fe3eac` / `8b4fbf0` | **PASS** — на коммите сторожа ERROR в teardown («1 соединени(й) открыто и не закрыто…»), сьют `277 passed, 18 errors` — ровно 18 виновников; на коммите починки — зелёный |

## До и после

| | до (`73342b3` + `error`) | после |
|---|---|---|
| красных на прогон, без coverage | 5 (5 прогонов, набор один) | 0 |
| красных на прогон, с coverage | 5 + 1 ошибка setup (6 прогонов) — ДРУГИЕ тесты | 0 |
| тестов, оставляющих соединение открытым (приписка по событиям пула) | 18 | 0 |
| из упавших — не виновных вовсе | 2 из 5 (`test_tts_piper.py` базы не касается) | — |
| тестов в сьюте | 272 | 277 |
| покрытие | 95.64% | 95.64% (продуктовый код не тронут) |

## Мутации (сторож обязан краснеть, и ровно там, где течёт)

Сьют-мутации прогнаны с заглушённым каналом сборщика мусора
(`-W ignore::pytest.PytestUnraisableExceptionWarning`), чтобы мерить сторож, а не
монетку. M1 повторён и с настоящим конфигом.

| Мутация | Ожидание | Результат |
|---|---|---|
| M1: фикстура `db` без владельца (как была) | красные ровно тесты на `db` | **16 красных, 3 из 3 прогонов, набор одинаковый**. С настоящим конфигом — те же 16 ошибок сторожа плюс 3 падения от сборщика мусора, и одно из них — снова `test_tts_piper.py`: сторож указывает на виновных, канал `error` — на прохожего |
| M2: lifespan без `await resolved.db.dispose()` | красные все тесты, поднимающие приложение с базой (TestClient — в своём потоке) | **44 красных, 2 из 2, набор одинаковый** (`test_ws_voice` 12, `test_ws_talk` 10, `test_rest_api` 8, `test_ws_pace` 5, `test_ws_meta` 4, `test_ws_prosody` 3, `test_shutdown_summary` 2) |
| M3: `owned_database` без `dispose()` | красные все, кто читает или сеет через владельца | **45 красных, 2 из 2, набор одинаковый** |
| M4b: строка ignore starlette снята | сбор падает | **7 ошибок сбора** (W1) |
| MG1: учёт не слышит `connect` | W3, W5, W7 красные | **3 красных** — ровно они |
| MG2: учёт не слышит `checkout` | W4 красный | **1 красный** — он |
| MG3: учёт не снимает слушателей | W6 красный | **1 красный** — он |
| MG4: учёт не слышит `close` | все тесты сторожа красные (закрытие не видно) | **5 красных** |

M4 до разделения модулей (conftest импортировал `helpers.py`, а тот —
`starlette.testclient`) дал не 7 ошибок сбора, а `ImportError while loading
conftest`, `rc=4` — весь прогон разом. Отсюда `tests/db_lifecycle.py` (D4).

## Машинные гейты

| Гейт | Результат |
|---|---|
| `uv run pytest` (сьют + coverage-гейт 85) | **PASS** — 277 passed, 95.64% |
| `ruff check app tests`, `ruff format --check app tests` | **PASS** — 92 файла |
| `mypy app` (strict) | **PASS** — 55 файлов, 0 ошибок |
| `python3 scripts/check_module_size.py` | **PASS** — все файлы ≤ 500 строк (самый длинный из новых — `test_connection_guard.py`, 120) |
| `STRICT=1 pre-commit run --all-files` | **PASS** — 28 хуков из 28, включая jscpd, слои, ратчет сложности, secrets |
| `bash delivery/evals/smoke/run.sh` | **PASS** — S1–S6 ok, S7 skip (сервер не поднят) |
| `python3 scripts/lint/contour_doctor.py` | **PASS** — `AUTO 46 · WEAK 17 · ABSENT 0 · TOOL 3 · SKIP 1 · DEAD 0` |
| `python3 scripts/delivery_check.py --diff-base origin/main` | **PASS** — 0 ошибок; предохранитель — 9 файлов кода, +352/−84 (net +268) при пределах 25 / 800 (`adapted.json` — механика контура, в объём не входит; метрики ниже считают его десятым); 2 предупреждения ниже |
| стоимость сторожа | ~1.2 ms на тест под load average ~200 (6 подписок на событие и их снятие; лучший из 5 × 2000 циклов) — ~0.34 s на сьют |

### Оставшиеся предупреждения

- **`human_ok_spec: deferred`** — подпись примеров W1–W7 на мерже (решение
  human:anthony 2026-10-23).
- **Реляционный оракул (§6.5)** — решение человека 2026-08-12, зависимость для
  тестов-свойств не добавляется.

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` — продуктовый код не тронут: `git diff --stat origin/main --
backend/app` пуст. Пути гашения приложения сторож проверил, но не менял: две скрытые
утечки (H5 в `diagnosis.md`) переданы следующей поставке. at=2026-10-23

## Ревью рисковых мест (§12.5)

0. **Что смотрел:** дифф целиком — `backend/tests/db_lifecycle.py`
   (`ConnectionLedger`, `owned_database`), `backend/tests/conftest.py`
   (`_no_leaked_connections`, фикстура `db`), `backend/tests/helpers.py`
   (`load_interview`, `fetch_interview`, `seed_finished_interview`), четыре тестовых
   модуля, блок `filterwarnings` в `backend/pyproject.toml`, записи
   `scripts/lint/adapted.json` и `delivery/STACK-ACCEPTANCE.md`.
1. **новый модуль** (`db_lifecycle`, `conftest`, `test_connection_guard`) — что может
   сломаться: сторож может (а) молчать при утечке — закрыто тестами W3–W7 и мутациями
   MG1–MG4, где снятие каждого события роняет ровно свои тесты; (б) краснить зря —
   закрыто 10 + 10 зелёными прогонами на двух платформах; (в) копить слушателей на
   классе `Pool` — закрыто W6 и MG3. Порядок teardown держит pytest: autouse
   поднимается первым и сворачивается последним, после `db`, TestClient и lifespan.
2. **транзакция БД** — риска нет, потому что ни одной транзакции дифф не меняет:
   репозитории и `async with db.session()` в `backend/app` не тронуты; `owned_database`
   только гасит движок (`dispose()` в `finally`), а фикстура `db` делает то же, что
   прежняя, плюс teardown, которого у прежней не было.
3. **интеграция** (`httpx`) — риска нет, потому что слово пришло строкой ignore в
   `filterwarnings`: тест-клиент starlette по-прежнему работает на `httpx`, поведение
   не меняется, а строка гасит ровно одно предупреждение с импорта по тексту
   сообщения. Если starlette сменит текст — строка перестанет совпадать, и сбор
   покраснеет громко (M4b), а не молча.
4. **цепочка гейтов** (`scripts/lint/adapted.json`) — меняется только текст записи
   адаптации `backend/pyproject.toml`; скрипты гейтов, их снимки и конфиги не
   тронуты. Доктор после правки — DEAD 0.

## Spec coverage gaps

- Пути гашения приложения — сторож нашёл там утечки, но эта поставка их не чинит
  (D5): репро и проверенная правка — в `diagnosis.md`, H5.
- `scripts/repair_vocabulary.py` не гасит свой движок (процесс выходит,
  `ResourceWarning` на выходе) — разовый скрипт без тестов, записано, не тронуто.

## Уроки

- **L88 (предварительно):** «канонный рецепт поставлен» и «класс закрыт» — не одно и
  то же. Фикстура `checkedout() == 0` из CQG §2.7 здесь не нашла бы НИ ОДНОЙ из 18
  утечек: у всех соединение возвращено в пул, а пул не закрыт, и 16 из 18 — на
  `StaticPool`, у которого `checkedout()` нет. Сторож должен слушать обе стороны
  жизни соединения: открыто → закрыто и выдано → возвращено. Кандидат в полевой
  отчёт канону.
- **L89 (предварительно):** под `filterwarnings = ["error"]` красный тест от
  предупреждения сборщика мусора указывает на ПРОХОЖЕГО: движок держится
  циклическими ссылками и собирается там, где сработал порог поколения. Замер: 18
  виновников, 5 упавших, из них 2 не виновны вовсе (`test_tts_piper.py` базы не
  касается); набор менялся от включения coverage. Прежде чем читать упавший тест —
  приписать ресурс тесту, который его открыл (события пула, а не трассировка
  `__del__`).
- **L90 (предварительно):** «отменить» и «дождаться отмены» — два шага, и второй не
  терпит короткого срока. Пути гашения, отменяющие задачу без ожидания, оставляют
  соединение вне пула 10 из 10; ожидание отмены со сроком 50 ms — всё ещё 2 из ~45
  под нагрузкой; без срока — 0 из 80. Это D4 `ws-disconnect-hang`, которое тот же
  `aclose()` не соблюдает.

## Verdict

- [x] **READY FOR HANDOFF** — W1–W7 и repro зелёные; 10 из 10 прогонов на двух
      платформах; машинные гейты зелёные по правилам delivery@2.06 · cqg@2.69;
      `quality` и `CI` на ветке — строка «CI run» в шапке
- [ ] NEED CONVERGE
- [ ] BLOCKED

Долг до мержа: `human_ok_spec: deferred` — подпись человека под примерами W1–W7
(решение human:anthony 2026-10-23: подписывает на мерже). Строка дайджеста ниже
«примеры человек подписал до кода» станет правдой только с этой подписью: пока
утверждения привязаны к примерам, которые ещё никто, кроме исполнителя, не читал.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **15**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
W3	assert not problems, "; ".join(problems)  # W3, W4, W5, W7
W3	assert lent_by_pool == 0  # W3: канонной фикстуре здесь нечего увидеть
W3	assert len(found) == 1  # W3
W3	assert found[0].startswith("1 соединени(й) открыто и не закрыто")  # W3
W3	assert NOT_DISPOSED in found[0]  # W3: причина названа, а не только число
W3	assert after == []  # W3: dispose() закрывает соединение, учёт это видит
W4	assert any(NOT_RETURNED in problem for problem in found)  # W4
W4	assert found[0].startswith("1 соединени(й) выдано пулом")  # W4
W4	assert after == []  # W4
W5	assert not pool_can_tell  # W5: канонной фикстуре нечего спросить у этого пула
W5	assert len(found) == 1 and NOT_DISPOSED in found[0]  # W5
W6	assert quiet == []  # W6
W6	assert after_exit == []  # W6
W7	assert len(found) == 1 and NOT_DISPOSED in found[0]  # W7
W7	assert after == []  # W7
```

✅ **Каждое утверждение ведёт к примеру спеки** (W3 W4 W5 W6 W7), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 10 code (+6 process docs) / +353/-85 (net +268) |
| commits | 5 |
| time_to_accepted_spec | spec drafted, not yet accepted |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — backend/tests/conftest.py (новый оракул), backend/tests/db_lifecycle.py (новый оракул), backend/tests/test_connection_guard.py (новый оракул), scripts/lint/adapted.json |
| implement_retries | 1 — мутация M4 показала, что conftest через `helpers.py` тянет `starlette.testclient`: без строки ignore падала загрузка conftest, то есть весь прогон; учёт и владелец вынесены в `tests/db_lifecycle.py` (D4) |
| verify_fails_before_green | 0 — локальный verify зелёный с первого полного прогона после починки (10 + 10); CI — строка «CI run» в шапке |
| est_token_or_cost | n/a — не измерялось; локальные прогоны и контейнер, внешних платных вызовов нет |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
