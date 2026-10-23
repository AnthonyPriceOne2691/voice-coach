# Spec: аудит уязвимых зависимостей — зелёный и исполняется в CI (deps-refresh)

## Задача

Остаток обновления контура 2.69 (`delivery/STACK-ACCEPTANCE.md`, «Остатки обновления
2.69»): гейт `deps-audit` (`scripts/lint/check_deps_audit.sh`) красный и **не
исполняется нигде**. Его хук стоит в `.pre-commit-config.yaml` на стадии `manual` —
по бюджету pre-push (CQG §8.6) он CI-only, — а шага в `quality.yml` нет. Канон держит
этот шаг в джобе `gates` («в CI обязателен», CQG §3).

Замер 2026-10-23 на `main` (`73342b3`), тем же вызовом, что в CI:

```
deps-audit: python-половина мерена по uv.lock — дерево продукта, как в проде
  ✗  py_total: 20 (было 0)
  ✗  js_critical: 2 (было 1)
  ✗  js_high: 6 (было 3)
  ✗  js_total: 24 (было 14)
  ✗  критические/высокие уязвимости: critical=2 high=6 — снимком не легализуются
exit 1
```

- **Python** (по `backend/uv.lock`, 20 записей pip-audit, 16 уникальных advisories):
  anyio 4.14.1 (3, фикс 4.14.2), urllib3 2.7.0 (3, фикс 2.8.0), virtualenv 21.7.0
  (9 уникальных, фиксы до 21.14.9), certifi 2026.6.17 (1, фикс 2026.10.19). С замера
  18.10 (py 14) появились certifi и пять новых у virtualenv.
- **Frontend** (`npm audit`, 12 уязвимостей): critical — vitest ≤ 4.1.10 и tinypool;
  high — vite ≤ 6.4.3 и пять транзитивных (brace-expansion, browserslist, js-yaml,
  nanoid, source-map-js); moderate — @vitest/mocker, esbuild ≤ 0.24.2 (вложенная копия
  vite 5 у vitest 2), vite-node, baseline-browser-mapping. Фикс vitest — только 5.x:
  три мажорные версии от нынешней 2.1.9.

## Инварианты

1. **Поведение продукта не меняется.** Бандл прежний, тесты те же — ни один не
   ослаблен; если API раннера переехал, тест адаптируется с сохранением утверждения.
2. **critical/high снимком не легализуются, снимок только тает** (CQG §3, правило
   самого гейта). Снимок вверх не пересъёмывается.
3. **Гейт, вписанный только на стадию `manual`, не исполняется нигде.** У такого
   гейта обязан быть шаг CI, и стоять он обязан с `if: always()` — иначе упавший
   шаг выше уносит его из прогона молча (Delivery §3.1a). Сторож — на класс, не на
   случай: `check_gate_coverage.sh` стадий не читает и считал этот гейт подключённым.
4. **Минимальная линия.** Для semver-пакета — свежий патч наименьшей линии, которая
   закрывает все известные advisories; мажорный скачок — только там, где в текущей
   линии фикса нет (vitest).

## Что меняется

1. **Frontend:** vitest `^2.1.8` → `^5.0.5`, vite `^6.0.3` → `^6.4.5` (пир vitest 5 —
   `vite >= 6.4.0`); `npm audit fix` поднимает транзитивные без мажоров. Из дерева
   уходят tinypool, vite-node и вложенные vite 5 / esbuild 0.21.
2. **Backend:** только `backend/uv.lock` — anyio, urllib3, certifi, virtualenv (и что
   новый virtualenv требует). `pyproject.toml` не меняется.
3. **CI:** канонный шаг «Vulnerable dependencies» в джобе `gates` (`quality.yml`).
4. **Сторож класса** «у хука на стадии `manual` есть шаг CI» — pytest в `backend/tests`.
5. **Снимок** `scripts/lint/deps_audit_baseline.txt` тает до нулей.
6. **Записи контура:** `adapted.json` (из записи `quality.yml` снимается «Vulnerable
   dependencies — НЕ подключены»), строка аудита в STACK-ACCEPTANCE — ЗАКРЫТО с
   числами до и после.
7. **Doc 07** — Node 22 LTS (vitest 5 требует ≥ 22.12), vite `^6.4`.

## Что НЕ меняется

- Код продукта (`backend/app`, `frontend/src`) — ни строки.
- `backend/pyproject.toml` (его правят параллельные ветки) и `frontend/package.json`
  сверх двух версий; @vitejs/plugin-react 4.7.0 и jsdom 25 совместимы и не трогаются.
- Скрипт гейта `check_deps_audit.sh` — канон как есть. Найденное в нём (ложное
  WARNING на зелёном пути, двойной счёт `js_total`, а на verify — js-половина, читающая
  упавший `npm audit` как ноль) — вопрос человеку и кандидат в апстрим, а не правка
  поставки: менять поведение проверки — решение человека.
- Хук `deps-audit` в pre-commit остаётся на стадии `manual`: замер канона — 24.5 с
  при бюджете pre-push 10 с (§8.6).
- Мутационный гейт и `filterwarnings = ["error"]` — свои поставки.

## Acceptance examples

| # | Вход | Ожидаемый выход |
|---|---|---|
| V1 | `env LINT_PY_SRC=backend/app LINT_COV_PKG=app LINT_FE_DIR=frontend LINT_BE_DIR=backend bash scripts/lint/check_deps_audit.sh` на дереве поставки | exit 0, ни одного critical/high; счётчики `py_total=0 js_critical=0 js_high=0 js_total=0` (на `main` — 20 / 2 / 6 / 24 и exit 1) |
| V2 | PR этой поставки в `main` | в джобе `gates` шаг «Vulnerable dependencies» с `if: always()` зовёт `scripts/lint/check_deps_audit.sh`; в его логе python-половина «мерена по uv.lock», строк «○ пропущено» нет, шаг зелёный |
| V3 | хук на стадии `manual` без шага CI, зовущего его скрипт | сторож красный и называет хук; с шагом без `if: always()` — тоже красный |
| V4 | `npm test` на vitest 5 | те же 57 тестов в тех же 11 файлах зелёные, тесты не правлены; умолчание — node: без строки `// @vitest-environment jsdom` компонентный тест падает `document is not defined` |
| V5 | `npm run build`, `npm run lint`, `prettier --check src` | сборка проходит, бандл побайтно прежний (`index-DEbu37-m.js`, `index-uwZHTTsa.css`); eslint — 0 ошибок и прежнее 1 предупреждение |
| V6 | `npx vite --port 5273 --strictPort` без бэкенда | сервер стартует на 5273; `/` отдаёт приложение; `/sessions`, `/vocabulary`, `/settings`, `/health` и `/ws` уходят прокси на `127.0.0.1:8000` — ошибка прокси, а не страница приложения |
| V7 | `UV_FROZEN=1 ./scripts/run_checks.sh` на новом `uv.lock` | весь сьют зелёный — на базе `a4a0dce` 275 тестов, с поставкой 278 (+3 сторожа V2/V3); coverage ≥ 85 %, mypy strict и ruff чистые |
| V8 | в дерево возвращается пакет с critical (vitest 2.1.9) | гейт красный (exit 1) при любом снимке — critical/high снимком не легализуются |

## Non-functional

- Новых прямых зависимостей нет — только версии существующих.
- Цена шага в CI — один прогон гейта, ~30 с (локальный замер 29.5 с) при бюджете
  джобы 20 минут; гейт ходит в сеть за базами уязвимостей.
- Node: vitest 5 требует `^22.12.0 || ^24 || >=26`; CI ставит `node-version: "22"`
  (свежая 22.x), локально 24.12.

## Оракулы

- **V1, V8** — прогон гейта на дереве поставки и мутация (eval-smoke).
- **V2** — лог шага в CI на PR; структура шага — pytest-сторож.
- **V3** — pytest-сторож класса; до подключения шага красный.
- **V4, V5** — существующий сьют фронта, сборка, линтеры; мутация docblock'а.
- **V6** — запуск dev-сервера и проба маршрутов (eval-smoke, исполнение рискового пути).
- **V7** — `run_checks.sh`; на linux — джоба `CI` на PR.

## Объём

Предохранитель считает `frontend/package.json` и сторожа; lock-файлы — сгенерированные,
`.github/workflows/`, `scripts/lint/`, `delivery/` — механика контура (Delivery §3.4).
