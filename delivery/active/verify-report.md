# Verify report

**Date:** 2026-08-12
**Verifier:** agent:claude-code (прогоны) + human:anthony (приёмка ветки)
**asserts_reviewed_by:** n/a (все утверждения ведут к одобренным примерам)
**Commit:** ветка `fix/ws-disconnect-mid-turn`

## Что чинилось

Разрыв соединения посередине хода не завершал сессию: `ended_at` оставался
пустым навсегда. Разбор — `active/diagnosis.md`. Дефект **старый**, поставкой
`ws-disconnect-hang` не вносился (замер: `git diff 6a6132e 70c6d15 --
backend/app/api/ws_voice.py` меняет 52 строки, ни одной в `_on_utterance_end`,
`_error`, `_send`).

## Правка — одна, и это результат замера, а не первоначальный план

Спека объявляла ДВЕ правки: проброс `WebSocketDisconnect` и защиту `_send` от
отправки в мёртвый сокет. Перед фиксацией обе прогнаны по отдельности:

| Вариант | Сьют |
|---|---|
| только `except WebSocketDisconnect: raise` | **10 passed** |
| только проверка состояний в `_send` | **1 failed** |
| обе | 10 passed |

Несущая — проброс; проверка в `_send` репро не закрывает. **Она снята**, и это
не экономия строк: с ней сервер доигрывает весь ход (LLM + TTS) для ушедшего
клиента, а без неё обрывается на первой же отправке. Реплика пользователя
сохраняется в обоих случаях — она пишется до отправки. Подписанная граница
поставки тем самым **сузилась**, о чём сказано человеку до мержа, а не после.

## Assertion digest (ревью ожиданий, не кода)

Вывод `scripts/lint/assert_digest.sh` дословно:

```
База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **6**, из них без ссылки на пример спеки: **0**.

B1	assert escaped is None, f"из ws_session вылетело {escaped!r}"
B1	assert row is not None  # B1
B1	assert row.status == "in_progress"  # B1
B1	assert row.ended_at is not None  # B1, B2
B1	assert [t["role"] for t in json.loads(row.transcript_json)] == ["agent", "user"]
B3	assert "voice turn failed" not in caplog.text  # B3

asserts_without_example: 0
```

Каждое утверждение ведёт к примеру спеки, а примеры подписаны человеком ДО кода
(`human_ok_spec: yes`, at=2026-08-12), поэтому отдельной подписи под дайджестом
не требуется.

## Shape oracles

- [x] PASS — `ruff check` / `ruff format --check` (63 файла) / `mypy` strict (45 файлов)
- [x] PASS — module size ≤ 500 LOC
- [x] PASS — `pre-commit run --all-files`

## Behavior oracles

- [x] PASS — **B1** `test_disconnect_during_turn_finishes_session`: из `ws_session`
      ничего не вылетает, `status = in_progress`, `ended_at` заполнен, транскрипт
      содержит обе реплики
- [x] PASS — **B2** тот же тест на коде ДО фикса: **3 красных из 3**, сообщение
      `AssertionError: из ws_session вылетело RuntimeError('Cannot call "send"
      once a close message has been sent.')` — та же ошибка, что в браузерном логе
- [x] PASS — **B3** `voice turn failed` в логе отсутствует
- [x] PASS — **B4** `test_stt_empty_recoverable` и `test_decode_failure_is_recoverable`
      зелёные: живой клиент по-прежнему получает `recoverable`-ошибки
- [x] PASS — **B5** `test_disconnect_without_end_session_finishes_flow` зелёный —
      инвариант прошлой поставки не сломан
- [x] PASS — сьют: **93 passed, покрытие 93.03%** (гейт 85)
- [x] PASS — linux-контейнер (python 3.12.13, версия раннера): **5 прогонов из 5
      зелёных, 0 висов** — регрессия на путь завершения ws не внесена (урок L5)

## Product oracles

- [x] PASS — `delivery/evals/smoke/run.sh`
- [x] PASS — **B6, половина данных**: браузер, закрытие вкладки в `Thinking…` —
      `ended_at` заполнен; в логе бэкенда **0** строк `Exception in ASGI
      application`, **0** `voice turn failed`, **0** `did not finish`
- [ ] **B6, половина UI — НЕ ПРОВЕРЕНА, и не по вине этой поставки.** Увидеть
      сессию в History нельзя: фронт зовёт `/sessions` и `/vocabulary`, а
      `frontend/vite.config.ts` проксирует только `/api`, `/health`, `/ws`.
      Запрос падает в SPA-fallback (замер со страницы: `fetch('/sessions/
      interviews')` → `200`, тело `<!doctype html>`), `response.json()` бросает,
      вкладка показывает «Failed to load history». Бэкенд статику не отдаёт,
      то есть в единственном поддерживаемом запуске (`scripts/dev.sh`) вкладки
      History и Useful Words мертвы **всегда**, независимо от этой правки.
      Решение человека 2026-08-12: чинить **отдельной поставкой**, эту не
      расширять. Пробел назван, а не закрыт.

## Исполнение рисковых путей (§12.6)

`runtime_paths: backend/app/api/ws_voice.py` — путь завершения ws-сессии. Один
путь, порог §12.6 не превышен, подпись breaker'а не требуется (проверено до
работы, урок L6).

| Что исполнял | Чем | Что увидел | at |
|---|---|---|---|
| разрыв посередине хода, ДО фикса | браузерный стенд `drive2.py` (Chromium 151, VAD/MediaRecorder/ws/whisper/qwen2.5/Piper настоящие, имитирован микрофон) | `ended_at = null`, **2 прогона из 2**; в логе `Exception in ASGI application` | 2026-08-12 |
| он же, ПОСЛЕ фикса | тот же стенд | `ended_at` заполнен, **2 прогона из 2**; в логе ноль необработанных исключений | 2026-08-12 |
| сьют целиком на linux | docker, python 3.12.13, 5 прогонов | 93 passed × 5, 0 висов | 2026-08-12 |

Почему стенд, а не `TestClient`: тест-клиент на закрытии **отменяет** задачу
приложения (замер: внутрь STT прилетает `CancelledError`), uvicorn — нет. Это
же выяснение стоило одной переделки теста и записано уроком.

## Ревью рисковых мест (§12.5)

0. **Что смотрел:** дифф целиком — `backend/app/api/ws_voice.py`
   (`_on_utterance_end`, `_send`), `backend/tests/test_ws_voice.py` (новый тест),
   `backend/tests/fakes.py` (`GoneClientWebSocket`, `TabClosingStt`).

1. **Проброс меняет поток управления в обработчике ошибок.** Худший исход —
   потерять обработку настоящего отказа хода. Закрыто B4: оба теста
   recoverable-ошибок зелёные, живой клиент получает `STT_EMPTY` и `INTERNAL`.
2. **Ход теперь обрывается раньше.** Агентская реплика при разрыве не
   генерируется — намеренно: слушать её некому. Реплика пользователя пишется
   ДО отправки, то есть транскрипт не беднеет. Проверено утверждением
   `["agent", "user"]` в тесте.
3. **Поддельный транспорт в тестах** может разойтись со starlette. Риск реален и
   уменьшен тем, что фейк повторяет две ступени, СНЯТЫЕ С ИСХОДНИКОВ
   (`websockets.py:89` и `:98`), а не придуманные; и что тот же сценарий
   независимо исполнен в настоящем браузере.
4. **Транзакция БД** не тронута: правка только в классификации исключения.
5. **Производительность** — тронут путь ошибки, не путь хода. Сьют 0.95–1.08 с
   (было столько же), latency-инвариант ~3.0 s не задет.
6. **Безопасность, деньги, интеграции — риска нет:** авторизации нет, внешних
   платных вызовов нет, протокол doc 15 не изменился, фронт не тронут ни строкой.
7. **Цепочка гейтов — риска нет:** `scripts/**` и конфиги не тронуты.

## Spec coverage gaps

- **B6, половина UI** — см. выше: блокирована посторонним дефектом прокси,
  решение человека — отдельная поставка.
- Реляционного оракула (`@given`) нет: инвариант про порядок событий, а не про
  класс входов (§6.5 предупреждение остаётся законным).

## Verdict

- [x] **READY FOR HANDOFF**
- [ ] NEED CONVERGE
- [ ] BLOCKED

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 3 code (+6 process docs) / +138/-1 (net +137) |
| commits | 1 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — delivery/active/spec.md (новый оракул) |
| implement_retries | **2** — обе переделки касались ТЕСТА, не правки: (1) `TestClient` отменяет задачу приложения, и первый вариант ловил `CancelledError` вместо разрыва; (2) хелпер ожидания стал мёртвым после перехода на поддельный транспорт и уронил ruff. Сам фикс переписан 0 раз |
| verify_fails_before_green | заполняется после первого прогона CI на ветке |
| est_token_or_cost | n/a — не измерялось; локальный инструмент, внешних платных вызовов нет |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
