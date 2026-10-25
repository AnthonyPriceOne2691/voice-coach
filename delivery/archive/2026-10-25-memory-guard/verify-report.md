# Verify report: memory-guard (D3b, что может попасть в память)

**Date:** 2026-10-25
**Builder:** agent:claude-code (worktree `.claude/worktrees/agent-a4f54d21e471ed425`, ветка `feat/memory-guard`)
**Verifier:** human:anthony
**asserts_reviewed_by:** n/a (все 31 новое утверждение ведут к подписанным примерам K2, K3, K4, K10, K11, K12 — дайджест ниже; спека подписана human:anthony 2026-10-23, `human_ok_spec: yes`)
**CI run:** вписывается после первого прогона PR — см. ниже «Прогоны CI»
**Commit:** спека `ef322c7`, код `a3b660c`, корень репозитория в тестах `30d2b3a`; слияния с `main` — `de7bb73` (deps-refresh `8d344d4`), `a71e483` (talk-check-wiring `5d7d7b7`, talk-notes-rest `a97a621`), `e106fc0` (mutation-gate `84783b6`)

Все замеры ниже — с дерева после третьего слияния с `main` (`e106fc0` + `30d2b3a`),
macOS, load average 2–6 во время прогонов; мутации MG1–MG10 сняты дважды — на `a71e483`
и на итоговом дереве, счёт одинаковый. Модель, Ollama, браузерный стенд не запускались:
в этой поставке модель не зовётся.

С `main` пришёл мутационный гейт (#44) и с ним сторож `test_repo_root.py`: корень в
тестах — только `app.config.REPO_ROOT`. `test_memory_guard.py` считал его `parents[2]` —
переведён на `REPO_ROOT` (`30d2b3a`).

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| K3 | цитата, которой он не говорил («I love surfing» — сказал Генри, его реплик в `said` нет), — `NOT_SAID`; текст не о своей цитате — `UNRELATED`; инвариант на 300 входах: сохранённая цитата — кусок его реплики как есть, слово, которого он не говорил, — всегда отказ | **PASS** |
| K4, K5, K6, K7, K8 | 13 случаев: почта, телефон, ставка, долг, суд, семья, здоровье, Ally — `NEVER_STORE` с категорией; в каждой паре и цитата, обрезанная до безобидного хвоста («so I barely slept»); инвариант на 300 входах: категория в реплике с цитатой — отказ с ЭТОЙ категорией | **PASS** |
| K10 | из пяти (по-русски, не на «you», вопрос без «?», два годных) сохранены два годных в порядке модели; 13 случаев «одно поле испорчено → своя причина» и 3 случая красной стороны («you're», «your», «St.»); кривой кандидат — отказ только ему; в логе причина, категория и число, метка `canary_text` — нигде; инвариант на 200 входах: сохранены первые ≤ 3 годных в порядке модели | **PASS** |
| K12 | «You're reading Dune.» рядом с «You started reading Dune.» и наоборот — `REPEAT`; от меньшего набора: короткий пересказ длинной заметки и наоборот — `REPEAT`; сосед в одном ответе; инвариант на 300 парах: повтор симметричен, часть заметки — всегда повтор | **PASS** |
| K2, K11 (часть guard) | заметка из его слов проходит с цитатой в написании распознанного; ответ не той формы — отказ всего ответа | **PASS**; запись, повтор и `failed` — memory-write |
| маркеры | каждый `invariants.hard[].id` контракта памяти оставил маркер в `backend/app/memory/` (`test_contracts.py`, сторож обобщён со сводки) | **PASS** |

## Мутации (сторож обязан краснеть)

Прогон 2026-10-25 скриптом мутаций (замена текста → `pytest` по файлу сторожа → файл
возвращён из памяти); в таблице — фактический вывод прогона. После восстановления —
`53 passed`, `git status` чист.

| Мутация | Сторож | Результат |
|---|---|---|
| MG1: M-H4 не смотрит реплику с цитатой | `test_memory_guard.py` | **красный** — 5 failed, 48 passed |
| MG2: M-H6 — доля от большего набора | `test_memory_guard.py` | **красный** — 4 failed, 49 passed |
| MG3: M-H2 снят (латиница не проверяется) | `test_memory_guard.py` | **красный** — 5 failed, 48 passed |
| MG4: предел трёх снят | `test_memory_guard.py` | **красный** — 1 failed, 52 passed |
| MG5: список «никогда» не применяется | `test_memory_guard.py` | **красный** — 15 failed, 38 passed |
| MG6: текст не сверяется с цитатой (M-H3) | `test_memory_guard.py` | **красный** — 1 failed, 52 passed |
| MG7: в заметку идёт цитата модели, а не распознанное | `test_memory_guard.py` | **красный** — 5 failed, 48 passed |
| MG8: отказ пишет в лог текст кандидата | `test_memory_guard.py` | **красный** — 1 failed, 52 passed: страж канона «лог app.memory.guard.info несёт canary_text», утечек 2 |
| MG9: категория без шаблонов не роняет загрузку | `test_memory_guard.py` | **красный** — 1 failed, 52 passed |
| MG10: в контракте памяти правило без маркера в коде | `test_contracts.py` | **красный** — 1 failed, 24 passed |

## Машинные гейты

| Гейт | Результат |
|---|---|
| `uv run pytest` | **PASS** — 404 passed, покрытие 96.47%; `app/memory/` — 100%; новых тестов 55 (53 в `test_memory_guard.py`, 2 случая сторожа маркеров); стражи канона: «записей прочитано 24531 · текстов под меткой 1 (canary_text в 4 тест(ах)) · пул: взято 703, не вернулось 0 · утечек 0» |
| мутационный гейт `check_mutation_gate.sh` (параметры CI: `MIN_KILLED=60`, `BUDGET_SEC=900`) | **PASS** — 4 файла (`app/memory/*`, `orchestrator/tips.py`), убито 400 из 470 (85%), выжило 70 |
| `uv run mypy app` | **PASS** — strict, 62 файла |
| `ruff check` / `ruff format --check` | **PASS** |
| `lint-imports` | **PASS** — 3 kept, 0 broken (новый слой `memory`) |
| `STRICT=1 pre-commit run --all-files` | **PASS** — 28 хуков Passed, exit 0 (jscpd — ратчет не вырос) |
| `okf_sync_gate.py --base origin/main` | **PASS** — OK, 6 mapped concepts |
| `okf_validate.py` | **PASS** — 0 errors, 0 warnings, files=14 |
| `delivery_check.py --diff-base origin/main` | 0 ошибок; предохранитель — 10 файлов кода, net +787 (+810/−23) при 800 |
| `delivery/evals/smoke/run.sh` | **PASS** — S1–S6 ok, S7 пропущен (сервер не поднят) |

### Оставшиеся предупреждения

- Примеры K1, K13, K15, K16, K17, K18, K19, K20, K21, K22, K23, K24, K25 без ссылки в
  тестах — они принадлежат поставкам memory-write и memory-recall.
- Реляционный оракул (§6.5) — тест-зависимость для свойств не добавляется (решение
  человека 2026-08-12, решение 12); инварианты идут перебором с зерном 20261025.
- Предохранитель: net 787 при 800. Первая собранная версия была выше предела —
  срезано без waiver: таблицы случаев переписаны строками, дублирующий тест снят,
  повторы прозы в docstring и YAML убраны (урок L105).

## Изменение поверхности модели (§14.1)

- `data/contracts/memory.contract.yaml` (новый) — правила M-H1…M-H7 и числа, которые
  код читает (`load_rules`); модель его не видит, но он решает, какие её слова станут
  заметкой. at=2026-10-25
- `data/contracts/memory_never_store.txt` (новый) — шаблоны шести категорий; совпадение
  — кандидат отброшен целиком. at=2026-10-25
- `backend/app/memory/__init__.py`, `backend/app/memory/guard.py`,
  `backend/app/memory/rules.py` (новые) — решение кода о кандидате; в путь разговора не
  подключены, модель не зовётся (подключает memory-write). at=2026-10-25
- `backend/app/orchestrator/tips.py` — `locate` и `latin_only` открыты для памяти;
  поведение заметок к речи прежнее: `test_tips_policy.py` не менялся и проходит
  (23 passed). at=2026-10-25

## Ревью рисковых мест (§12.5)

1. **новый модуль** (`guard.py`, `rules.py`) — чистые функции и загрузка данных; риск —
   неверное решение о заметке. Закрыт таблицами случаев на настоящих данных, пятью
   инвариантами на переборе и десятью мутациями (все красные). Порядок проверок в
   `decide` несущий: M-H2 до разбора слов (иначе кириллица получила бы причину «форма»,
   L82), M-H4 после M-H3 (реплика с цитатой известна только после поиска).
2. **производительность** (`json.loads` в `parse_candidates`, `re.compile` шаблонов в
   `load_never_store`, `re.search` в `NeverStore.category`) — риска нет: разбор идёт
   один раз на ответ модели после разговора (≤ 300 токенов), шаблоны компилируются один
   раз при загрузке, а `category` проходит 22 шаблона по четырём коротким строкам
   (заметка ≤ 25 слов и одна реплика). В голосовой путь ничего не встаёт.
3. **регулярные выражения из данных** (`memory_never_store.txt`, `_SENTENCE_BREAK`) —
   вложенных квантификаторов нет; самый дорогой, почта `[\w.+-]+@`, квадратичен по
   длине слова без «@» и ограничен длиной реплики. Шаблон пишет человек в репозитории,
   не пользователь; сломанный или пустой — ошибка загрузки (MG9 и тест строк).
4. **безопасность** (`secrets: password` в `test_never_store_line_that_cannot_be_read_fails_loudly`)
   — риска нет: это строка неизвестной категории в тесте загрузчика списка; секретов в
   диффе нет, гейт секретов зелёный.
5. **деньги** (`prices?`, `invoices?` в `memory_never_store.txt`) — риска нет: слова
   списка — шаблоны отказа, расчётов и платежей в коде нет.
6. **приватность** (не класс маячка, но главный риск поставки) — текст отброшенного в лог
   не уходит: `_log` получает только `Rejection` (причина, категория), MG8 доказывает,
   что страж канона ловит утечку. Остаточный риск — перефраз мимо списка («a hearing»,
   «my little one»): advisory, меряет живой eval K9 по «запускай» в memory-write.

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` — проверки памяти не входят ни в путь хода, ни в фон: их
подключает memory-write, которая и объявит `backend/app/memory/service.py`. at=2026-10-25

## Прогоны CI

Заполняется после push: ссылки на `CI` и `quality` и их итоги по логу.

## Verdict

**READY FOR HANDOFF** — оракулы K3–K8, K10, K12 (и части K2, K11) зелёные на настоящих
данных, десять мутаций красные, машинные гейты зелёные по правилам delivery@2.07 ·
cqg@2.74 · okf@1.21. Живых проверок у поставки нет: модель не зовётся.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **31**, из них без ссылки на пример спеки: **0**.

```
K2	assert _decide(CALL, CALL_SAID) == CALL_KEPT
K3	assert _decide(surfing, CALL_SAID) == Rejection(Reason.NOT_SAID)
K3	assert _decide(unrelated, CALL_SAID) == Rejection(Reason.UNRELATED)
K4	assert isinstance(verdict, Rejection) and verdict.reason is Reason.NEVER_STORE
K4	assert verdict.category in {Category(name) for name in categories.split(",")}
K10	assert _decide(replace(CALL, **{field: value}), CALL_SAID) == expected
K10	assert isinstance(result, Sifted) and [m.text for m in result.kept] == [CALL.text, DUNE.text]
K10	assert [r.reason for r in result.rejected] == [Reason.NOT_ENGLISH, Reason.FORM, Reason.FORM]
K10	assert isinstance(result, Sifted) and [m.text for m in result.kept] == [
K10	assert logged == {("never_store", Category.MONEY, 1), ("not_english", None, 1)}
K10	assert all(mark not in r.getMessage() for r in records)
K12	assert _decide(candidate, DUNE_SAID, known=(saved,)) == Rejection(Reason.REPEAT)
K12	assert isinstance(_decide(candidate, DUNE_SAID, known=("You're learning to surf.",)), Candidate)
K12	assert isinstance(result, Sifted) and [m.text for m in result.kept] == [DUNE.text]
K12	assert result.rejected == [Rejection(Reason.REPEAT)]
K11	assert _sift(raw, CALL_SAID) == Rejection(Reason.MALFORMED)
K10	assert isinstance(result, Sifted) and [m.text for m in result.kept] == [CALL.text]
K10	assert [r.reason for r in result.rejected] == [Reason.MALFORMED] * 5
K10	assert (RULES.max_memories, RULES.min_quote_words, RULES.text_words) == (3, 3, (3, 25))
K10	assert (RULES.follow_up_max_words, RULES.repeat_share) == (15, 0.6)
K10	assert {category for category, _ in RULES.never_store.patterns} == set(Category)
K3	assert isinstance(kept, Candidate), (said, fragment)
K3	assert any(kept.evidence in turn for turn in said)
K3	assert words(kept.evidence) == fragment
K3	assert _decide(unsaid, *said) == Rejection(Reason.NOT_SAID)
K4	assert _decide(_quoting(fragment, index), *tainted) == Rejection(
K12	assert is_repeat(a, b, RULES.repeat_share) == is_repeat(b, a, RULES.repeat_share)
K12	assert is_repeat(part, a, RULES.repeat_share) and is_repeat(a, part, RULES.repeat_share)
K10	assert isinstance(result, Sifted)
K10	assert [m.text for m in result.kept] == expected
K10	assert result.rejected.count(Rejection(Reason.OVER_LIMIT)) == max(0, sum(good) - 3)
```

✅ Каждое утверждение ведёт к примеру спеки (K10 K11 K12 K2 K3 K4), а примеры человек
подписал до кода (`human_ok_spec`): `asserts_reviewed_by: n/a (все утверждения ведут к
одобренным примерам)`.

asserts_without_example: 0

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 10 code (+14 process docs) / +810/-23 (net +787) |
| commits | 7 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 3 commit(s) after first phase: handoff |
| harness_hardened | yes — backend/tests/test_memory_guard.py (новый оракул) |
| implement_retries | 3 — ruff на первом прогоне (SIM905 на словаре служебных слов, RUF043 в `match=`); срез по предохранителю объёма: net 870 → 814 → 789 → 786; после #44 — корень репозитория в тесте (`parents[2]` → `REPO_ROOT`, net 787) |
| verify_fails_before_green | MANUAL — count red verify runs (CI run list) |
| est_token_or_cost | n/a — модель не зовётся, живых прогонов нет |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
