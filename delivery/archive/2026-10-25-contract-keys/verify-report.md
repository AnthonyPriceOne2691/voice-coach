# Verify report: contract-keys

**Date:** 2026-10-25
**Builder:** agent:claude-code (worktree `.claude/worktrees/agent-a98e3306c368a0d23`, ветка `fix/contract-keys`)
**Verifier:** human:anthony
**asserts_reviewed_by:** n/a (класс S — правило §3.1d уровня 3 для M/L; утверждения сторожа ведут к примерам K1–K6 mini-spec, дайджест ниже)
**CI run:** _заполняется после push_
**Commit:** репро `86bf83d`, честный контракт `5378d37`, привязка утверждений `60b0920`, фаза `b79fd3a`, слияние с `main` `78102a1` — `29e2704`; ветка начата от `main` `1fa99e5`

## Оракулы mini-spec

| id | Оракул | Результат |
|---|---|---|
| K1 | `test_contract_keys.py::test_every_contract_key_is_executed_or_declared[interview\|review\|talk\|memory]` | **PASS**. На `1fa99e5` с пустыми `NOT_EXECUTED` — 4 красных: interview 13 ключей, review 10, talk 7, memory 11 — **41**; у каждого путь и причина молчания |
| K2 | поле типа загрузчика читает кто-то вне загрузчика | **PASS**: `ContractSpec.max_retries` читает `turn_runner.py`, у памяти — `min_quote_words`, `follow_up_max_words` в `guard.py`. На `main` `mode` и `enforcement` красные: «загрузчик кладёт ключ в `ContractSpec.mode`, а поле не читает никто» |
| K3 | параметр голосового правила — из `RuleSpec.params` | **PASS**: читаются `max`, `states`, `ack_max_words`, `patterns_file`, `ack_whitelist_file`. Замер слепоты без этой сверки (H6): ключей правил в красном списке 11 вместо 15, ни одного `recovery` правила |
| K4 | `test_every_contract_file_is_read_or_mirrored` | **PASS**; на `main` красный: `контракты вне сторожа: ['summary.contract.yaml']` |
| K5 | `test_not_executed_entries_are_alive` | **PASS**; мутации KM3 (мёртвая запись) и KM6 (протухшая запись) — красный |
| K6 | `test_the_sweep_sees_the_contracts` — обход видит ключи всех глубин, сбор кода — константы и поля | **PASS**; KM1, KM2, KM5 роняют и его |

Красный прогон — на коммите репро `86bf83d` (дерево `1fa99e5` + сторож с пустыми списками):
`5 failed, 2 passed`. После `5378d37` — `7 passed`.

## Мутации (сторож обязан краснеть ровно там, где правка)

Каждая — одна за другой на дереве после правки, только `tests/test_contract_keys.py`; файл
восстанавливается побайтно из копии, `git diff` после серии пуст.

| Мутация | Ожидание | Результат |
|---|---|---|
| KM1: `spec.py` не читает `recovery.max_retries` (`max_retries=1`) | красные три голосовых контракта и K6 | **4 failed, 3 passed** |
| KM2: `enforcer.py` не читает `states` (`states: list[str] = []`) | красные interview и K6 | **2 failed, 5 passed** |
| KM3: запись `drift` снята из `NOT_EXECUTED` | красные interview, review и K5 (запись под чужим именем — мёртвая) | **3 failed, 4 passed** |
| KM4: в `review.contract.yaml` новый ключ `recovery.retry_delay_ms: 200` | красный review | **1 failed, 6 passed** |
| KM5: `turn_runner.py` не читает `ContractSpec.max_retries` | красные три голосовых контракта и K6 | **4 failed, 3 passed** |
| KM6: `spec.py` начинает читать `drift` (`data.get("drift")`) | красный K5: запись протухла | **1 failed, 6 passed** |
| KM7: `memory/rules.py` не читает `min_quote_words` | красный memory | **1 failed, 6 passed** |

## Машинные гейты

Во время поставки `main` ушёл с `1fa99e5` на `78102a1` (shutdown-leaks H5:
`summary/service.py`, `main.py`); слияние `29e2704` — без конфликтов. Числа — с дерева
после слияния.

| Гейт | Результат |
|---|---|
| `./scripts/run_checks.sh` | **PASS** — размер модулей, ruff, mypy strict, **413 passed**, покрытие 96.48% |
| `STRICT=1 pre-commit run --all-files` | **PASS** — 28 хуков из 28, включая `check-yaml` по всем пяти контрактам |
| значения контрактов | `yaml.safe_load` до и после совпадает у всех пяти `*.contract.yaml`: правка — только комментарии |
| `bash delivery/evals/smoke/run.sh` | **PASS** — S1–S6 ok (S6 — контракты и промпты парсятся), S7 skip |
| `python3 scripts/lint/contour_doctor.py` | **PASS** — `AUTO 47 · WEAK 17 · ABSENT 0 · TOOL 3 · SKIP 1 · DEAD 0` |
| `python3 scripts/okf_validate.py knowledge/` | **PASS** — 0 ошибок, 14 файлов |
| `python3 scripts/okf_sync_gate.py --base origin/main` | **PASS** — `OK (6 mapped concepts, 0 warning(s))`: пути контрактов, кроме памяти, ни в одном `implementation:` (D8) |
| мутационный гейт (`check_mutation_gate.sh`, как в `quality.yml`) | «изменённых prod-файлов нет» — продуктовый код не тронут |
| `python3 scripts/delivery_check.py --diff-base origin/main` | **PASS** на handoff — `0 error(s), 1 warning(s)`: предупреждение о размере класса S, разбор ниже |
| предохранитель §3.4 | 7 файлов, +448/−31 (net +417) при пределах 25 / 800; из них сторож — 347 строк |

**Предупреждение «class S, а тронуто 7 файлов».** Разбор: продуктового кода — ноль строк;
один новый тест (347 строк, из них 53 — записи `NOT_EXECUTED` и `MIRRORED` с причинами), комментарии в
четырёх YAML (+54/−18) и два дока (+47/−13). Класс S по работе: один сторож и пометки.

## Изменение поверхности модели (§14.4)

- `data/contracts/**` — `interview`, `review`, `talk`, `summary` `.contract.yaml`: только
  комментарии «не исполняется — …» у молчащих ключей и блоков и шапка со ссылкой на сторож;
  значения не тронуты — `yaml.safe_load` до и после совпадает у всех пяти файлов, загрузчик
  и енфорсер получают те же данные, поведение модели и проверок прежнее. Исправлены два
  ложных комментария: интервью ссылался на несуществующий `contracts/rules/` и на
  `templates/contract_fallback.txt` (не читает никто), сводка обещала метку
  `summary_failed` (не ставит никто). `memory.contract.yaml` не тронут (D7). at=2026-10-25

## Ревью рисковых мест (§12.5)

Маячок поднял один класс — **новый модуль** `test_contract_keys` (структурный). Риска для
продукта нет, потому что это тест: приложение его не импортирует, код `backend/app` он
читает `ast.parse`, а не исполняет, контракты — `yaml.safe_load`; цена в сьюте — `7 passed
in 0.48s`. Что может сломаться у самого сторожа — с именами из диффа:

1. **Ложный красный на рефакторинге.** Переименуй `RuleSpec.params` или перенеси загрузчик —
   `_params_key` и `Family.modules` перестанут видеть чтение, сторож покраснеет на ключах,
   которые исполняются. Сообщение называет путь ключа и причину, чинится строкой в `VOICE`.
2. **Ложный зелёный по совпадению имён.** Ключ раздела ищется среди констант читателя:
   ключ, названный как чужая константа загрузчика, выглядел бы прочитанным; поле типа —
   по имени атрибута во всём `backend/app` (`.mode` где угодно сочлось бы чтением
   `ContractSpec.mode`). Для параметров правил слепота закрыта сверкой с `RuleSpec.params`
   (H6, K3); для остального — названа в докстринге сторожа.
3. **Комментарий сломал YAML.** Проверено: `check-yaml` зелёный, `yaml.safe_load` даёт те
   же значения, S6 смоука парсит контракты.

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` с причиной в STATUS: продуктовый код не тронут ни строкой.

## Отложено «по запускай»

Ничего: поведение модели и проверок не меняется, живой прогон проверять нечем.

## Открытые вопросы человеку

1. **Строить ли детектор дрейфа** (doc 13, «Drift detection»): окно, пороги, смена
   температуры, напоминание модели, режим «только шаблоны», предупреждение в UI. Сейчас
   есть только счётчики за сессию. До решения блоки `drift` помечены и сторожатся.
2. **Остальные объявленные и не исполняемые ключи** — исполнить или убрать из контрактов:
   свой текст перегенерации на режим (`regenerate_prompt`, долг L73), повтор I2-H5 с
   `num_predict` ×2, сужение `scope` у I2-H3, предусловия из YAML, декларативные I1-S2 и
   I1-S3 с их `recovery`/`template`.
3. **Сирота `data/prompts/templates/contract_fallback.txt`** — удалить или подключить.

## Наблюдения вне поставки

- В doc 13 остаются устаревшие иллюстрации — «Module layout (planned)» (`loader.py`,
  `patterns.py`, `recovery.py`) и «`interview.contract.yaml` (excerpt)» (`senior_colleague`,
  `warm_professional`); исправлен только абзац про `contracts/rules/`.
- Найдено на summary-profile: при пустом `active/` джоба `delivery` в CI зовёт
  `delivery_check.py` без `--diff-base` и архивированную поставку не судит; судит pre-push.

## Verdict

**READY FOR HANDOFF** — K1–K6 зелёные, репро красный на `1fa99e5` по правильной причине (41
ключ и файл сводки), семь мутаций краснят ровно свои тесты, значения контрактов не
изменились, локальные гейты зелёные. Детектор дрейфа — открытый вопрос человеку.

## Дайджест утверждений

Оговорка к строке «примеры человек подписал до кода»: у класса S подписи примеров нет
(`human_ok_spec: n/a`), K1–K6 записал исполнитель в mini-spec. Ожидаемые значения взяты
не из реализации сторожа, а из самих контрактов и кода, который их читает: какие ключи
объявлены — YAML, кто их читает — `spec.py`, `enforcer.py`, `memory/rules.py`; красный
список на `main` — замер, а не ожидание.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **14**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
K1	assert silent == [], (  # K1
K4	assert on_disk == declared, f"контракты вне сторожа: {sorted(on_disk ^ declared)}"  # K4
K4	assert unread == [], f"у контракта есть семья, а его файл не грузит никто: {unread}"  # K4
K4	assert stale == [], f"контракт объявлен незагружаемым, а код его грузит: {stale}"  # K4
K5	assert anchors, f"NOT_EXECUTED[{pattern!r}] не совпал ни с одним ключом"  # K5
K5	assert executed == [], f"NOT_EXECUTED[{pattern!r}] протух: {executed}"  # K5
K6	assert deep <= set(interview)  # K6
K6	assert f"{MEMORY_FORM}/text_max_words" in memory  # K6
K3	assert interview[f"{QUESTION_OR_ACK}/states"].rule_param  # K3
K3	assert not interview[f"{QUESTION_OR_ACK}/check"].rule_param  # K3
K6	assert {"max_retries", "patterns_file"} <= voice.names  # K6
K3	assert {"max", "states", "ack_max_words", "patterns_file"} <= voice.params  # K3
K2	assert "max_retries" in voice.fields_read  # K2
K2	assert {"min_quote_words", "follow_up_max_words"} <= memory_code.fields_read  # K2
```

✅ **Каждое утверждение ведёт к примеру спеки** (K1 K2 K3 K4 K5 K6), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 7 code (+5 process docs) / +448/-31 (net +417) |
| commits | 5 |
| time_to_accepted_spec | n/a (no spec.md in history — class S?) |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — backend/tests/test_contract_keys.py (новый оракул) |
| implement_retries | 2 — первая версия сторожа печатала поддеревья молчащих разделов по строке на ключ и «читала» `id`/`check` предусловий по совпадению имён — введено правило «под молчащим ключом вложенные не судятся»; утверждения переписаны под привязку к K1–K6: строки с id правил (`G1-H4`, `M-H5`) увели бы её на чужой id |
| verify_fails_before_green | 0 — локальные гейты verify зелёные с первого прогона и после слияния; прогоны CI ветки — в шапке |
| est_token_or_cost | n/a — модель не запускалась |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
