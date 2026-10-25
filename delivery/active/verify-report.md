# Verify report: shutdown-leaks

**Date:** 2026-10-25
**Builder:** agent:claude-code (worktree `.claude/worktrees/agent-acb118d08a01f0c55`, ветка `fix/shutdown-leaks`)
**Verifier:** human:anthony
**asserts_reviewed_by:** deferred (reason=все 5 новых утверждений ведут к примерам E1–E2 — дайджест ниже; подпись примеров E1–E5 человеком на мерже вместе с human_ok_spec, после неё здесь n/a)
**CI run:** _заполняется после push_
**Commit:** спека `6c7083f`, repro `3a0b7d5`, правка `13839f6`, verify `75b3d47`, слияние с `main` `58b1a5c`, сверка документов с кодом #48 — следующий коммит

Verify прогнан дважды. Первый круг — на `main` `8d344d4` (#46 deps-refresh; ветка
отведена от `c1e4952` и до первого коммита сведена fast-forward, venv и node_modules
пересобраны по новым lock-файлам), под нагрузкой соседних сессий: load average 6–74.
Во время verify в `main` пришёл `5d7d7b7` (#48 talk-check-wiring: `_cancel_warmup` в
`ws_voice.py` стал `_cancel_background` и получил соседа `TalkChecks.cancel()`, +12
тестов). Он влит слиянием `58b1a5c` без конфликтов, lock-файлы не менялись; всё, что
зависит от дерева, перемерено на слитом дереве в тихой машине (load average 2–3).
Числа ниже — со слитого дерева, если не сказано иное.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| E1 | `test_shutdown_cancellation.py::test_shutdown_waits_until_a_cancelled_summary_returns_its_connection` | **PASS** — учёт соединений после выхода из lifespan пуст, в логе `summary task(s) cancelled by timeout`. До правки 5 из 5 красных: «1 соединени(й) выдано пулом и не возвращено…» + «1 соединени(й) открыто и не закрыто…» в теле, «не вернулось в пул» от стража канона в teardown |
| E2 | `test_shutdown_cancellation.py::test_shutdown_cancels_a_stuck_ws_cleanup_and_waits_for_it` | **PASS** — учёт пуст, в логе `ws cleanup(s) did not finish in time — cancelling`. До правки 5 из 5 красных: те же две строки в теле, «открыто и не закрыто» от нашего сторожа в teardown |
| E3 | `test_shutdown_summary.py::test_shutdown_waits_for_a_running_background_summary` | **PASS** без правки теста |
| E4 | `test_shutdown_summary.py::test_shutdown_gives_up_on_a_hung_summary_and_says_so` | **PASS** без правки теста — отмена зависшей модели теперь дожидается, размотка мгновенна |
| E5 | `test_ws_voice.py::test_disconnect_without_end_session_finishes_flow`, `::test_disconnect_during_turn_finishes_session` | **PASS** без правки тестов |
| repro | E1/E2 на коммите repro `3a0b7d5` (код до правки) / на коммите правки `13839f6` | **PASS** — история показывает тест раньше починки: на `3a0b7d5` оба красные, на `13839f6` оба зелёные |

## Мутации (правка обязана краснеть, и ровно там, где её сняли)

Скрипт мутаций — по одной, файл восстанавливается в `finally`, после всех пяти
`git diff` совпадает с коммитом правки. Прогон — три модуля: `test_shutdown_cancellation`,
`test_shutdown_summary`, `test_ws_voice` (16 тестов). Прогнан дважды — до слияния #48
под нагрузкой и на слитом дереве в тихой машине (E2 идёт через изменённый
`ws_voice.py`); результаты совпали полностью.

| Мутация | Ожидание | Результат |
|---|---|---|
| M1: `aclose()` отменяет без ожидания (как до правки) | красный ровно E1 | **E1 красный 3 из 3** (FAILED + ERROR в teardown), 15 зелёных |
| M2: `aclose()` ждёт отмену со сроком `SHUTDOWN_SUMMARY_TIMEOUT_S` | красный ровно E1 | **E1 красный 3 из 3**, 15 зелёных |
| M3: `_drain` без отмены (как до правки) | красный ровно E2 | **E2 красный 3 из 3**, 15 зелёных |
| M4: `_drain` отменяет без ожидания | красный ровно E2 | **E2 красный 3 из 3**, 15 зелёных |
| M5: `_drain` ждёт отмену со сроком `SHUTDOWN_DRAIN_TIMEOUT_S` | красный ровно E2 | **E2 красный 3 из 3**, 15 зелёных |

M2 и M5 — то, ради чего в тесте медленная размотка (decisions D5): с мгновенной
размоткой вариант «ждать отмену со сроком» краснел бы монеткой — в замере test-leaks
2 из ~45 под нагрузкой. С медленной M2 и M5 красные 3 из 3 и в тихой машине (load
average 2–3 на втором круге), то есть от нагрузки вердикт не зависит.

## Машинные гейты

| Гейт | Результат |
|---|---|
| `uv run pytest` 10 раз подряд (сьют + coverage-гейт 85) | **PASS 10 из 10** на слитом дереве — 324 passed и 95.92% в каждом; итог стражей канона одинаковый во всех десяти: «пул: взято 630, не вернулось 0 · утечек 0»; load average 2–3, сьют 5–6 s. До слияния #48 — тоже **10 из 10**: 312 passed, 95.81%, «пул: взято 540, не вернулось 0 · утечек 0», под load average 13–74, сьют 16–61 s |
| `./scripts/run_checks.sh` | **PASS** — размер модулей, `ruff check` (All checks passed), `ruff format --check` (102 файла), `mypy app` strict (58 файлов, 0 ошибок), pytest 324 passed, 95.92% |
| `STRICT=1 pre-commit run --all-files` | **PASS** — 28 хуков из 28, включая jscpd, слои, ратчет сложности, secrets |
| `bash delivery/evals/smoke/run.sh` | **PASS** — S1–S6 ok, S7 skip (сервер не поднят) |
| `python3 scripts/lint/contour_doctor.py` | **PASS** — `AUTO 47 · WEAK 17 · ABSENT 0 · TOOL 3 · SKIP 1 · DEAD 0` |
| `python3 scripts/delivery_check.py --diff-base origin/main` | **PASS** — 0 ошибок, 3 предупреждения ниже; предохранитель — 3 файла кода, +188/−4 (net +184) при пределах 25 / 800 |
| `python3 scripts/okf_sync_gate.py --base origin/main` | **PASS** (rc 0) — `model-split.md`: путь `backend/app/summary/service.py` тронут, концепт нет; drift разрешён `canon_drift_waiver` из STATUS |
| `python3 scripts/okf_validate.py` | **PASS** — 0 ошибок, 0 предупреждений, 13 файлов |
| классы риска §12.5 (тем же `risky_classes`, что гейт) | транзакция БД (`rollback`), производительность (`json.dumps`), новый модуль (`test_shutdown_cancellation`) — разобраны в «Ревью рисковых мест» |

### Оставшиеся предупреждения

- **`human_ok_spec: deferred`** и **`asserts_reviewed_by: deferred`** — подпись примеров
  E1–E5 человеком на мерже; до неё `phase` остаётся `verify`.
- **Реляционный оракул (§6.5)** — решение человека 2026-08-12: зависимость для
  тестов-свойств не добавляется.

## Изменение поверхности модели (§14.1)

- `backend/app/summary/service.py` — задет путь поверхности, но не поведение модели:
  изменён только `SummaryService.aclose()` (порядок гашения — отменить и дождаться
  отмены). Промпты, `SCHEMA_HINT`, модели (`ollama_model_review` /
  `ollama_model_interview`), параметры сэмплирования и бюджеты разбора не тронуты; что
  уходит в модель и что из неё принимается — побайтно прежнее. Оракулы §6.5b и
  дифференциальный прогон не нужны: поверхность, которую они судят, не менялась.
  at=2026-10-25

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` — с причиной в STATUS: отказ обеих дверей гашения теперь виден
сьюту. E1/E2 исполняют настоящий lifespan, настоящую ws-сессию и настоящий пул
SQLAlchemy над aiosqlite; состояние «задача держит соединение в момент гашения» тест
ставит сам (`holding`), поэтому вердикт не зависит от планировщика: 5 из 5 до правки
на macOS, вторая среда — workflow `CI` на ubuntu (строка «CI run» в шапке).
Linux-контейнер не поднят: демон Docker на машине не запущен, а поднимать ВМ на машине,
которую делят соседние сессии, исполнитель не стал. at=2026-10-25

## Ревью рисковых мест (§12.5)

0. **Что смотрел:** дифф целиком — `SummaryService.aclose()` в
   `backend/app/summary/service.py`, `_drain` в `backend/app/main.py`, новый
   `backend/tests/test_shutdown_cancellation.py` (`StuckOnFinalWrite`,
   `_hold_connection`, `SLOW_UNWIND_S`); соседей правки — `ws_session` и
   `_SessionHandler.aclose()` / `_cancel_background` в `ws_voice.py`,
   `TalkChecks.cancel()` в `voice/talk_checks.py` (оба — в виде после слияния #48),
   `_safe_full` в `summary/service.py`, `Database.session()`, `AsyncSession.__aexit__`
   и `AsyncEngine.dispose()` SQLAlchemy 2.0.51.
1. **транзакция БД** (поднят словом `rollback` в докстрингах) — правка меняет не
   транзакцию, а МОМЕНТ `dispose()` относительно размотки: `rollback` и возврат
   соединения делает `AsyncSession.__aexit__` (`create_task(self.close())` под
   `asyncio.shield`), и `await asyncio.wait(pending)` только дожидается, пока он
   закончится. Что может сломаться: задача, глотающая `CancelledError`, держала бы
   гашение — на путях обеих дверей таких нет (`_safe_full` ловит `Exception`, а
   `_cancel_background` глотает отмену уборки лишь пока ждёт снятие прогрева и
   проверки речи, затем доходит до конечной записи `finish`; задача проверки речи в
   базу не пишет); выход процесса такую задачу ждал бы и без правки (`asyncio.run`).
   Сами записи (`set_debrief`, `finish`) и репозитории не тронуты.
2. **производительность** (поднят `json.dumps` в новом тесте) — риска нет, потому что
   `json.dumps(SUMMARY)` — подготовка ответа фейковой модели в теле теста, не путь
   продукта; в `backend/app` выборок и разбора в цикле дифф не добавляет. Время
   гашения в штатном случае не меняется (`if not pending: return` раньше отмены); в
   застрявшем — срок плюс размотка, которую процесс и так ждал на выходе.
3. **новый модуль** (`test_shutdown_cancellation`) — что может сломаться: (а) ложный
   зелёный, если задача не успела взять соединение к гашению — закрыто ожиданием
   `holding` до выхода из lifespan; (б) ложный красный от сборщика мусора в чужом
   тесте — на правленном коде утечки нет, полный сьют зелёный 10 из 10; в красном
   состоянии (мутации) сторож называет виновника синхронно; (в) зависимость от
   соседних модулей: модуль берёт `GoneClientWebSocket`, `make_container`,
   `MINIMAL_SUMMARY` и не правит ни `fakes.py`, ни `helpers.py`, которые меняют
   соседние PR #44 и #48 (#48 слит во время поставки, слияние без конфликтов).
4. **строки лога** — `did not finish in time` и `cancelled by timeout` сохранены
   дословно (их ищет наблюдение `ws-disconnect-hang`) и утверждаются тестами E1/E2:
   переименование покраснело бы здесь, а не тихо обнулило бы сигнал наблюдения.

## Spec coverage gaps

- `contextlib.suppress(CancelledError)` вокруг ожидания отменённой задачи глотает и
  отмену того, кто ждёт, — `_cancel_background` в `ws_voice.py` и `TalkChecks.cancel()`
  в `voice/talk_checks.py` (второй пришёл с PR #48 во время поставки, то есть шаблон
  копируется). Уборку это не вешает — она доходит до конечной записи, — но отмена
  обработчика посреди `_on_utterance_end` тоже была бы проглочена. Не тронуто (spec,
  out of scope; голосовой путь, `ws_voice.py` — поверхность модели); кандидат в
  следующую поставку вместе с общим помощником на все четыре сайта (plan, D4).
- Уборки, начатые после того, как `_drain` снял свой список, гашение не ждёт —
  записано, не тронуто.
- Живое гашение `./scripts/dev.sh` — по «запускай» (`eval-smoke.md`, отложено).
- Linux-контейнер не поднят; linux — только workflow `CI` на ubuntu.

## Уроки

- **L102:** срок на ожидании отмены не ограничивает ничего, а только переставляет
  шаги. Выход процесса под uvicorn — `asyncio.run`, и тот на выходе отменяет и ждёт
  оставшиеся задачи без срока; `AsyncEngine.dispose()` при этом выданные соединения
  не закрывает и не ждёт (SQLAlchemy так и документирует), а при пустой очереди пула
  не уступает циклу ни разу. Значит «отменить и не дождаться» — не гонка с
  `dispose()`, а детерминированный проигрыш, и выход процесса от этого не короче.
- **L103:** утечку «под нагрузкой» делает детерминированной замедление того, что под
  нагрузкой медленно. Размотка отмены 0.2 s в управляемом репозитории превратила
  «2 из ~45 на занятой машине» из замера test-leaks в красный на каждом прогоне у
  обоих вариантов «ждать отмену со сроком» (M2, M5). Управляемость (L60) — это не
  только «где остановить», но и «сколько длится уборка после остановки».
- **L104:** строка лога, которую читает открытое наблюдение, — интерфейс, а не текст.
  Сигнал `ws-disconnect-hang` — «в логе гашения нет `did not finish in time` /
  `cancelled by timeout`»; переименуй строку — и наблюдение позеленеет по построению.
  Перед правкой текста лога — `git grep` по `observe_signal` архивных STATUS, а
  нужная подстрока — под утверждением теста.

## Verdict

- [x] **READY FOR HANDOFF** — E1–E5 и repro зелёные; мутации M1–M5 краснят ровно свои
      тесты; машинные гейты — таблица выше; переход в `handoff` ждёт подписи примеров
      E1–E5 человеком (`human_ok_spec: deferred`)
- [ ] NEED CONVERGE
- [ ] BLOCKED

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **5**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
E1	assert leaks == []  # E1: к концу гашения соединение возвращено и закрыто
E1	assert "summary task(s) cancelled by timeout" in caplog.text  # E1: отмена названа
E2	assert ws.sent[0]["type"] == "session_started"  # E2: сессия была, уборке было что писать
E2	assert leaks == []  # E2: к концу гашения соединение возвращено и закрыто
E2	assert "ws cleanup(s) did not finish in time" in caplog.text  # E2: срок назван в логе
```

asserts_without_example: 0

Строку дайджеста «примеры человек подписал до кода» эта поставка пока не заслужила:
примеры E1–E5 написаны и закоммичены до кода (`6c7083f` раньше `3a0b7d5`), но подпись
человека под ними будет на мерже (`human_ok_spec: deferred`). Поэтому
`asserts_reviewed_by` — `deferred`, а не `n/a`.

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 3 code (+6 process docs) / +188/-4 (net +184) |
| commits | 3 |
| time_to_accepted_spec | spec drafted, not yet accepted |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — backend/tests/test_shutdown_cancellation.py (новый оракул) |
| implement_retries | 0 — правка зелёная с первого прогона; медленная размотка в тесте (D5) добавлена ДО правки, на красном repro, а не после провала. `ruff format` переложил одну строку лога в `main.py` — форма, не переделка |
| verify_fails_before_green | 0 — локальный verify зелёный с первого полного прогона (10 из 10); CI — строка «CI run» в шапке |
| est_token_or_cost | n/a — не измерялось; локальные прогоны, внешних платных вызовов и модели нет |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
