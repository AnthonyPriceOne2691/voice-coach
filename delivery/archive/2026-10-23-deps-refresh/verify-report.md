# Verify report: deps-refresh

Дата прогонов: 2026-10-23. Builder: agent:claude-code (worktree
`agent-aa3d737f55163b435`). Verifier: human:anthony. Живые модели не запускались.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| V1 | `check_deps_audit.sh` на дереве поставки (`eval-smoke.md`) | **PASS** — exit 0, ни одной строки ✗; `--generate`: `py_total=0 js_critical=0 js_high=0 js_total=0` (на `main` 73342b3 — 20 / 2 / 6 / 24, exit 1); pip-audit и npm audit напрямую — 0 |
| V2 | шаг «Vulnerable dependencies» в CI PR #46 + `test_deps_audit_runs_in_quality_gates_job` | **PASS** — шаг в джобе `gates`, `if: always()`, зелёный: «python-половина мерена по uv.lock», строк «○ пропущено» нет. js-половину лог гейта не доказывает (находка N1), её свидетель — `npm ci` той же джобы: «audited 404 packages … found 0 vulnerabilities» |
| V3 | `test_manual_only_hook_runs_in_ci[deps-audit]`, `test_manual_sweep_is_not_blind` | **PASS** — до шага CI красный («не зовёт ни один шаг CI — гейт не исполняется нигде»); без `if: always()` — красный |
| V4 | `npm test` на vitest 5.0.5 + мутация docblock'а | **PASS** — те же 57 тестов в тех же 11 файлах, тесты не правлены; без `// @vitest-environment jsdom` — `document is not defined` |
| V5 | `npm run build`, `npm run lint`, `prettier --check src`, `tsc -b --force` | **PASS** — бандл побайтно прежний (`index-DEbu37-m.js`, `index-uwZHTTsa.css`), eslint 0 ошибок / 1 предупреждение (ратчет 1) |
| V6 | `npx vite --port 5273 --strictPort` без бэкенда | **PASS** — `/` 200 с React refresh; `/health`, `/sessions/interviews`, `/settings`, `/vocabulary` — 500 и `http proxy error … ECONNREFUSED 127.0.0.1:8000`; `/ws/voice` — `ws proxy error`; чужой путь — SPA 200 |
| V7 | `UV_FROZEN=1 ./scripts/run_checks.sh` | **PASS** — 278 passed (275 базы `a4a0dce` + 3 сторожа), coverage 95.64 %, mypy strict, ruff; WS- и shutdown-тесты 5 × 38 passed; в CI джоба `backend` (linux) — pass |
| V8 | vitest 2.1.9 при снимке 99/99/999 | **PASS** — exit 1, «critical=2 high=1 — снимком не легализуются» |

## Находки верификации

Все три — в канонном `scripts/lint/check_deps_audit.sh` (дайджест `8cbe1573` совпадает
с замком `cqg@2.74`); скрипт не правился: правку поведения гейта сперва видит человек
(L65, D6). Кандидаты в апстрим и вопросы человеку.

- **N1. js-половина читает упавший `npm audit` как ноль.** `npm audit --json` без
  реестра печатает `{"message": "… ECONNREFUSED …", "error": …}`, разбор берёт
  `.get("metadata", {})` и даёт `0 0 0`; состояния «js не проверена» на этот случай нет
  (у python-половины оно есть с lab-9 №6). Замер: vitest 2.1.9 в дереве (critical=2) —
  с реестром exit 1, с `npm_config_registry=http://127.0.0.1:9/` — **exit 0**, вывод
  побайтно тот же, что у честного зелёного. Предложение: при неразобранном JSON —
  `skipped+=…; js_unchecked=1`, как у pip-audit.
- **N2. Зелёный путь лжёт «не проверены».** Проверка «нет манифестов» смотрит только
  в корень (`! -f pyproject.toml && ! -f package.json`), а половины — в `$LINT_BE_DIR` и
  `$LINT_FE_DIR`. На раскладке `backend/` + `frontend/` каждый зелёный прогон печатает
  «не найдено ни одного поддерживаемого манифеста … Зависимости ЭТОГО стека не
  проверены» и выходит раньше строки `OK — просмотрено N манифест(ов)` с числами — в CI
  так и напечатано. Предложение: судить по `checked`/манифестам половин.
- **N3. `js_total` вдвое больше.** Сумма идёт по всем числам `metadata.vulnerabilities`,
  включая `total`: 12 уязвимостей → 24. Ратчет сравнивает удвоенное с удвоенным и не
  врёт, но число в выводе и в снимке не то, что называет.

## Мутации (сторож обязан краснеть)

| Мутация | Ожидание | Результат |
|---|---|---|
| MS1: шага CI нет (коммит `81437bf` — сторож до шага) | V2 и V3 красные | **красные** — «не зовёт ни один шаг CI — гейт не исполняется нигде» |
| MS2: шаг без `if: always()` | V2 и V3 красные | **красные** — «шаг аудита без if: always()» |
| MS3: без `// @vitest-environment jsdom` в `SummaryCard.test.tsx` | 3 теста красные | **красные** — `ReferenceError: document is not defined` |
| MS4: vitest 2.1.9 и снимок 99/99/999 | гейт exit 1 | **exit 1** — «critical=2 high=1 — снимком не легализуются» |
| MS5: vitest 2.1.9 и реестр недоступен | гейт exit 1 | **exit 0** — находка N1 |
| MS6: `clearMocks: false` в конфиге (проверка безразличия, не сторож) | 57 из 57 | **57 из 57** — умолчание vitest 5 ни одно утверждение не меняет |

## Машинные гейты

| Гейт | Результат |
|---|---|
| `UV_FROZEN=1 ./scripts/run_checks.sh` | **PASS** — 278 passed, coverage 95.64 %, mypy «no issues found in 55 source files», ruff |
| `npm test`, `npm run build`, `npm run lint`, `prettier --check src`, `tsc -b --force` | **PASS** — 57 тестов, артефакт-оракул собран, warning-ратчет прежний (1) |
| `STRICT=1 pre-commit run --all-files` | **PASS** — 28 хуков; jscpd 71 файл / 0 клон-пар, сложность 94 файла / 0 находок, слои — python 82 и ts 31, eslint-warnings 1 при снимке 1 |
| `check_deps_audit.sh` | **PASS** — exit 0 (см. N1–N3 про то, что он печатает) |
| `check_baseline_ratchet.sh` | **PASS** — 15 снимков, `deps_audit_baseline.txt` только вниз |
| `check_diff_coverage.sh` | **PASS** — изменённых prod-файлов нет |
| `okf_sync_gate.py --base origin/main` | **PASS** — 5 концептов, 0 предупреждений |
| `contour_doctor.py` | **PASS** — AUTO 47 · WEAK 17 · ABSENT 0 · TOOL 3 · SKIP 1 · DEAD 0; аудит в его пробе не исполняется (нет pip-audit/npm) — N1 ему не видна |
| `delivery_check.py --diff-base origin/main` | 0 ошибок; предохранитель — 3 файла, net +86 |
| CI PR #46 | **PASS** — `backend`, `gates`, `delivery` |

### Оставшиеся предупреждения

- **Реляционный оракул (§6.5)** — решение человека 2026-08-12, зависимость для
  тестов-свойств не добавляется. Differential здесь — по артефакту: бандл до и после
  обновления побайтно одинаков.
- ~~`human_ok_spec: deferred`~~ — снято: примеры V1–V8 подписаны human:anthony
  2026-10-23 на мерже, как он и решил.

## Перед `merge_guard` (L49)

`scripts/merge_guard.sh` одалживает симлинками `frontend/node_modules` и `backend/.venv`
**основного клона**, где сейчас vitest 2.1.9 и anyio 4.14.1: smoke мержа прогонит старый
тулчейн и будет зелёным не про эту поставку. В основном клоне до `merge_guard`:
`cd frontend && npm install --no-save vitest@5.0.5 vite@6.4.5` и
`cd backend && uv pip install anyio==4.14.2 urllib3==2.8.0 certifi==2026.10.19 virtualenv==21.14.13 packaging==26.3 python-discovery==1.6.4`;
после мержа — `npm ci` и `uv sync --all-extras`.

## Ревью рисковых мест (§12.5)

1. **цепочка гейтов** (`scripts/lint/`, `pre-commit-config`, `quality.yml`) — дифф
   добавляет шаг `check_deps_audit.sh` в джобу `gates` и тает `deps_audit_baseline.txt`;
   скрипты гейтов не тронуты. Что реально может сломаться: шаг краснит чужие PR, когда
   выходит новый advisory, — это работа гейта, выход — обновление или подписанный
   `deps_audit_waiver`. Снимок только вниз — `check_baseline_ratchet.sh` OK. Тихая
   сторона — N1: без реестра js-половина зеленеет.
2. **производительность** (`re.compile`) — одна регулярка `SCRIPT_RE` на модуль теста,
   разбор двух YAML на прогон; горячего пути нет, риска нет.
3. **новый модуль** (`test_manual_gates_run_in_ci`) — чистые функции `_manual_only_hooks`,
   `_ci_steps`, `_runs_always` над `.pre-commit-config.yaml` и `.github/workflows/*.yml`,
   состояния нет. Слепота сторожа закрыта `test_manual_sweep_is_not_blind`: если разбор
   конфига сломается, `MANUAL_HOOKS` опустеет и этот тест покраснеет, а не уйдёт в skip.
4. **транзакция БД** (`commit`) — токен из имени `.pre-commit-config.yaml`, которое читает
   сторож; базы дифф не касается — ни моделей, ни репозиториев. Риска нет.
5. **версии зависимостей** (`vitest`, `vite`, `anyio`) — бандл побайтно прежний; anyio —
   патч под WS-тестами, на linux джоба `backend` зелёная.

## Исполнение рисковых путей (§12.6)

`runtime_paths: frontend/package.json` — версия vite, то есть dev-сервер (`scripts/dev.sh`).
Исполнено `npx vite --port 5273 --strictPort` без бэкенда: «VITE v6.4.5 ready», `/` —
приложение с React refresh, пять префиксов прокси уходят на `127.0.0.1:8000` (в логе
vite `ECONNREFUSED` на каждый, `/ws/voice` — `ws proxy error`), чужой путь — SPA 200.
Сервер погашен, порт свободен. at=2026-10-23

## Уроки (предварительные id — ведущий сверит с INDEX)

- **L94:** гейт, вписанный только на стадию `manual`, не исполняется нигде, а
  `check_gate_coverage.sh` стадий не читает и считает его подключённым: аудит зависимостей
  молчал с развёртывания при critical=2 high=6. «Вписан» и «исполняется» — разные вопросы;
  сторож на класс — у хука `manual` обязан быть шаг CI с `if: always()`.
- **L95:** отсутствие строки «пропущено» доказывает только ту половину гейта, у которой
  есть состояние «не проверено». js-половина аудита читает упавший `npm audit` как ноль:
  critical=2 в дереве, нет реестра — exit 0 и вывод честного зелёного. Свидетель js в
  CI — строка `npm ci` той же джобы, а не гейт; в каждом «проверено» спрашивай, чем
  отличается «не смог».
- **L96:** `uv lock --upgrade-package` без пина берёт свежайшее, а не закрывающее
  (anyio 4.15.1 вместо 4.14.2, certifi от дня поставки): правило — свежий патч наименьшей
  линии, закрывающей все advisories. Обновление тулчейна проверяется differential по
  артефакту — хэши бандла до и после, — а не только «тесты зелёные».

## Verdict

**READY FOR HANDOFF** — V1–V8 зелёные, CI PR #46 зелёный по всем трём джобам. Три
дефекта канонного гейта (N1–N3) — вопрос человеку с готовыми предложениями; до правки N1
свидетель js-половины в CI — строка `npm ci`. Перед `merge_guard` — освежить окружение
основного клона (L49).

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **6**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
V2	assert steps, f"в джобе gates (quality.yml) нет шага, зовущего {DEPS_AUDIT}"
V2	assert any(_runs_always(step) for step in steps), "шаг аудита без if: always()"
V3	assert MANUAL_HOOKS.get("deps-audit") == [DEPS_AUDIT]
V3	assert scripts, f"{hook_id}: в entry нет пути scripts/… — искать в CI нечего"
V3	assert steps, f"{hook_id}: {script} не зовёт ни один шаг CI — гейт не исполняется нигде"
V3	assert any(_runs_always(step) for step in steps), (
```

Каждое утверждение ведёт к примеру спеки (V2, V3), а примеры V1–V8 подписаны
human:anthony 2026-10-23 (`human_ok_spec: yes`) — подпись V2 и V3 покрывает и эти
утверждения.

asserts_without_example: 0

asserts_reviewed_by: n/a (все 6 утверждений ведут к примерам V2 и V3, подписанным human:anthony 2026-10-23)

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 8 code (+8 process docs) / +375/-1390 (net -1015) |
| commits | 13 |
| time_to_accepted_spec | 2.6h |
| rework_after_done | 0 commit(s) after first phase: handoff |
| harness_hardened | yes — .github/workflows/quality.yml, backend/tests/test_manual_gates_run_in_ci.py (новый оракул), scripts/lint/adapted.json, scripts/lint/deps_audit_baseline.txt |
| implement_retries | 2 — `uv lock --upgrade-package` без пина дал anyio 4.15.1 и certifi от дня поставки, перелочено с пинами (D1, D2); `main` ушёл на накат 2.74/2.07 — ветка перебазирована до первого push, гейты перепрогнаны (V7: 272 → 275 базы + 3); перед handoff слит `origin/main` 384f8b2 |
| verify_fails_before_green | 0 — CI PR #46 зелёный с первого прогона (`40008573567`, `40008573576`, затем `40010473853`, `40010473874`); красные прогоны верификации — только намеренные мутации MS1–MS5 |
| est_token_or_cost | n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
