# Verify report: talk-check-core (D3a.2, ядро проверки речи)

Дата прогонов: 2026-10-23. Builder: agent:claude-code (ведущая сессия
voice-interview-coach). Verifier: human:anthony.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| C1, C4 | модель ничего не нашла / изменение без смены слов — не заметка (`test_tips_policy.py`) | **PASS** |
| C2 | ошибка — заметка с фрагментом в написании распознанного и причиной | **PASS** |
| C3 | плоская фраза — заметка `style` | **PASS** |
| C5 | смешанная реплика — одна заметка, об ошибке | **PASS** |
| C6 | несказанное не отмечается: два случая + инвариант на 300 входах; латиница и контракт | **PASS** — тест нашёл дефект: вариант на кириллице отбрасывался как «не меняет слов», а иероглифы проходили контракт; починено (решение 4) |
| C7 | повтор по фрагменту и по варианту — не заметка | **PASS** |
| C8 | префикс разговора не тронут, просьба последней, схема и `num_ctx` клиента (`test_language_check.py`, `test_ollama_client.py`) | **PASS** на фейке; живой замер — не прогнан (решение 9) |
| C9 | eval 37 случаев в шести классах (`delivery/evals/talk-check/`) | **НЕ ПРОГНАН** — человек ответил «не сейчас»; скрипт готов, импорт и линт проверены |

## Мутации (сторож обязан краснеть)

Прогон 2026-10-23 скриптом мутаций (мутация → `pytest -x` по файлу сторожа → файл
возвращён); в таблице — фактический вывод. Первая редакция этого отчёта вписала
«красный» ДО прогона — исправлено на замер.

| Мутация | Сторож | Результат |
|---|---|---|
| MK1: `decide` берёт цитату модели, не сверяя её с репликой | `test_tips_policy.py` | **красный** — 1 failed, 3 passed |
| MK2: проверка латиницы снята | `test_tips_policy.py` | **красный** — 1 failed, 9 passed |
| MK3: повтор не сверяется | `test_tips_policy.py` | **красный** — 1 failed, 5 passed |
| MK4: просьба кладётся первой, а не последней | `test_language_check.py` | **красный** — 1 failed |

## Машинные гейты

| Гейт | Результат |
|---|---|
| `uv run pytest` | **PASS** — 302 (main 275 + 27), покрытие 95.8%; стражи исполнения: пул 530, не вернулось 0, утечек 0 |
| `uv run mypy app` | **PASS** — strict, 57 файлов |
| `ruff check` / `ruff format --check` | **PASS** |
| `STRICT=1 pre-commit run --all-files` | **PASS** — jscpd 0 клон-пар (после решения 6) |
| `okf_sync_gate.py` | **PASS** — концепты `orchestrator-owns-structure` и `model-split` обновлены |
| `delivery_check.py --diff-base origin/main` | 0 ошибок; предохранитель — 14 файлов кода, net +590 |

### Оставшиеся предупреждения

- Примеры C10–C17 без ссылки в тестах — они принадлежат поставкам talk-notes и talk-tips.
- Реляционный оракул (§6.5) — решение человека 2026-08-12: зависимость для
  тестов-свойств не добавляется; инварианты идут перебором (решение 7).
- Пример и тест одним коммитом (§3.1d) — спека подписана и закоммичена отдельно на
  ветке `feat/talk-check` (`d9a7f9d`) до кода; на ветку ядра она приехала вместе с
  ним при разрезе.

## Изменение поверхности модели (§14.1)

- `data/prompts/language_check.txt` (новый), `backend/app/voice/language_check.py`,
  `backend/app/orchestrator/tips.py`, `backend/app/llm/ollama_client.py`,
  `backend/app/config.py` — модель получает вторую просьбу в префиксе разговора и
  отвечает по JSON-схеме. В путь хода ядро не входит: подключает wiring. at=2026-10-23

## Ревью рисковых мест (§12.5)

1. **новый модуль** (`tips.py`, `language_check.py`) — чистые функции и один вызов
   модели; риск — неверное решение о заметке. Закрыт тестами решения на настоящем
   контракте и инвариантом на переборе; дефект с нелатинскими вариантами найден и
   закрыт до ревью.
2. **регулярные выражения** (`re.compile`, `_WORD`) — разбор слов реплики; один
   проход по строке длиной реплики, без вложенных квантификаторов — катастрофический
   возврат невозможен.
3. **шов модели** (`ChatOptions`, `Unpack`, `json_schema`) — изменилась сигнатура
   `LlmClient.stream_chat` для всех вызовов. Вызывающий код не менялся (те же
   именованные аргументы); mypy strict подтверждает соответствие клиента протоколу.
   Что реально может сломаться — `num_ctx`: другое значение перезагрузило бы модель,
   поэтому проверка зовётся без него, ровно как реплика (тест C8).

4. **интеграция** (Ollama `/api/chat`, поле `format`) — JSON-схема в `format` нужна
   Ollama с поддержкой структурного вывода; старая версия ответит прозой или
   ошибкой. Опасности нет, потому что ответ без схемы — `parse_candidate` →
   `MALFORMED`, а ошибка HTTP — `OllamaError`: заметки нет, разговор идёт (wiring
   считает такие проверки упавшими). Версия Ollama на машине Антона проверяется
   живым eval C9.

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` — ядро не входит в путь хода; WS-путь исполняет поставка
talk-check-wiring. at=2026-10-23

## Verdict

**READY FOR HANDOFF** — оракулы C1–C8 зелёные на фейке, машинные гейты зелёные по
правилам delivery@2.07 · cqg@2.74. Живой eval C9 и замер C8 отложены человеком
(«не сейчас», 2026-10-23) и записаны в `observe_signal`: ядро в продукт не
подключено, пока не придёт wiring.

## Assertion digest

asserts_without_example: 0

asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 14 code (+11 process docs) / +611/-21 (net +590) |
| commits | 3 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — backend/tests/test_language_check.py (новый оракул), backend/tests/test_tips_policy.py (новый оракул), delivery/evals/talk-check/cases.yaml, delivery/evals/talk-check/run.py |
| implement_retries | MANUAL — fills from session log |
| verify_fails_before_green | MANUAL — count red verify runs (CI run list) |
| est_token_or_cost | MANUAL / n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
