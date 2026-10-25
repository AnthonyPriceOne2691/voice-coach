# Verify report: summary-profile

**Date:** 2026-10-25
**Builder:** agent:claude-code (worktree `.claude/worktrees/agent-a98e3306c368a0d23`, ветка `fix/summary-profile`)
**Verifier:** human:anthony
**asserts_reviewed_by:** n/a (класс S — правило §3.1d уровня 3 для M/L; все 18 новых утверждений ведут к примерам U1–U5 mini-spec, дайджест ниже)
**CI run:** PR #51, коммит `5396c57` (весь код поставки, слияние с `main` `84783b6` и архив): `CI` https://github.com/AnthonyPriceOne2691/voice-coach/actions/runs/40221473420 — **success**, по логу «356 passed», покрытие 96.18%, «OK: all files <= 500 LOC», mypy «Success: no issues found in 59 source files»; `quality` https://github.com/AnthonyPriceOne2691/voice-coach/actions/runs/40221473410 — **success**: мутационный шаг «убито 64 из 78 (82%), выжило 14» по `app.knowledge.prompts.*` (на linux умирают мутанты, эквивалентные на macOS), diff-coverage `app/knowledge/prompts.py` 100.0, `okf_sync_gate: OK (5 mapped concepts, 0 warning(s))`, `okf_validate: 0 error(s)`, smoke пройден, `stack_selftest … 0 failure(s)`, доктор `DEAD 0`. ⚠ Джоба `delivery` в CI архивированную поставку НЕ судила: при пустом `active/` шаг зовёт `delivery_check.py` без `--diff-base` и печатает «idle … 0 error(s), 1 warning(s)»; с базой её судил pre-push (`delivery phase gate + breakers (pre-push) … Passed`) и локальный прогон — 0 ошибок (ниже)
**Commit:** репро `0e6d540`, починка `ce0108e`, канон и доки `ef6a20c`, слияние с `main` `84783b6` — `c45c9db`, корень репозитория в тестах из `app.config` — `959198e`, U3 строкой целиком — `4954127`; ветка начата от `main` `5d7d7b7`

## Оракулы mini-spec

| id | Оракул | Результат |
|---|---|---|
| U1 | `test_summary.py::test_full_summary_sends_the_candidate_profile` — настоящий `summary_system.txt`, синтетический профиль | **PASS**. На `5d7d7b7` красный по правильной причине: `AssertionError: профиль не дошёл до сводки` — системное сообщение = файл промпта без профиля |
| U2 | `test_summary.py::test_minimal_summary_sends_the_candidate_profile` — настоящий `minimal_summary_system.txt` | **PASS**; до правки красный тем же сообщением |
| U3 | `test_summary.py::test_summary_without_profile_file_says_so[full\|minimal]` — файла профиля нет | **PASS**; до правки оба красные: заглушки `(no candidate profile available)` в сообщениях не было |
| U4 | `test_summary.py::test_positioning_is_judged_against_the_profile_section` — оба промпта и настоящий профиль | **PASS**; до правки красный (`summary_system: профиль не объявлен входом`) |
| U5 | `test_summary.py::test_summary_prompts_with_profile_fit_the_context_budget` — бюджет doc 20 | **PASS**: полная 11,257 из 16,384, минимальная 4,879 из 8,192 (расчёт — doc 20). До правки тоже зелёный — сторож бюджета после правки, не репро |
| — | `test_prompts.py::test_generic_loader_substitutes_the_profile` — `system()` подставляет профиль, файл без плейсхолдера отдаётся как есть | **PASS**; до правки красный |

Красный прогон до правки — на коммите репро `0e6d540` (дерево `5d7d7b7` + тесты):
`6 failed, 24 passed` в `test_summary.py` + `test_prompts.py` (U1, U2, U3 ×2, U4 и тест
загрузчика). После правки `ce0108e` — `30 passed`.

Два утверждения дайджест привязал к L20 — ближайшей метке комментария модуля. Это
предусловия помощника `_summary_call` («сводка сохранилась»), общего для U1–U3: без
них сверка сообщений шла бы по вызову, который мог и не дойти до модели.

## Мутации (сторож обязан краснеть ровно там, где правка)

Каждая — на дереве после правки, файл восстанавливается побайтно из копии; отпечаток
`git diff` до и после серии совпал (`be34aac…`).

| Мутация | Ожидание | Результат |
|---|---|---|
| M1: `system()` без подстановки профиля | красные U1, U2, U3 ×2 и тест загрузчика | **5 failed, 25 passed** — ровно они |
| M2: из `summary_system.txt` убран `{{profile_condensed}}` | красные U1, U3[full], U4 | **3 failed** — ровно они |
| M3: из `minimal_summary_system.txt` убран плейсхолдер | красные U2, U3[minimal], U4 | **3 failed** — ровно они |
| M4: в `summary_system.txt` возвращено правило «SEO lead vs AI automation engineer» | красный U4 | **1 failed** — он |
| M5: `summary_num_ctx` = 8192 | красный U5 | **1 failed** — он |

## Машинные гейты

Во время поставки `main` ушёл с `5d7d7b7` на `84783b6` (talk-notes-rest #42, mutation-gate
#44); ветка сведена слиянием `c45c9db`, после него `uv sync --all-extras` и `npm ci`.
Сторож M15 из `main` (`test_repo_root.py`) запретил считать корень глубиной пути в
тестах — `test_summary.py` берёт `REPO_ROOT` из `app.config` (`959198e`). Числа ниже — с
дерева после слияния; до него `run_checks.sh` давал 329 passed, 95.92%.

| Гейт | Результат |
|---|---|
| `./scripts/run_checks.sh` | **PASS** — размер модулей, ruff, mypy strict, **356 passed**, покрытие 96.18% (гейт 85); `app/knowledge/prompts.py` — 100% |
| `STRICT=1 pre-commit run --all-files` | **PASS** — 28 хуков из 28 |
| мутационный гейт локально (`check_mutation_gate.sh`, `MIN_KILLED=60`, `BUDGET_SEC=900`, как в `quality.yml`) | **PASS** — область `app.knowledge.prompts.*`, убито **58 из 78 (74%)**. Логика подстановки в `system()` (`if PROFILE_PLACEHOLDER in text`, `replace`) убита вся. Выжили 20: 19 — в вызовах `read_text(encoding=…)` у каждого загрузчика, включая два в `system()` (выборочно проверены `encoding=None` и `"UTF-8"` — на UTF-8-локали macOS и linux эквивалентны исходнику); 1 — имя файла профиля в верхнем регистре, эквивалентное на регистронезависимой ФС macOS. Первый прогон дал 57 из 78: выживал мутант обрамления заглушки `XX(no candidate profile available)XX` — U3 сверял заглушку подстрокой; теперь — строкой целиком, и мутант убит |
| `bash delivery/evals/smoke/run.sh` | **PASS** — S1–S6 ok, S7 skip (сервер не поднят) |
| `python3 scripts/lint/contour_doctor.py` | **PASS** — `AUTO 47 · WEAK 17 · ABSENT 0 · TOOL 3 · SKIP 1 · DEAD 0` |
| `python3 scripts/okf_validate.py knowledge/` | **PASS** — 0 ошибок, 0 предупреждений, 13 файлов |
| `python3 scripts/okf_sync_gate.py --base origin/main` | **PASS** — `OK (5 mapped concepts, 0 warning(s))`; до коммита концепта — FAIL на `model-split` (оба промпта сводки), как и должно |
| `python3 scripts/delivery_check.py --diff-base origin/main` | **PASS** на handoff — `0 error(s), 1 warning(s)`: предупреждение о размере класса S, разбор ниже |
| предохранитель §3.4 | 9 файлов, +217/−11 (net +206) при пределах 25 / 800 |

**Предупреждение «class S, а тронуто 9 файлов / 206 строк».** Разбор: код — один файл
(`prompts.py`, +11/−2), данные промптов — два (+8/−2), тесты — два (+136/−2), доки — четыре
(docs 05, 08, 16, 20; +62/−5). Правка одного механизма с ясным repro — класс S по работе; объём
дали тесты и обязательные правки канона дизайна (constitution п. 7: расхождение кода с
доком чинится в том же PR).

## Изменение поверхности модели (§14.4)

- `data/prompts/**` — `summary_system.txt`: во входе «Candidate profile (below)», блок
  `CANDIDATE PROFILE (judge positioning against it — do not summarize it)` с
  `{{profile_condensed}}` перед `OUTPUT`; правило «Flag positioning issues if candidate
  sounded like SEO lead vs AI automation engineer» → «Flag positioning issues against
  the Positioning rules in the candidate profile (e.g. sounding like an SEO lead instead
  of the builder)». `minimal_summary_system.txt`: блок `CANDIDATE PROFILE (score
  positioning against its Positioning rules — do not summarize it)` после `INPUT`.
  Что меняется в поведении: R1 и qwen впервые видят профиль (~1,270 токенов) и судят
  `positioning` по его таблице `Positioning rules`, а не по роли из текста промпта.
  Остальные правила, схема ответа (`SCHEMA_HINT`), модели и параметры выборки не
  тронуты. Порча промпта (§6.5b) в проекте не развёрнута — живого оракула на поведение
  нет; поставка добавляет оракулы доставки (U1–U4) и бюджета (U5). at=2026-10-25
- `backend/app/knowledge/prompts.py` — `PromptLibrary.system()` подставляет профиль
  туда, где файл промпта его просит; файл без плейсхолдера отдаётся как есть. Кроме
  двух промптов сводки плейсхолдера нет ни в одном файле, который грузится через
  `system()` (`translate_term_system.txt` — без него, проверено тестом загрузчика), так
  что голосовые промпты и починка перевода получают байт-в-байт прежний текст:
  `interviewer_system()`, `talk_system()`, `review_system()` не тронуты (D5). at=2026-10-25

## Ревью рисковых мест (§12.5)

Маячок поднял два класса — оба по словам, а не по смыслу правки:

1. **деньги — риска нет**, потому что поднял его токен `цена` в doc 20 («цена — память
   KV-кэша R1» в разделе про длинные сессии). Денег в продукте нет, правка их не
   касается.
2. **производительность — риска в коде нет, цена в токенах названа.** Токен —
   `json.dumps(VALID)` в тестах (`_summary_call`): сериализация фиксированного ответа
   фейковой модели. В продуктовом коде новых циклов нет: `system()` читает файл профиля,
   только если в промпте есть `PROFILE_PLACEHOLDER`, поэтому `translate_term` (до 12
   вызовов на сводку, S-H4) профиль не читает вовсе; сводка читает его раз на попытку.
   Настоящая цена — промпт длиннее на ~1,270 токенов: prefill R1 офлайн и не виден
   пользователю (D-8), а минимальная сводка на qwen после Skip ждёт prefill этих токенов.
   Не замерено (модель — по «запускай»), строка в отложенных проверках ниже.

Что ещё может сломаться — без маячка, по смыслу правки:

3. **Модель начнёт пересказывать профиль вместо сессии** (цифры портфолио в
   `overall_summary` или `strengths` без опоры на транскрипт). Держит текст: в обоих
   блоках «do not summarize it», а правило «cite question numbers and short evidence
   quotes» остаётся. Машинного исполнителя нет — advisory, как и было
   (`delivery/rule_enforcers.md`); проверяется живым прогоном.
4. **Длинная сессия переполнит контекст.** Разобрано в doc 20: 15 минут влезает с
   запасом (U5), 30 минут — минимальная с запасом ~800, 45 минут — полная на границе
   16,384, минимальная по оценке не влезала и до профиля. Открытый вопрос человеку.

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` с причиной в STATUS: профиль уходит в модель текстом системного
сообщения, путь исполняется тестами сводки на фейковой модели; меняется содержимое
промпта, а не тракт.

## Отложено «по запускай» (модель не запускалась)

Живой прогон R1 и qwen — только по слову человека; в этой поставке Ollama не
запускалась ни разу.

1. **R1 судит позиционирование по профилю.** Полная сводка живой сессии, где кандидат
   сбивается на SEO-рамку: балл `positioning` и запись `consistency_flags` или
   `improvements` (category `positioning`) опираются на таблицу `Positioning rules`
   профиля. Провал — повод перенести профиль из `system` в `user` (D2: DeepSeek советует
   держать инструкции R1 в пользовательском сообщении).
2. **qwen делает то же в минимальной сводке**, и prefill после Skip не растёт заметно
   (поле `prompt_eval_duration` ответа Ollama до и после).
3. **Размер промпта длинной сессии** — `prompt_eval_count` полной и минимальной сводки
   на 30- и 45-минутной сессии против оценок doc 20.

## Наблюдения вне поставки

- Doc 08 рисует вход сводки «… + session_metadata + knowledge profile»; метаданные
  сессии в сводку тоже не идут. Тот же класс (вход объявлен — исполнителя нет), другой
  вход; записано строкой в changelog doc 08, не чинилось.
- `review_system.txt` (Mode 2) держит пример «At Q5 you sounded like an SEO lead; try
  opening as the automation builder» — сверен с профилем: «SEO lead» стоит в колонке
  Don't, «builder» — его же слово. Не устарел, не тронут.

## Verdict

**READY FOR HANDOFF** — U1–U5 зелёные, репро красный на `5d7d7b7` по правильной причине,
пять мутаций краснят ровно свои тесты, локальные гейты зелёные. Поведение на настоящей
модели — отложенные проверки по «запускай» и сигнал наблюдения, не условие закрытия.

## Дайджест утверждений

Оговорка к строке «примеры человек подписал до кода»: у класса S подписи примеров нет
(`human_ok_spec: n/a`), U1–U5 записал исполнитель в mini-spec. Ожидаемые значения
взяты не из реализации, а из объявлений самого репозитория: вход «Candidate profile» —
из промптов сводки, заглушка — из `PromptLibrary._profile`, раздел `Positioning rules` —
из профиля, бюджет — из doc 20 и `config.py`.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **18**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
U1	assert library.system("summary_system") == "RULES\nSam, builder of things\nEND"  # U1
U1	assert library.system("translate_term_system") == "translate to russian"  # U1
L20	assert await service.generate_full("i1", "r1") is not None
L20	assert await service.generate_minimal("i1") is not None
U1	assert messages[0]["role"] == "system"  # U1
U1	assert SYNTHETIC_PROFILE in messages[0]["content"], "профиль не дошёл до сводки"  # U1
U1	assert all(PROFILE_PLACEHOLDER not in m["content"] for m in messages)  # U1
U2	assert messages[0]["role"] == "system"  # U2
U2	assert SYNTHETIC_PROFILE in messages[0]["content"], "профиль не дошёл до сводки"  # U2
U2	assert all(PROFILE_PLACEHOLDER not in m["content"] for m in messages)  # U2
U3	assert NO_PROFILE in messages[0]["content"].splitlines()  # U3
U3	assert all(PROFILE_PLACEHOLDER not in m["content"] for m in messages)  # U3
U4	assert "## Positioning rules" in profile  # U4
U4	assert PROFILE_PLACEHOLDER in text, f"{name}: профиль не объявлен входом"  # U4
U4	assert "Positioning rules" in text, f"{name}: позиционирование не по профилю"  # U4
U4	assert "AI automation engineer" not in text, f"{name}: зашитая роль вернулась"  # U4
U5	assert full + settings.summary_max_tokens <= settings.summary_num_ctx  # U5
U5	assert minimal + settings.minimal_summary_max_tokens <= settings.ollama_num_ctx  # U5
```

✅ **Каждое утверждение ведёт к примеру спеки** (L20 U1 U2 U3 U4 U5), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 9 code (+7 process docs) / +217/-11 (net +206) |
| commits | 6 |
| time_to_accepted_spec | n/a (no spec.md in history — class S?) |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | no |
| implement_retries | 2 — тесты взяли `REPO_ROOT` из `app.config` после слияния с `main` (сторож M15 пришёл с mutation-gate) и U3 сверяет заглушку строкой после выжившего мутанта; код починки — с первого раза |
| verify_fails_before_green | 0 — локальные гейты verify зелёные с первого прогона и после слияния; CI ветки зелёный с первого прогона (`CI` 40221473420, `quality` 40221473410) |
| est_token_or_cost | n/a — модель не запускалась; прогоны CI на публичном репозитории |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
