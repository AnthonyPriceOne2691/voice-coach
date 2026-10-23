# Eval smoke — mutation-gate

Прогоны 2026-10-23: локально (MacBook, 10 ядер) и в CI PR #44. ⚠ Машина почти весь
день была под чужой нагрузкой — load average 100–290 (Xcode, llama-tokenize соседних
проектов). Поэтому **локальное время — не мера CI** (L81): при каждом времени записана
нагрузка. Доли убитых от нагрузки почти не зависят — она меняет только число
таймаутов. mutmut 3.7.0, Python 3.12.

## M6 — гейт на диффе talk-screen судит

Команда — та же, что в замере 18.10:
`env LINT_PY_SRC=backend/app LINT_COV_PKG=app LINT_FE_DIR=frontend LINT_BE_DIR=backend BASE=e1b2e19~1 MIN_KILLED=60 BUDGET_SEC=300 bash scripts/lint/check_mutation_gate.sh`

| | До | После трёх правок |
|---|---|---|
| вывод | `⚠ mutation: mutmut 3.7.0 завершился с кодом 1` … `✗ мутационный гейт не просудил НИЧЕГО` | `mutation: убито 497 из 806 (61%), выжило 309` · `mutation: OK` |
| exit | 1 | 0 |
| время | 5.5 s — падение на сборе статистики | 3 min 46 s, нагрузка не снята |

Промежуточные стены, по одной на правку (журнал — `diagnosis.md`):
`TypeError: 'function' object is not subscriptable` (vocabulary.py) →
`FileNotFoundError: …/backend/data/contracts/interview.contract.yaml` →
`FAIL Required test coverage of 85% not reached. Total coverage: 16.67%` /
`failed to collect stats. runner returned 1`.

## M7 — обратный прогон: тесты без утверждений гейт краснят

Временная локальная ветка, на ней в диффе против `feat/mutation-gate` только
`voice/warmup.py` (строка-комментарий). Ветка удалена, наружу не уходила.

| `test_warmup.py` | Гейт | exit | Время, нагрузка |
|---|---|---|---|
| с утверждениями | `убито 60 из 63 (95%), выжило 3` · `OK` | 0 | 127 s, load 103 |
| все `assert` вырезаны (AST, `pass` вместо `assert`), pytest `6 passed` | `убито 27 из 63 (42%), выжило 36` · `ERROR: убито 42% мутантов, цель ≥60%` | 1 | 212 s, load 140 |

27 убито и без утверждений: распаковка `[record] = caplog.records`, чтение WAV и
индексация вызовов падают сами. Порог это отделяет.

## M11 — доли убитых по модулям

`mutmut run '<модуль>.*'` на свежем `mutants/` (кэш mutmut держит статистику прошлого
кода — новые функции на нём выглядят «no tests»). Доля = убито / (убито + выжило), как
считает гейт; `timeout` в неё не входит.

| Модуль | Убито / всего | % | timeout | Прогон |
|---|---|---|---|---|
| `orchestrator/talk.py` | 123 / 145 | 84.8 | 0 | 129 s вместе с соседями ниже, нагрузка не снята |
| `orchestrator/pace.py` | 32 / 37 | 86.5 | 0 | то же |
| `orchestrator/meta_request.py` | 19 / 22 | 86.4 | 0 | то же |
| `voice/talk_flow.py` | 45 / 53 | 84.9 | 0 | то же |
| `voice/session_flow.py` | 62 / 88 | 70.5 | 0 | то же |
| `voice/turn_runner.py` | 136 / 202 | 67.3 | 0 | то же |
| `contracts/enforcer.py` | 138 / 171 | 80.7 | 0 | после снятия `@dataclass` (M12), 21 s |
| `voice/warmup.py` | 60 / 63 (было 7 / 63) | 95.2 (было 11.1) | 0 | после `test_warmup.py` |
| `api/ws_voice.py` | 496 / 744 | 66.7 | 57 | после перебазирования на `a4a0dce` (стражи изменили 7 строк файла); тихая машина, load 3–15, ≈ 5 min; до перебазирования — 490 / 741 (66.1%), load 150–200, 784 s |
| `config.py` (`find_repo_root`) | 7 / 7 | 100 | 0 | новая функция |
| `storage/repositories/vocabulary.py` | 122 / 146 (было 89 / 146) | 83.6 (было 61.0) | 0 | после M14 |

Повторный прогон тех же модулей (остановлен на `ws_voice`, 577 из ~800) дал те же доли
в пределах 1 п.п.: talk 85.0, pace 85.7, meta_request 86.4, talk_flow 84.9,
session_flow 71.4, turn_runner 67.0, enforcer 80.6, vocabulary 83.4, ws_voice 66.3.

### Выжившие, которых не убить (эквивалентные)

- `voice/warmup.py` — все три: имя файла прогрева `"warmup.wav"` → `"XXwarmup.wavXX"`
  и `"WARMUP.WAV"` (whisper читает файл по содержимому, имя не видит); `break` →
  `return` после первого куска стрима (за циклом ничего нет).
- `contracts/enforcer.py` — `text.lower()` → `text.upper()` в
  `_check_question_or_ack` (регулярка слов `[A-Za-z']+` считает оба регистра
  одинаково); тексты поля `matched` в `Violation` (`"XXno question…XX"`, верхний
  регистр) — диагностика, а не поведение.

### Выжившие, которые НЕ эквивалентны — кандидаты в тесты (не догонялись: модули выше 60%)

- `contracts/enforcer.py`: граница G1-H2 — `total > max` → `>=`, начальное
  `_chars = 0` → `1`, разделитель `+ 1` → `+ 2`/`- 1`: ровно 400 символов на ход никто
  не проверяет; граница Q-ссылок Mode 2 — `number > question_count` → `>=`;
  `states` у `question_or_ack` — правило вне своих состояний не проверяется; поля
  `sentence_index`/`matched` события нарушения (doc 13) — подмена на `None` не видна.
- `storage/repositories/vocabulary.py`: умолчания `type="word"`, `category="technical"`
  и пропуск записи без `term_en` (`""` → `None` даёт термин «None») — doc 10 их не
  обещает, а поля без `term_en` отсекает раньше `validate_summary`.

## M12 — `contracts/enforcer.py` виден гейту

| | Мутантов на файл | Убито | Чьи |
|---|---|---|---|
| `TurnEnforcer` под `@dataclass` | 21 | 21 (100%) | только `ContractEnforcer`: `__init__`, `start_turn`, `violation_event` |
| `TurnEnforcer` — обычный класс | 171 | 138 (80.7%) | плюс `feed`, `finish`, `spoken_text` и все проверки контракта |

mutmut 3.7 не мутирует декорированное (`_skip_node_and_children`: любой декоратор
класса; у функций — всё, кроме одиночных `@staticmethod`/`@classmethod`). По пакету
`app/` слепы 213 из 2,502 строк функций (8.5%); вне M11 — маршруты FastAPI, свойства,
`Turn`/`TranscriptBuffer` (143 строки).

## M13 — шаг в CI судит дифф PR

PR #44, прогон quality [40007693515](https://github.com/AnthonyPriceOne2691/voice-coach/actions/runs/40007693515),
шаг «Mutation testing (changed files, budgeted)»:

```text
mutation: 3 файл(ов), бюджет 300s, цель ≥60% убитых
mutation: область — 3 файл(ов) (глобы: app.config.* app.contracts.enforcer.* app.storage.repositories.vocabulary.*), запуск из backend
mutation: убито 267 из 324 (82%), выжило 57
mutation: OK
```

85 s на раннере (19:00:12.93 → 19:01:37.59 UTC) при бюджете 300; локально тот же дифф —
29 s при load 9. На push в `main` шаг не запускается (`if: … github.event_name ==
'pull_request'`).

## Цена `api/ws_voice.py` в CI

Заполняется замером draft-PR #45 (дифф — только docstring `ws_voice.py`, бюджет поднят
до 2400 s ради полной цены) — см. verify-report.
