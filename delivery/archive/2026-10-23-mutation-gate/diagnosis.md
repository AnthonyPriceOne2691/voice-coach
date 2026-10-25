# Diagnosis: мутационный гейт на этом проекте не просудил ни одного мутанта

**Симптом (дословно, 2026-10-23, `BASE=e1b2e19~1` — дифф talk-screen, 2 файла):**

```text
mutation: область — 2 файл(ов) (глобы: app.api.ws_voice.* app.voice.warmup.*), запуск из backend
⚠ mutation: mutmut 3.7.0 завершился с кодом 1 — гейт не судит, вывод ниже
...
✗ мутационный гейт не просудил НИЧЕГО (причина выше) — это НЕ «мутанты убиты».
```

Воспроизведение — та же команда, что в замере 18.10:
`env LINT_PY_SRC=backend/app LINT_COV_PKG=app LINT_FE_DIR=frontend LINT_BE_DIR=backend BASE=e1b2e19~1 MIN_KILLED=60 BUDGET_SEC=300 bash scripts/lint/check_mutation_gate.sh`.
Цикл — 5–15 секунд: mutmut падает на сборе статистики, до мутантов не доходит.

## Журнал гипотез

| # | Гипотеза | Как проверял | Вердикт |
|---|---|---|---|
| H1 | `REPO_ROOT = parents[2]` под копией `backend/mutants/app/config.py` указывает в `backend/`, сьют не находит `data/contracts` (замер 18.10) | Прогон гейта, хвост вывода; затем копия `config.py` в раскладке `mutants/` во временном каталоге | **ПОДТВЕРЖДЕНА, но вторая.** Первым прогоном не видна: сбор падает раньше (H2). После H2 — `FileNotFoundError: …/backend/data/contracts/interview.contract.yaml` в `tests/test_health.py`. Копия старого `config.py` в `<tmp>/repo/backend/mutants/app/` даёт `REPO_ROOT = <tmp>/repo/backend`. Та же беда у тринадцати тестовых файлов: `Path(__file__).resolve().parents[2]` из `backend/mutants/tests/` — тоже `backend/` |
| H2 | Копия пакета не импортируется: трамплин mutmut прячет имя из аннотации | Хвост вывода гейта; чтение `backend/mutants/app/storage/repositories/vocabulary.py` | **ПОДТВЕРЖДЕНА, первая стена.** `TypeError: 'function' object is not subscriptable` на `-> list[VocabularyEntry]`. mutmut 3.7 (`function_trampoline_arrangement`) ставит трамплин под исходным именем `list`, а копию оригинала и мутанты — следом с той же подписью: в теле класса `list` уже метод. Сканер AST по `backend/app`: случай единственный |
| H3 | Сбор статистики падает не на тестах, а на пороге покрытия | Хвост вывода после H1+H2 | **ПОДТВЕРЖДЕНА, третья стена.** `272 passed`, затем `FAIL Required test coverage of 85% not reached. Total coverage: 16.67%` и `failed to collect stats. runner returned 1`. `--cov-fail-under=85` стоит в `addopts` проекта (в канонном фрагменте его нет) и судит мутированную копию: каждая функция там лежит десятком мутантов, которых сьют не исполняет |
| H4 | Ключи мутантов не совпали с путями импорта (`none match any mutant key`) | Поиск строки в выводе | **ОТВЕРГНУТА.** Гейт запускает mutmut из `backend/`, ключи `app.…` совпадают с импортом тестов (§3.7 канона) |
| H5 | mutmut не смог запустить pytest (`BadTestExecutionCommandsException`) | Поиск строки в выводе | **ОТВЕРГНУТА.** `tests/` копируется сам (`also_copy` по умолчанию), pytest стартует |

## Подтверждённая причина

Три независимые стены, и каждую видно только после предыдущей. Замер 18.10 назвал
вторую, потому что первую на этом коде не видел никто: гейт не запускался ни в CI,
ни руками после неё.

1. **H2** — `storage/repositories/vocabulary.py`: метод `list` с аннотацией
   `list[VocabularyEntry]`. Чинится отложенными аннотациями
   (`from __future__ import annotations`) — mutmut переносит `__future__`-импорты в
   начало копии, и аннотация больше не вычисляется в теле класса. Сторож на класс
   дефекта — `tests/test_mutation_copy.py` (на файле без отложенных аннотаций —
   красный, проверено).
2. **H1** — корень репозитория ищется по данным: ближайший предок, где лежат
   `data/prompts` и `data/contracts`; нет — `RepoRootNotFoundError`. Тесты берут
   корень из `app.config`, а не считают сами.
3. **H3** — прогоны pytest внутри mutmut идут с `--no-cov`
   (`[tool.mutmut] pytest_add_cli_args`). Покрытие меряет `ci.yml` и шаг Diff
   coverage, а не мутант.

После трёх правок тот же прогон: `mutation: убито 497 из 806 (61%), выжило 309`,
`mutation: OK`.

## Что нашлось по дороге (не причина симптома, но про «судит ли гейт»)

- **Слепое пятно декораторов.** mutmut 3.7 не мутирует методы декорированного класса
  и декорированные функции, кроме `@staticmethod`/`@classmethod`
  (`_skip_node_and_children`). Под `@dataclass` у `TurnEnforcer` были невидимы все
  проверки контракта: 70 из 88 строк функций `contracts/enforcer.py`, гейт показывал
  «100%» по 21 мутанту из `ContractEnforcer`. По пакету слепы 213 из 2502 строк
  функций (8.5%): маршруты FastAPI, свойства, `Turn`/`TranscriptBuffer`.
- **Знаменатель гейта.** Канонный вердикт считает `killed / (killed + survived)`:
  `timeout` и `no tests` не входят ни туда, ни туда. Функция диффа без единого
  покрывающего теста из доли выпадает молча, если рядом есть судимые.
- **Цена `api/ws_voice.py`.** Каждый выживший мутант гоняет все WS-тесты, повисший —
  ждёт таймаута mutmut. Локальный прогон под нагрузкой (load average 150–200):
  ws_voice — 6,600 s рабочего времени на 801 мутант (повисшие 60 — 2,382 s,
  выжившие 251 — 2,852 s).
