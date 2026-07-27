# Code Quality Gates — правила чистого кода и их enforcement

> **Карта стека (вход для агента):** [AGENT_STACK.md](AGENT_STACK.md)  
> **Слой в стеке:** ② качество кода — после
> [AGENT_DELIVERY_HARNESS.md](AGENT_DELIVERY_HARNESS.md), перед
> [OKF_KNOWLEDGE_BUNDLE.md](OKF_KNOWLEDGE_BUNDLE.md).  
> Этот файл = oracles на **форму** кода. Как вести фичу — в Delivery; канон
> домена — в OKF. Если в проекте ещё нет `delivery/` — сначала Delivery
> ([AGENT_STACK.md](AGENT_STACK.md) §2.A), потом этот канон.

**Canon version:** `cqg@1.7` · 2026-07-27 (Changelog — в конце файла). Версию впиши в
`delivery/CONSTITUTION.md` / `STATUS.md` (`stack:`) при развёртывании.

**Самодостаточный документ.** Всё, что нужно для этой системы качества, — здесь: правила с порогами,
механика гейтов и **полные исходники всех скриптов и конфигов** (Приложения A и B). Кладёшь этот один
файл в проект — и разворачиваешь систему из него, ничего больше копировать не нужно.

> **Язык:** проза — русский, идентификаторы / команды / код — английские.
>
> **Стек:** ruff + mypy (backend), ESLint + Prettier + TypeScript (frontend), pre-commit, import-linter, jscpd.
> Пути и имена пакетов настраиваются env-переменными (§6) — по умолчанию `backend/`-и-`frontend/`-layout.

### Применимость (читать до развёртывания)

Документ **не** stack-agnostic. Готовые к запуску скрипты рассчитаны на
**Python-backend (FastAPI-style слои, SQLAlchemy/Alembic) + TypeScript/React-frontend**.
`env`-переменные §6 настраивают *пути*, а не *язык*. Для другого стека:

| Слой | Переносится как есть | Требует адаптации |
|---|---|---|
| 2026-07-27 | **1.7** | `check_gate_coverage.sh` доработан по разбору боевой версии: перечисление через `git ls-files` (только отслеживаемые — как остальные гейты §4; локальный черновик больше не ложное срабатывание), причина исключения печатается на каждом прогоне (устаревшее исключение видно глазами), ноль гейтов = ошибка, а не тихий пропуск. Мета-гейт требует подключения и самого себя. Плюс «Карта ролей» в блоке «Применимость»: инвариант — роль, а не имя файла (роль может занять скрипт с другим именем — тогда §3 и репозиторий расходятся молча) |
| 2026-07-27 | **1.6** | Мета-гейт `check_gate_coverage.sh`: каждый скрипт `scripts/lint/` обязан быть подключён к pre-commit/CI (и наоборот — конфиг не ссылается на отсутствующий файл), исключения только с причиной в `is_exempt()`. Причина: на первом развёртывании jscpd был извлечён и адаптирован, но не вписан в конфиг — приёмка показала 7/7 зелёных. Плюс: запрет собирать конфиг «по смыслу» (§5), порядок «полнота → зелёность», гейт в §3/§4/Приложение B/CI |
| 2026-07-27 | **1.5** | §8.5 переделан: тарифо-независимая база принуждения (`needs:`, `scripts/merge_guard.sh` — гейты на СЛИТОМ состоянии, pre-push hook, workflow `main-guard` с issue на красное), защита ветки вынесена в §8.5.3 как усиление + таблица «чем закрыт каждый её пункт на Free» и честный остаток (force-push, обход админом) |
| 2026-07-27 | **1.4** | Помечены два места, где развёртывание упирается в реальность проекта: §6 «Первый прогон» (как отличить «пути не настроены» от настоящих нарушений + список запрещённых «решений») и §8.5 помечен как РУЧНОЙ шаг вне репозитория, который не проверит ни один скрипт; шаг 9 в §5 |
| **Механика** | baseline-ratchet (per-path и global-count), `STRICT=0`, `--generate`/`--tighten`, `pass_filenames: false`, резолв `REPO_ROOT` | — |
| **Гейты** | `file-length`, `jscpd-DRY` (jscpd умеет ~150 языков), `no-grab-bag-module` (сменить паттерн имён), secrets-хук | `config-access`, `di-indirection`, `service-no-web` — grep-паттерны переписать под язык (`os.Getenv`, `process.env`, …) |
| **AST-гейты** | Идея (`silent-except`, `inline-prompt`) | Реализация: `check_ast_gate.py` — только Python `ast`; для TS/Go/Rust нужен свой парсер или ESLint-правило |
| **Линтеры** | Роль в цепочке | ruff/mypy → `golangci-lint` / `clippy` / `biome`; `import-linter` → `eslint-plugin-boundaries` / `go-arch-lint` / `cargo-deny` |
| **Правила §2** | §2.1 размеры, §2.4 «ошибки не молчат» / DRY-данные / config, §2.5 coverage, §2.7 secrets | §2.2 (ruff/mypy/tsc-специфика), §2.3 слои `api→services→repository→models`, §2.6 Alembic |
| **diff-coverage** | Порог 70% и роль DoD-шага | Раннер: `pytest --cov` → `go test -cover` / `vitest --coverage` |

Правило при адаптации: **сохраняй механику, меняй паттерн**. Новый гейт должен уметь
`--generate`, `STRICT=0` и baseline-файл (§7), иначе он выпадет из ратчета.

#### Карта ролей — заполняется при развёртывании

Практика (первое развёртывание, Swift-проект) показала пробел: адаптация — это не
всегда «поправить паттерн внутри скрипта». Бывает, что **роль занимает другой
скрипт с другим именем** (`check_eslint_warnings.sh` → `check_swiftlint_ratchet.sh`),
и тогда таблица §3, ключёванная каноническими именами файлов, перестаёт совпадать
с репозиторием: гейт на месте, а строка канона выглядит непокрытой (и наоборот).

**Инвариант — роль, а не имя файла.** При развёртывании заполни таблицу и положи
её в `delivery/STACK-ACCEPTANCE.md` (Delivery A.12):

| Роль (инвариант) | Канонический скрипт | В этом проекте | Статус |
|---|---|---|---|
| Доступ к настройкам только типизированно | `check_grep_gate.sh --rule config-access` | | |
| DI вместо importlib-магии | `check_grep_gate.sh --rule di-indirection` | | |
| Сервис не знает про web | `check_grep_gate.sh --rule service-no-web` | | |
| Нет модулей-помоек | `check_grep_gate.sh --rule no-grab-bag-module` | | |
| Ошибки не молчат | `check_ast_gate.py --rule silent-except` | | |
| Длинные промпты — в файлы | `check_ast_gate.py --rule inline-prompt` | | |
| Длина файлов под контролем | `check_file_length.sh` | | |
| Копипаст не растёт | `check_jscpd_gate.sh` | | |
| Warnings линтера не растут | `check_eslint_warnings.sh` | напр. `check_swiftlint_ratchet.sh` | адаптирован |
| Направление зависимостей | `import-linter` | | |
| Покрытие изменённого кода | `check_diff_coverage.sh` | | |
| Снимки только вниз | `check_baseline_ratchet.sh` | | |
| **Все гейты подключены** | `check_gate_coverage.sh` | | |

Статус — один из: `как есть` · `адаптирован (<имя>)` · `n/a + причина`.
`n/a` без причины не бывает: причина идёт в `not_wired_reason()` мета-гейта, где
печатается на каждом прогоне.

---

## 0. Как пользоваться

- **Карта стека** — [AGENT_STACK.md](AGENT_STACK.md) (порядок Delivery → CQG → OKF).
- **Правила** (что можно/нельзя, с порогами) — §2 (вкл. **§2.7 secrets**). Самодостаточны для применения и ревью.
- **Гейты** (чем прибито на коммите) — §3, механика каждого.
- **CI** (обязательный неподделываемый прогон тех же гейтов) — **§8**.
- **Развернуть в проекте** — §5 (два способа) + §6 (настройка путей через env).
- **Исходники** — Приложение A (6 скриптов), §8.2 (7-й, CI-only) и Приложение B (конфиги, вкл. CI-workflow):
  всё дословно, готово к раскладке по путям.
- **Связанные каноны:** [AGENT_DELIVERY_HARNESS.md](AGENT_DELIVERY_HARNESS.md) ·
  [OKF_KNOWLEDGE_BUNDLE.md](OKF_KNOWLEDGE_BUNDLE.md).
- **HITL / agent stop-gates** — не здесь, а в Delivery §10.

**Стоимость чтения.** Канон — §1–§8 (≈710 строк): правила, пороги, механика, CI.
Приложения A и B — **bootstrap payload** (≈1320 строк, 65% файла): дословные
исходники, нужны только при развёртывании или правке конкретного скрипта.
Ревью кода и ответ на «можно ли так писать» не требуют приложений вообще.

---

## 1. Философия

1. **Health-by-default.** Правила применяются **сразу при написании нового кода**, не «потом отрефакторим».
   Новый код обязан быть чистым; легаси — тает (см. baseline-ratchet).
2. **Гейт vs ревью.** `[гейт]` = прибито на коммите, не пройдёт механически. Остальное (SRP, атомарность,
   OCP/LSP/ISP, docstring↔поведение) — **свойства-оценки**, гейтом не ловятся без ложных срабатываний → только
   judgment-ревью по чек-листу.
3. **Одна тема = «одна тарелка».** Файл несёт одну ответственность; имя файла = тема. Шов для разбиения ≠ размер —
   пилить по ответственностям. Безымянные `utils/misc/common/helpers.py` запрещены (тематический
   `<topic>_helpers.py` рядом с фичей — можно).
4. **DRY-данные с ПЕРВОГО повтора.** Rule-of-three — для **логики**. Для **данных** (константы, enum-строки,
   ключи, статусы, тексты), читаемых ≥2 модулями, — единый источник + импорт сразу. Копия = «баг с таймером».
5. **Ошибки не молчат.** Каждый `except`/fallback — либо лог с контекстом, либо `raise`. Мисконфиг — fail-fast
   на старте, не тихий дефолт.

### Baseline-ratchet (сердце системы)

Как ввести жёсткое правило в проект с тоннами легаси-нарушений, не переписывая всё разом:

- **Снимок** текущих (легаси) нарушений живёт в `scripts/lint/*_baseline.txt`.
- Гейт **падает только при РОСТЕ** относительно снимка. Новый / чистый файл держится на **hard 0** (или hard-лимите).
- Снимок **тает** — правишь легаси-файл → заодно чистишь его нарушения и пере-снимаешь снимок **вниз**
  (`--generate` / `--tighten`).
- **Инвариант: снимок только вниз, вверх — НИКОГДА.** Застывший или выросший baseline = провал ратчета.

Две формы снимка:
- **Per-path** (`<count>:<path>`) — у каждого легаси-файла свой потолок; чистый файл = 0.
- **Global single-number** — одно число на весь фронт/бэк (jscpd clone-пары, сумма eslint-warnings); падает при росте суммы.

---

## 2. Правила чистого кода

Пороги, чем прибито, escape-хатч.

### 2.1. Размер и сложность

| Правило | Порог | Enforced | Escape |
|---|---|---|---|
| **Файл** | prod **≤500** строк / tests **≤1000**; конфиги ≤500; при 400+ строк — сигнал к сплиту | **Гейт** `file-length` | `STRICT=0` (soft, виден в PR); baseline +30; exemption +50 |
| **Функция — длина** | soft **50** / hard **80** строк | **Гейт** ruff / ESLint | `# noqa: <CODE> -- <причина>` |
| **Функция — сложность** | цикломатическая soft 8 / **hard 10** (ruff `C901`, mccabe) | **Гейт** ruff / ESLint | `# noqa: C901 -- <причина>` |
| **Функция — аргументы** | soft 5 / **hard 8** (web-фреймворк DI — исключение) | **Гейт** ruff / ESLint `max-params 5` | — |
| **Функция — вложенность** | soft 3 / hard 4 | ESLint `max-depth 4`; ревью на бэке | — |
| **Функция — returns** | soft 6 (ruff `max-returns=6`) | **Гейт** ruff | `# noqa: PLR0911 -- <причина>` |

Ruff pylint-лимиты: `max-args=8`, `max-positional-args=5`, `max-branches=12`, `max-returns=6`,
`max-statements=50`, mccabe `max-complexity=10`.

Каталог **паттернов декомпозиции** (только ревью): thin orchestrator + phase-helpers; mutable accumulator
(`@dataclass(slots=True)`); declarative dispatch table (при 4+ однотипных `if/elif`); strategy-реестр (OCP);
`@dataclass(frozen=True)` classification вместо `tuple[set, set, ...]`; cross-flow shared logic → `<domain>/queries.py`.
**⚠️ Паттерны `importlib.import_module`-indirection и monkeypatch-propagation — legacy-only, в новом коде запрещены**
(ловит `di-indirection`).

### 2.2. Стиль и типы

- **Ruff (backend)**, наборы: `E W F I N UP B C4 C90 SIM RUF ASYNC S PT RET PIE PL TRY400 DTZ`. `line-length=100`,
  format double-quote. Полный select/ignore — Приложение B.
- **mypy `--strict`**: новые модули — 0 errors; новые суппрессы не добавлять; регрессия = блок.
- **Prettier (frontend)**: `printWidth=100`, `tabWidth=2`, `singleQuote`, `trailingComma=all`. **Версия пинится
  exact** (без `^`) — caret-дрейф форматтера даёт массовые ложные diff'ы.
- **TypeScript strict-флаги**: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`,
  `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noUnusedLocals`, `noUnusedParameters`,
  `noImplicitReturns`, `verbatimModuleSyntax`.
- **Escape (дословно):** `# type: ignore[code]` — только с конкретным кодом, **никогда голый**;
  `# noqa: <CODE>` с кодом и комментарием; `# noqa: BLE001 -- <причина>` для осознанного broad-except.

### 2.3. Архитектура и слои

| Правило | Суть | Enforced |
|---|---|---|
| **Направление зависимостей** | `api → services → repository → models`; слой интеграций — лист; `models` не знает про `api`; `repository` не знает про `services` | **Гейт** `import-linter` |
| **Тонкие роутеры** | Эндпоинт **≤30 строк**: валидировать → достать актора из контекста запроса → `await service.do(...)` → response schema. DTO — в `schemas.py` (`extra="forbid"`), не в роутере | Ревью; `import-linter` |
| **Сервис не знает про web** | Сервисный слой (`services/`, `service.py`) не импортирует web-фреймворк; auth в эндпоинте, сервис принимает id-параметры | **Гейт** `service-no-web` |
| **DI, не importlib-магия** | Явные зависимости через параметры/`Protocol`; запрет `pkg\|session\|ctx: Any`, `import_module("...")` в новом коде | **Гейт** `di-indirection` + mypy |
| **Нет grab-bag модулей** | Запрещены `utils/misc/common/helpers.py` без темы (`_helpers.py` с подчёркиванием — ок) | **Гейт** `no-grab-bag-module` |
| **SOLID / design-doc freshness** | SRP-флаги (>30 импортов, файл по 2+ темам, функция «5 дел»); OCP/LSP/ISP; PR, меняющий инварианты гейт-цепочки, обновляет связанный design-doc в том же PR | **Ревью** |

### 2.4. Ошибки, данные, конфиг, промпты

| Правило | Суть | Enforced | Escape |
|---|---|---|---|
| **Ошибки не молчат** | `except` → лог+контекст (id сущности/операции) ИЛИ `raise`; мисконфиг = fail-fast; запрет security-fallback | **Гейт** ruff `S110`/`S112`/`TRY400` + AST `silent-except`; `BLE001` per-module | `# silent-ok: <причина>` (AST-гейт); `# noqa: BLE001` |
| **DRY-данные** | Данные-константы (enum/статусы/ключи/тексты) ≥2 модулей → единый источник с 1-го повтора | **Гейт** `jscpd-DRY`; ревью | — |
| **Config только typed** | Доступ только `config.X` / typed `Settings`; дефолт 1 раз в `config/<domain>.py`; запрет `getattr(config,...)`, `os.getenv`/`os.environ` вне `config/` | **Гейт** `config-access` + mypy | ленивый `import config` внутри функции (про доступ, не импорт) |
| **Промпты не инлайном** | LLM-промпт >5–10 строк → отдельный `*.md`-файл, lazy-load + cache | **Гейт** `inline-prompt` (AST) | `# noqa: PLW0603 -- single-shot module cache` |
| **Docstring = контракт** | Обещания (no-raise/атомарность/семантика возврата) правятся с кодом в том же PR; комментарий = intent, не changelog | **Ревью** | — |

### 2.5. Тесты

- **Coverage-таргеты:** backend total **≥70% → ≥80%**; critical paths **≥85%**; integrations **≥75%**; frontend **≥60%**.
- **diff-coverage изменённых prod-файлов ≥70%** (`check_diff_coverage.sh`, ручной DoD-шаг, не commit-хук).
- **TDD-light обязателен для функций >200 строк:** характеризационные тесты → декомпозиция → прогон бит-в-бит →
  unit на каждый extracted helper (в том же PR).
- **Изоляция:** отдельная тестовая БД, внешние API off через env. Реальные API — только под
  `@pytest.mark.integration` (в CI off). PT004 (фикстура без return) прибита ruff.

### 2.6. Alembic и процесс

- **Revision ID ≤32 символа**: `alembic_version.version_num` = `VARCHAR(32)` по умолчанию → длиннее =
  `StringDataRightTruncation` на `UPDATE`. Короткий осмысленный slug. 33–64 — только если pre-migration hook
  расширяет колонку до `VARCHAR(64)`.
- **`upgrade head` во ВСЕХ средах**: dev / staging / prod / тестовая БД — у каждой свой `DATABASE_URL`; prod — по
  релиз-процессу (окно/бэкап/runbook).

### 2.7. Secrets и mechanical security

**Граница:** этот раздел — *нельзя вкоммитить / захардкодить*. HITL на prod-деплой
и опасные действия агента — в [AGENT_DELIVERY_HARNESS.md](AGENT_DELIVERY_HARNESS.md) §4 / §10.3.

| Правило | Суть | Enforced | Escape |
|---|---|---|---|
| **Нет секретов в git** | API keys, tokens, private keys, `.env` с прод-значениями не в коммите | **Гейт** `detect-secrets` или `gitleaks` (pre-commit) + `.gitignore` для `.env` | baseline/allowlist инструмента; никогда «просто отключить» |
| **Нет хардкода секретов в коде** | Строки вида `sk-…`, `BEGIN PRIVATE KEY`, `password = "…"` в prod-путях | **Ревью** + bandit/ruff security where enabled; желательно тот же secrets-scanner на staged diff | тестовые фикстуры с явным `fake-` / `test-` префиксом в allowlist |
| **Секреты только из env/secret store** | Чтение через typed config / vault; не логировать значения | **Ревью** + CQG config-access (доступ к env вне `config/` уже режется) | — |
| **Промпты/skills** | Длинные промпты → файлы; индекс в `skills/README.md` (см. Delivery §11) | **Гейт** `inline-prompt` | — |

**Минимум при развёртывании CQG:** добавить в `.pre-commit-config.yaml` один
secrets-хук (пример в конце Приложения B рядом с другими hooks). Если хука ещё
нет — STATUS Delivery: считать security-oracles **weak** и не пушить в remote
без ручного просмотра diff на секреты.

Типичный фрагмент (выбери один инструмент и запини rev):

```yaml
  # Secrets — mechanical; не замена HITL Delivery.
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  # альтернатива: gitleaks
  # - repo: https://github.com/gitleaks/gitleaks
  #   rev: v8.21.2
  #   hooks:
  #     - id: gitleaks
```

Первичная генерация baseline (detect-secrets):

```bash
detect-secrets scan > .secrets.baseline
# закоммить baseline; дальше хук падает только на *новые* находки
```

---

## 3. Каталог гейтов

**11 commit-гейтов** (прибиты `.pre-commit-config.yaml`, таблица ниже) + **1 ручной**
(`diff-coverage`) + **рекомендуемый 12-й** secrets-scanner (§2.7). Одиннадцатый —
**мета-гейт `gate-coverage`**: он проверяет, что остальные вообще подключены.
Читай таблицу **построчно** при сборке конфига; «по смыслу» — это как раз тот
способ, которым гейт теряется. Сверх них в
`.pre-commit-config.yaml` живут 5 стандартных хуков-линтеров (ruff, ruff-format, mypy,
eslint, prettier) — они не «гейты-ратчеты», а базовая проверка, поэтому в этой таблице их нет. Все скрипты lint — в `scripts/lint/`,
резолвят `REPO_ROOT` через `git rev-parse --show-toplevel` до любого `cd`. Общий env: **`STRICT=0`** переводит гейт в
soft-режим (печатает предупреждение, `exit 0`) — аварийный обход, виден в PR.
**Secrets-хук в soft не переводят** без явного human waiver в PR.

| Гейт | Команда | Что ловит | Порог | Baseline | Пере-снятие |
|---|---|---|---|---|---|
| config-access | `check_grep_gate.sh --rule config-access` | `getattr(config,…)`, `os.getenv`, `os.environ` вне `config/` | per-file ратчет | `config_access_baseline.txt` | `--rule config-access --generate` |
| di-indirection | `check_grep_gate.sh --rule di-indirection` | `(pkg\|session\|ctx): Any`, `import_module("…")` | per-file ратчет | `di_indirection_baseline.txt` | `--rule di-indirection --generate` |
| service-no-web | `check_grep_gate.sh --rule service-no-web` | `import fastapi` в сервис-слое (`/services/`, `service.py`) | per-file (снимок пуст → hard 0) | `service_no_web_baseline.txt` | `--rule service-no-web --generate` |
| no-grab-bag | `check_grep_gate.sh --rule no-grab-bag-module` | существование `utils\|misc\|common\|helpers.py` без темы | per-file (вне снимка = hard fail) | `no_grab_bag_baseline.txt` | `--rule no-grab-bag-module --generate` |
| silent-except | `check_ast_gate.py --rule silent-except` | broad-except без `raise`/лога/`# silent-ok:` | per-file ратчет | `silent_except_baseline.txt` | `--rule silent-except --generate` |
| inline-prompt | `check_ast_gate.py --rule inline-prompt` | LLM-промпт (≥8 строк + персона-маркер) инлайном в `.py` | per-file; порог 8 строк | `inline_prompt_baseline.txt` | `--rule inline-prompt --generate` |
| file-length | `check_file_length.sh` | prod ≤500 / tests ≤1000 строк | 500/1000; +30 baseline / +50 exemption | `file_length_baseline.txt` | `--generate` / `--tighten` |
| jscpd-DRY | `check_jscpd_gate.sh` | рост числа clone-пар (копипаст) | global count; min-tokens 50 | `jscpd_baseline.txt` | `--generate` |
| eslint-warnings | `check_eslint_warnings.sh` | рост суммы ESLint-warnings фронта | global count | `eslint_warnings_baseline.txt` | `--generate` |
| import-linter | `lint-imports` (в backend) | направление зависимостей между слоями | контракты + frozen ignore | `.importlinter` | (правка конфига) |
| **gate-coverage** *(мета)* | `check_gate_coverage.sh` | **гейт есть, но не подключён**; и наоборот — конфиг ссылается на несуществующий скрипт | все скрипты `scripts/lint/` покрыты | — (исключения в `is_exempt()` с причиной) | — |
| **diff-coverage** *(ручной)* | `check_diff_coverage.sh` | покрытие изменённых prod-файлов | `<70%` (`MIN_PCT`) | — (diff против `BASE`) | — |

### 3.1. `check_grep_gate.sh` — grep-ратчеты (4 правила)

`--rule <name>` обязателен; `--generate` пере-снимает baseline вниз. Токен-граница делается через `(^|[^A-Za-z_.])`,
а не `\b` (BSD grep на macOS `\b` не держит). Baseline-формат `<count>:<path>` (от repo-root).

| rule | PATTERN (`grep -cE`) | FILTER путей |
|---|---|---|
| `config-access` | `getattr\([[:space:]]*config` \| `os\.getenv` \| `os\.environ` (с токен-границей) | — |
| `di-indirection` | `(pkg\|session\|ctx)[[:space:]]*:[[:space:]]*Any` \| `import_module\([[:space:]]*["']` | — |
| `service-no-web` | `^[[:space:]]*(from fastapi\|import fastapi)` | `/services/` \| `service\.py$` |
| `no-grab-bag-module` | `^` (любая строка → файл существует = нарушение) | `/(utils\|misc\|common\|helpers)\.py$` |

### 3.2. `check_ast_gate.py` — AST-ратчеты (2 правила)

Только stdlib `ast`. `--rule inline-prompt|silent-except` обязателен; `--generate` вниз. Baseline `<count>:<path>`.

**silent-except**: нарушение = broad-except (`except:`, `except Exception`, `except BaseException`, Tuple с ними)
**И НЕ** оставляет след **И НЕ** помечен escape. «След» = `raise`; или вызов `logger.*`/`logging.*`/`log.*`/`warnings.*`;
или вызов метода/функции с именем на `log`/`warn`/`exception`/`error`/`record`/`capture`/`notify`.
**Escape:** `# silent-ok: <причина>` внутри тела хендлера.

**inline-prompt**: нарушение = строковый литерал (не docstring) длиной **≥8 строк** (`_PROMPT_MIN_LINES = 8`), чей
`.strip().lower()` начинается с персона-маркера `("ты —", "ты -", "you are", "you classify", "act as", "роль:", "system:")`.
Порог по маркеру + длине → длинные SQL/Lua/regex не ложно-срабатывают.

### 3.3. `check_file_length.sh`

Env: `MAX_LINES_PROD=500`, `MAX_LINES_TESTS=1000`, `BASELINE_HEADROOM=30`, `EXEMPTION_HEADROOM=50`. Без аргументов
сканирует всё дерево (`git ls-files '*.py' '*.ts' '*.tsx'`). `allowed` = `снимок+30` в `[baseline]`; `снимок+50` в
`[exemption]`; вне обоих (новый файл) → hard 500/1000. `--tighten` опускает снимки ужавшихся `[baseline]`-файлов
(`newsnap = min(lines, snap)`; `≤ limit` → выпадает); `[exemption]` не тает. `--generate` пересобирает обе секции.
Проектные исключения/exemption правятся в функциях `is_excluded()` / `is_exempt_path()`.

### 3.4. Global-count гейты

- **`check_jscpd_gate.sh`** — гоняет `jscpd <py-src> -f python -k 50` (min-tokens 50 ≈ 10 строк), падает при
  `N > baseline`. Нет бинаря jscpd → skip (exit 0).
- **`check_eslint_warnings.sh`** — `eslint src --format json`, суммирует `warningCount`, падает при `sum > baseline`.
  Per-file eslint-хук блокирует только **errors** — этот ратчет не даёт **warnings** расти молча. Нет бинаря → skip.

### 3.5. `check_diff_coverage.sh` — ручной DoD-шаг (не commit-хук)

Полный сьют = минуты. Env: `STRICT` (0), `BASE` (`origin/main`), `MIN_PCT` (70), `SKIP_TESTS` (0). Гоняет
`pytest --cov=<pkg> --cov-report=json`, при `STRICT=1` падает, если изменённый prod-файл `< MIN_PCT` или не покрыт.
Пустой коммит-дифф + грязное дерево → жёлтый ворнинг; после push — авто-fallback на `origin/main@{1}`. Baseline нет.

### 3.6. `import-linter`

Конфиг `.importlinter` (в backend), запуск `lint-imports`. Типы контрактов: **`forbidden`** (A не импортирует
набор B), **`layers`** (строгий порядок `api → services → repository → models`). Легаси-нарушения замораживаются в
`ignore_imports` с `TODO` — тот же принцип тающего baseline.

---

## 4. Оркестрация (`pre-commit`)

Движок — [pre-commit](https://pre-commit.com). Конфиг `.pre-commit-config.yaml` — в корне репозитория.
`fail_fast: false` — гоняются все хуки, собираются все провалы.

### Порядок хуков

1. **ruff** (`astral-sh/ruff-pre-commit`): `ruff --fix --exit-non-zero-on-fix` + `ruff-format` на backend.
2. **mypy** (local, `system`): проектный `<venv>/bin/mypy --config-file pyproject.toml`, изменённые файлы, `exclude: /tests/`.
3. **eslint** (local, per-file, только errors) + **prettier --check** — на фронт-`src/`.
4. **eslint-warning-ratchet** → `check_eslint_warnings.sh`.
5. **file-length** → `check_file_length.sh`.
6. Шесть гейтов одним `repo: local`-блоком: `config-access`, `di-indirection`, `service-no-web`, `no-grab-bag-module`,
   `silent-except`, `inline-prompt`.
7. **jscpd-dry-gate** → `check_jscpd_gate.sh`.
8. **import-linter** → `lint-imports`.
9. **gate-coverage** → `check_gate_coverage.sh` — **мета-гейт, ставится последним**:
   падает, если какой-то скрипт из `scripts/lint/` не упомянут ни в этом конфиге,
   ни в CI. Без него порядок выше — просто список пожеланий: забытый пункт не
   отличается от выполненного.

**Ключевой приём:** все скрипт-хуки — `pass_filenames: false`. Скрипты сами обходят дерево через `git ls-files`
(а не по списку staged-файлов) — так ратчет видит весь проект и один файл не «прячет» другой. Аварийный обход всего
хука: `git commit -n`.

---

## 5. Развёртывание

### Способ 1 — через Claude Code (рекомендуется)

Положи этот файл в корень проекта и дай агенту команду:

> «Разверни code-quality gates по `CODE_QUALITY_GATES.md` под структуру текущего проекта: создай файлы из
> Приложений A и B по указанным путям, настрой env-переменные путей по §6, поставь зависимости, сгенерируй
> baseline'ы и активируй pre-commit. Затем разверни CI по §8: `check_baseline_ratchet.sh` +
> `.github/workflows/quality.yml`, гейт мержа по §8.5.1–8.5.2 (`merge_guard.sh`, pre-push hook,
> `needs:` у downstream-джоб) и проставь `ci-oracles:` **по факту**: `deployed` — если включена
> серверная защита ветки, `tooling` — если гейт мержа только в репозитории (нормальный режим на
> бесплатном тарифе). Защиту ветки (§8.5.3) предлагай, только если тариф её даёт.
> Если стек проекта не Python+TS — сверься с блоком «Применимость» в шапке и адаптируй паттерны,
> сохранив механику ратчета.»

### Способ 2 — вручную

> **⚠ Правило сборки конфига (сюда попадают из-за него).** `.pre-commit-config.yaml`
> из Приложения B копируется **дословно**, а затем правятся пути/версии. Собирать
> его «по смыслу», из головы — запрещено: так теряется гейт, скрипт которого уже
> лежит в `scripts/lint/`, и приёмка этого не видит (зелёный `pre-commit` говорит
> только о перечисленных хуках). Если адаптируешь под другой стек — иди по таблице
> §3 **построчно** и на каждую строку отвечай: подключён / осознанно исключён с
> причиной в `is_exempt()`. Механическая страховка — гейт `gate-coverage`.

1. **Создай файлы** из Приложения A (в `scripts/lint/`, скрипты — `chmod +x`) и Приложения B (по указанным путям).
2. **Настрой пути** под свою структуру через env-переменные — §6.
3. **Поставь зависимости** — Приложение B (dev-зависимости backend + фронт-devDependencies).
4. **Сгенерируй baseline'ы** под текущее состояние проекта (или стартуй с hard 0, если код уже чистый):
   ```bash
   bash scripts/lint/check_grep_gate.sh --rule config-access --generate
   bash scripts/lint/check_grep_gate.sh --rule di-indirection --generate
   bash scripts/lint/check_grep_gate.sh --rule service-no-web --generate
   bash scripts/lint/check_grep_gate.sh --rule no-grab-bag-module --generate
   <venv>/bin/python scripts/lint/check_ast_gate.py --rule silent-except --generate
   <venv>/bin/python scripts/lint/check_ast_gate.py --rule inline-prompt --generate
   bash scripts/lint/check_file_length.sh --generate
   bash scripts/lint/check_jscpd_gate.sh --generate
   bash scripts/lint/check_eslint_warnings.sh --generate
   ```
   `.importlinter`: перечисли легаси-нарушения в `ignore_imports` с `TODO`.
5. **Активируй и проверь ПОЛНОТУ, а не только зелёность:**
   ```bash
   pip install -r requirements-dev.txt   # ruff, mypy, pre-commit, import-linter
   pre-commit install
   bash scripts/lint/check_gate_coverage.sh   # ← сначала: все ли гейты подключены
   pre-commit run --all-files                 # затем: зелены ли подключённые
   ```
   Порядок именно такой. `pre-commit run --all-files` зелёный при **неполном**
   конфиге — обычное дело, и выглядит как успех.
6. **(Опц.)** `.git-blame-ignore-revs` + `git config blame.ignoreRevsFile .git-blame-ignore-revs` — чтобы
   style-коммиты не шумели в blame.
7. **Secrets (§2.7):** добавь `detect-secrets` или `gitleaks` в `.pre-commit-config.yaml`,
   сгенерируй baseline при необходимости, прогони `pre-commit run detect-secrets --all-files`
   (или gitleaks). Не оставляй security-oracles weak на remote push.
8. **CI (§8) — обязательный шаг, не опциональный:** положи `scripts/lint/check_baseline_ratchet.sh`
   (§8.2, `chmod +x`) и `.github/workflows/quality.yml` (§8.3). Без этого гейты обходятся
   `git commit -n`, а baseline можно молча переснять вверх.
9. **Гейт мержа (§8.5) — обязателен, тарифа не требует:** `scripts/merge_guard.sh` (§8.5.2,
   `chmod +x`), `pre-commit install --hook-type pre-push`, `needs: [gates, delivery]` у deploy-джобы,
   workflow `main-guard`. Правило после этого: **мерж поставки только через `merge_guard.sh`**;
   `git merge` руками = `commit -n`. В STATUS — `ci-oracles: tooling`.
10. ⚠ **Защита ветки (§8.5.3) — РУЧНОЙ шаг вне репозитория и только если тариф её даёт**
   (rulesets — Team+, приватный репо — Pro+). Ни один скрипт её не проверит. Включена и
   подтверждена человеком → `ci-oracles: deployed` и
   `ci: deployed (github-actions) merge-gate: server`. Не включена → остаёмся на `tooling`
   и пишем в STATUS честный остаток: force-push и обход админом не закрыты.

**Первый прогон будет красным** — это ожидаемо. Как отличить «пути не настроены» от
«в коде правда нарушения» и что при этом делать нельзя — **§6, блок «Первый прогон»**.

---

## 6. Настройка путей (env-переменные)

Скрипты не хардкодят структуру — читают её из env (дефолты под `backend/`-и-`frontend/`-layout). Задай значения
один раз: экспортом в шелле/CI и/или в `entry:` каждого хука в `.pre-commit-config.yaml`.

| Переменная | Что задаёт | Дефолт | Кто использует |
|---|---|---|---|
| `LINT_PY_SRC` | корень прод-Python для гейтов (от repo-root) | `backend/features` | grep, ast, jscpd |
| `LINT_FE_DIR` | фронт-каталог (`package.json`/`node_modules`/`src`) | `frontend` | eslint-warnings, jscpd |
| `LINT_BE_DIR` | backend-каталог (venv/pyproject/pytest) | `backend` | diff-coverage |
| `LINT_COV_PKG` | пакет для `--cov` | `features` | diff-coverage |
| `LINT_VENV` | venv относительно backend | `.venv` | diff-coverage |

Пороги/режим тоже через env: `MAX_LINES_PROD`, `MAX_LINES_TESTS`, `BASELINE_HEADROOM`, `EXEMPTION_HEADROOM`,
`STRICT`, `MIN_PCT`, `BASE`, `SKIP_TESTS`.

Правится **в самих файлах** (не env): исключения длины — функции `is_excluded()` / `is_exempt_path()` в
`check_file_length.sh`; архитектурные слои и легаси-ignore — `.importlinter`; пути `files:`/`entry:` — в
`.pre-commit-config.yaml`. Пути в `*_baseline.txt` не правятся руками — пересоздаются `--generate` (§5, шаг 4).

### ⚠ Первый прогон в новом проекте — ожидаемо красный

**Помечено специально, чтобы это не выглядело поломкой.** Дефолты рассчитаны на
`backend/features` + `frontend`. В любом другом проекте первый
`pre-commit run --all-files` будет красным, и это **нормальное состояние
развёртывания**, а не дефект гейтов.

Красное бывает двух видов, и различить их — главная работа первого прогона:

| Симптом | Диагноз | Что делать |
|---|---|---|
| «0 файлов просканировано», гейт зелёный подозрительно быстро | `LINT_PY_SRC` смотрит не туда — гейт **не видит код** | Настроить env (таблица выше). Зелёный гейт, ничего не проверяющий, хуже красного |
| `no such file or directory`, `cd` падает | Путь из env/`entry:` не существует | Настроить env; для отсутствующего фронта гейты уже делают мягкий skip |
| Сотни нарушений в легаси-файлах | Пути настроены **верно**, это правда состояние кода | `--generate` — снять baseline, дальше ратчет вниз (§1) |
| Нарушения в **новых/чистых** файлах | Правда состояние кода | Починить код, не снимать baseline |
| Другой язык, паттерн не применим | Гейт не про этот стек | Адаптировать паттерн по блоку «Применимость» в шапке, сохранив механику |

**Чего делать нельзя** (иначе весь ратчет теряет смысл):

- ставить `STRICT=0` в конфиг или в CI, чтобы «стало зелено»;
- удалять гейт из `.pre-commit-config.yaml` вместо настройки путей;
- переснимать baseline **вверх** — это ловит `check_baseline_ratchet.sh` (§8.2),
  но на первом прогоне снимка ещё нет, так что здесь защита только дисциплиной.

Признак, что развёртывание закончено: `pre-commit run --all-files` зелёный **и**
каждый гейт в выводе показал непустое число просканированных файлов.

---

## 7. Сопровождение

- **Baseline тает, не живёт вечно.** Тронул легаси-файл → счисти его нарушения (хотя бы часть) и пере-сними снимок
  вниз (`--generate` / `--tighten`). Снимок **вверх не переснимается никогда** — прибито
  `check_baseline_ratchet.sh` в CI (§8.2).
- **Новый гейт** добавляется так же: скрипт в `scripts/lint/` (резолвит `REPO_ROOT` до `cd`, поддерживает
  `--generate` и `STRICT=0`), baseline-файл, запись в `.pre-commit-config.yaml` (`pass_filenames: false`).
- **diff-coverage** гоняется руками перед push / в DoD: `bash scripts/lint/check_diff_coverage.sh`.
- **Ревью-свойства** (SRP, атомарность, OCP/LSP/ISP, docstring↔поведение, fail-silent листья, копии-близнецы)
  гейтом не ловятся — прогоняй `git diff` глазами на рисковых диффах (DB-транзакция, gate-цепочка, новый модуль,
  интеграция, деньги/безопасность).

---

## 8. CI — обязательный дубль (pre-commit обходится)

Всё из §3–§4 живёт **на машине автора** и обходится тремя способами:
`git commit -n`, `STRICT=0`, «хук не установлен в этом клоне» (`pre-commit install`
никто не запускал). Плюс четвёртый, специфичный для ратчета: **пере-снять baseline
вверх** — `--generate` на грязном дереве легализует свежие нарушения, и локально
всё зелено. Пока те же проверки не гоняются вне машины автора, гейтов фактически нет.

**Инвариант:** CI гоняет `STRICT=1` и падает — это единственный неподделываемый
прогон. Процессная рамка — [AGENT_DELIVERY_HARNESS.md](AGENT_DELIVERY_HARNESS.md) §10.4.

### 8.1. Что CI ловит, а pre-commit — нет

| Дыра | Как закрывается в CI |
|---|---|
| `git commit -n` / хук не установлен | `pre-commit run --all-files` в джобе |
| `STRICT=0` в шелле автора | `STRICT=1` в `env:` workflow, не переопределяется |
| **Baseline пере-снят вверх** | `check_baseline_ratchet.sh` (§8.2) — диффит снимки против base-ref |
| «У меня локально проходило» (версии, venv) | Чистый runner, `requirements-dev.txt` / `npm ci` |
| Полный сьют слишком долгий локально | Отдельный шаг; `diff-coverage` из ручного DoD-шага становится обязательным |
| Фазовая дисциплина delivery | `delivery_check.py --require-ci` |
| **Oneshot на 60 файлов** (breakers §3.4) | `delivery_check.py --diff-base` — считает `merge-base..HEAD` |
| **Канон разъехался с кодом** | `okf_sync_gate.py --base` (OKF Приложение C) |
| Метрики harness не снимаются | `delivery_metrics.py` в step summary + гейт на блок в verify-report |
| Красный CI смержили кнопкой | Branch protection (§8.5) — required checks + review |

### 8.2. Новый гейт: `check_baseline_ratchet.sh` (снимки только вниз)

§7 требует «снимок вверх не переснимается никогда», но механически это не было
прибито ничем. Этот скрипт сравнивает `scripts/lint/*_baseline.txt` с их версией в
`BASE` и падает при **любом росте счётчика или новой записи**. Работает и с per-path
(`<count>:<path>`), и с global-count (одно число) снимками; секции
`[baseline]`/`[exemption]` в `file_length_baseline.txt` схлопываются в один map по пути.

```bash
#!/usr/bin/env bash
# Ратчет над самими снимками: baseline может только ТАЯТЬ.
#
# Локальные гейты сравнивают код со снимком, но никто не сравнивает СНИМОК с его
# прошлой версией. `--generate` на грязном дереве легализует свежие нарушения —
# гейт зелёный, правило мертво. Этот скрипт закрывает дыру: рост счётчика или
# новая запись в baseline = fail.
#
# Форматы: "<count>:<path>" (per-path) и "<N>" (global). Комментарии (#) и
# секции ([baseline]/[exemption]) игнорируются.
#
# Настройка (env):
#   BASE                    — ref для сравнения (дефолт: origin/main)
#   LINT_DIR                — каталог снимков (дефолт: scripts/lint)
#   STRICT=0                — soft (warning, exit 0); в CI ЗАПРЕЩЁН
#   ALLOW_BASELINE_GROWTH=1 — осознанный рост (например, массовое переименование
#                             файлов); обязан быть виден и объяснён в PR
set -euo pipefail

BASE=${BASE:-origin/main}
STRICT=${STRICT:-1}
LINT_DIR=${LINT_DIR:-scripts/lint}
ALLOW_BASELINE_GROWTH=${ALLOW_BASELINE_GROWTH:-0}

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  echo "baseline-ratchet: ref '$BASE' недоступен (shallow clone? нужен fetch-depth: 0)" >&2
  exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Снимок -> "path<TAB>count". Global-число получает ключ __global__.
normalize() {
  awk '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    /^[[:space:]]*\[/ { next }
    {
      i = index($0, ":")
      if (i > 0) { c = substr($0, 1, i - 1); p = substr($0, i + 1) }
      else       { c = $0;                    p = "__global__" }
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", c)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", p)
      if (c ~ /^[0-9]+$/) print p "\t" c
    }' "$1"
}

violations=0
checked=0

shopt -s nullglob
for cur in "$LINT_DIR"/*_baseline.txt; do
  name=$(basename "$cur")
  if ! git show "$BASE:$cur" >"$tmp/old.raw" 2>/dev/null; then
    echo "  skip (нет в $BASE, новый гейт): $name"
    continue
  fi
  checked=$((checked + 1))
  normalize "$tmp/old.raw" | sort >"$tmp/old.tsv"
  normalize "$cur" | sort >"$tmp/new.tsv"

  if ! awk -F'\t' -v f="$name" '
      NR == FNR { old[$1] = $2; next }
      {
        if (!($1 in old)) {
          printf "  %s: НОВАЯ запись %s (count %s) — свежее нарушение легализовано\n", f, $1, $2
          bad = 1
        } else if (($2 + 0) > (old[$1] + 0)) {
          printf "  %s: %s вырос %s -> %s\n", f, $1, old[$1], $2
          bad = 1
        }
      }
      END { exit bad ? 1 : 0 }' "$tmp/old.tsv" "$tmp/new.tsv"; then
    violations=$((violations + 1))
  fi
done

if [[ "$violations" -eq 0 ]]; then
  echo "baseline-ratchet: OK ($checked снимков сверено с $BASE)"
  exit 0
fi

if [[ "$ALLOW_BASELINE_GROWTH" == "1" ]]; then
  echo "baseline-ratchet: рост разрешён ALLOW_BASELINE_GROWTH=1 — объясни в PR" >&2
  exit 0
fi
if [[ "$STRICT" == "0" ]]; then
  echo "baseline-ratchet: WARNING (STRICT=0) — $violations снимков выросли" >&2
  exit 0
fi
echo "baseline-ratchet: FAIL — снимок переснят ВВЕРХ в $violations файл(ах)." >&2
echo "Починка: убрать нарушения в коде, затем --generate/--tighten; снимок только вниз (§7)." >&2
exit 1
```

Класть в `scripts/lint/check_baseline_ratchet.sh`, `chmod +x`. **В pre-commit не
добавляется** (нужен диффа против remote-ref) — только CI / pre-push.

### 8.3. Workflow (GitHub Actions)

`.github/workflows/quality.yml` — минимальный полный набор:

```yaml
name: quality

on:
  pull_request:
  push:
    branches: [main]

env:
  STRICT: "1"                 # soft-режим в CI запрещён (Delivery §10.4)
  LINT_PY_SRC: backend/features
  LINT_FE_DIR: frontend
  LINT_BE_DIR: backend
  LINT_COV_PKG: features

jobs:
  gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0      # нужен для BASE-диффа: diff-coverage и baseline-ratchet
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install backend deps
        run: |
          python -m venv backend/.venv
          backend/.venv/bin/pip install -r backend/requirements-dev.txt
          # if-блок, а не `test -f X && cmd`: под `bash -e` ложный test уронил бы шаг
          if [ -f backend/requirements.txt ]; then
            backend/.venv/bin/pip install -r backend/requirements.txt
          fi

      - name: Install frontend deps
        run: npm ci --prefix frontend

      - name: pre-commit (all files, STRICT=1)
        run: |
          pip install pre-commit
          pre-commit run --all-files --show-diff-on-failure

      - name: Gate coverage (все гейты подключены)
        run: bash scripts/lint/check_gate_coverage.sh

      - name: Baseline ratchet (снимки только вниз)
        env:
          BASE: origin/${{ github.base_ref || github.event.repository.default_branch }}
        run: bash scripts/lint/check_baseline_ratchet.sh

      - name: Diff coverage
        env:
          BASE: origin/${{ github.base_ref || github.event.repository.default_branch }}
          MIN_PCT: "70"
        run: bash scripts/lint/check_diff_coverage.sh

  delivery:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0      # breakers и метрики считаются по merge-base..HEAD
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Delivery phase gate + circuit breakers
        env:
          BASE: origin/${{ github.base_ref || github.event.repository.default_branch }}
        run: |
          if [ -f delivery/active/STATUS.md ]; then
            python scripts/delivery_check.py --require-ci --diff-base "$BASE"
          else
            echo "no active delivery — skip"
          fi

      - name: Canon sync gate (code <-> knowledge)
        env:
          BASE: origin/${{ github.base_ref || github.event.repository.default_branch }}
        run: |
          if [ -f scripts/okf_sync_gate.py ]; then
            python scripts/okf_sync_gate.py --base "$BASE"
          else
            echo "no OKF sync gate — skip"
          fi

      - name: Harness metrics (report only, never fails)
        env:
          BASE: origin/${{ github.base_ref || github.event.repository.default_branch }}
        run: |
          if [ -f scripts/delivery_metrics.py ]; then
            python scripts/delivery_metrics.py --base "$BASE" >> "$GITHUB_STEP_SUMMARY"
          fi

      - name: Smoke evals (product oracles)
        run: |
          if [ -f delivery/evals/smoke/run.sh ]; then
            bash delivery/evals/smoke/run.sh
          else
            echo "no smoke suite — Delivery §6 backlog"
          fi

      - name: OKF bundle validator
        run: |
          if [ -f scripts/okf_validate.py ] && [ -d knowledge ]; then
            python scripts/okf_validate.py knowledge/
          else
            echo "no OKF bundle — skip"
          fi
```

GitLab / другой раннер: те же шаги в `.gitlab-ci.yml` (`stage: quality`), важны только
две вещи — **полная история** (`GIT_DEPTH: 0`) и **`STRICT=1`** в переменных пайплайна.

### 8.4. Правила

1. **`STRICT=0` и `ALLOW_BASELINE_GROWTH=1` в CI-конфиге не хранятся.** Только как
   ручной one-off с объяснением в PR.
2. **Secrets-хук в CI не отключается** (§2.7) — даже soft-режимом.
3. **Required checks.** Джобы `gates` / `delivery` — обязательные в branch protection,
   иначе красный CI просто игнорируется при merge.
4. **CI не заменяет pre-commit.** Локальные хуки — быстрая петля (секунды);
   CI — истина для DoD. Убирать локальные хуки «раз есть CI» нельзя: агент потеряет
   немедленный сигнал и будет чинить форму пачками в конце.
5. **Нет CI вообще?** Компенсация — Delivery §10.4, правило 4 (чистый клон + вывод в
   `verify-report.md`) и `ci-oracles: weak` в STATUS. Это временный режим, не норма.

### 8.5. Где стоит гейт мержа (без зависимости от тарифа)

Красный CI ничего не останавливает, если изменения можно влить мимо него. Но
серверная защита ветки **платная и не везде есть**:

| Механизм | Доступность |
|---|---|
| Repository **rulesets** | GitHub **Team / Enterprise** |
| Классическая **branch protection** | Приватный репо — **Pro / Team+**; публичный — есть и на Free |
| GitHub **Actions** (сам workflow) | Есть на Free (для приватных — квота минут) |

Плановая матрица у хостингов меняется — проверь свой случай. Но проектировать
контур в расчёте на платный тариф нельзя, поэтому **база принуждения лежит в
репозитории**, а защита ветки — усиление сверху.

#### 8.5.1. База: три гейта, работающие на любом тарифе

**① `needs:` — красное не уезжает дальше.** Единственный полностью серверный и
бесплатный гейт: любая downstream-джоба (deploy, release, publish, миграции)
объявляет зависимость от джобы качества. Даже если красный коммит попал в
`main`, до прода он физически не доходит.

```yaml
  deploy:
    needs: [gates, delivery]     # ← гейт, не требующий тарифа
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps: [...]
```

**② `merge_guard.sh` — мерж через гейты, а не кнопкой.** Замена required status
checks: проверяет **слитое состояние** (то, что окажется в `main`) в отдельном
worktree и мержит только при зелёном. Именно это делают required checks в режиме
strict — здесь то же самое, но в репозитории.

**③ pre-push hook — цена обхода.** Тяжёлые проверки на `pre-push`:

```bash
pre-commit install --hook-type pre-push
```

```yaml
# .pre-commit-config.yaml — добавить рядом с остальными
  - repo: local
    hooks:
      - id: delivery-gate
        name: delivery phase gate + breakers (pre-push)
        entry: bash -c 'PY=$(command -v python3 || command -v python); "$PY" scripts/delivery_check.py --diff-base "$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo origin/main)"'
        language: system
        stages: [pre-push]
        pass_filenames: false
      - id: baseline-ratchet
        name: baseline only melts (pre-push)
        entry: bash scripts/lint/check_baseline_ratchet.sh
        language: system
        stages: [pre-push]
        pass_filenames: false
```

Обходится `git push --no-verify` — это осознанное действие, остающееся в reflog,
а не «случайно смержил красное».

**④ Красное на `main` не остаётся незамеченным.** Workflow открывает issue, если
защищённого мержа не было и красное всё же попало в основную ветку:

```yaml
# .github/workflows/main-guard.yml
name: main-guard
on:
  push:
    branches: [main]
permissions:
  contents: read
  issues: write
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {fetch-depth: 0}
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - id: gates
        continue-on-error: true
        run: |
          pip install pre-commit
          pre-commit run --all-files
      - if: steps.gates.outcome == 'failure'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh issue create \
            --title "RED on main: ${{ github.sha }}" \
            --body "Гейты на main красные. Слито мимо merge_guard.sh (CQG §8.5). Починить или откатить." \
            --label bug
      - if: steps.gates.outcome == 'failure'
        run: exit 1
```

#### 8.5.2. `scripts/merge_guard.sh`

```bash
#!/usr/bin/env bash
# Мерж через гейты, а не кнопкой. Замена required status checks там, где их нет
# (бесплатный тариф, приватный репо, не-GitHub хостинг).
#
# Отличие от pre-push: проверяется СЛИТОЕ состояние — то, что реально окажется в
# целевой ветке. Ветка может быть зелёной, а после слияния с ушедшим вперёд main
# — красной; required checks в режиме strict ловят именно это.
#
# Механика: отдельный worktree на целевой ветке -> merge --no-commit -> прогон
# гейтов там -> мерж в основном клоне только при зелёном. Рабочее дерево не
# трогается, конфликт не оставляет репо в merge-состоянии.
#
# Usage:
#   scripts/merge_guard.sh <source-branch> [target-branch]   # default target: main
#   DRY_RUN=1 scripts/merge_guard.sh feat/x                  # только проверить
set -euo pipefail

SOURCE=${1:?usage: merge_guard.sh <source-branch> [target-branch]}
TARGET=${2:-main}
DRY_RUN=${DRY_RUN:-0}

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

red=$(printf '\033[31m'); green=$(printf '\033[32m'); yellow=$(printf '\033[33m'); reset=$(printf '\033[0m')
die() { printf '%smerge_guard: %s%s\n' "$red" "$1" "$reset" >&2; exit 1; }

# Интерпретатор резолвим, а не хардкодим: на macOS и в свежих дистрибутивах
# бинаря `python` нет вовсе, есть только `python3` (или venv проекта).
PY=${PYTHON:-}
if [[ -z "$PY" ]]; then
  for cand in backend/.venv/bin/python .venv/bin/python python3 python; do
    if [[ -x "$cand" ]] || command -v "$cand" >/dev/null 2>&1; then PY=$cand; break; fi
  done
fi
[[ -n "$PY" ]] || die "не найден python (задай PYTHON=/path/to/python)"

git rev-parse --verify --quiet "$SOURCE" >/dev/null || die "нет ветки '$SOURCE'"
git rev-parse --verify --quiet "$TARGET" >/dev/null || die "нет ветки '$TARGET'"
[[ -z "$(git status --porcelain)" ]] || die "рабочее дерево грязное — закоммить или спрячь правки"

WT=$(mktemp -d)/merge-check
cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1 || true; }
trap cleanup EXIT

printf 'merge_guard: проверяю %s -> %s на слитом состоянии\n' "$SOURCE" "$TARGET"
git worktree add --quiet --detach "$WT" "$TARGET" || die "не смог создать worktree"

# Мерж в worktree КОММИТИТСЯ, а не остаётся в индексе (--no-commit).
# Иначе гейты, считающие дифф по коммитам (`merge-base..HEAD`: delivery_check
# --diff-base, okf_sync_gate --base), видят ПУСТОЙ дифф и пропускают всё:
# HEAD ещё равен $TARGET, а изменения лежат в индексе. Worktree одноразовый,
# коммит в нём никуда не уезжает.
if ! git -C "$WT" merge --no-ff --no-edit "$SOURCE" >/dev/null 2>&1; then
  git -C "$WT" merge --abort >/dev/null 2>&1 || true
  die "конфликт при слиянии $SOURCE в $TARGET — разреши его в ветке и повтори"
fi

# Гейты гоняются в слитом дереве. Каждый — только если он в проекте есть:
# стек разворачивается послойно, и отсутствующий слой не должен ронять мерж.
failed=()
run_gate() {
  local label=$1; shift
  printf '  → %s\n' "$label"
  if ( cd "$WT" && "$@" >/tmp/merge_guard_out 2>&1 ); then
    printf '    %sOK%s\n' "$green" "$reset"
  else
    printf '    %sFAIL%s\n' "$red" "$reset"; sed -n '1,15p' /tmp/merge_guard_out
    failed+=("$label")
  fi
}

command -v pre-commit >/dev/null 2>&1 && [[ -f .pre-commit-config.yaml ]] \
  && run_gate "pre-commit (all files)" pre-commit run --all-files
[[ -f scripts/lint/check_baseline_ratchet.sh ]] \
  && run_gate "baseline ratchet" env BASE="$TARGET" bash scripts/lint/check_baseline_ratchet.sh
[[ -f scripts/delivery_check.py ]] \
  && run_gate "delivery gate + breakers" "$PY" scripts/delivery_check.py --diff-base "$TARGET"
[[ -f scripts/okf_sync_gate.py ]] \
  && run_gate "canon sync" "$PY" scripts/okf_sync_gate.py --base "$TARGET"
[[ -f delivery/evals/smoke/run.sh ]] \
  && run_gate "smoke evals" bash delivery/evals/smoke/run.sh

if (( ${#failed[@]} )); then
  printf '\n%smerge_guard: МЕРЖ ЗАБЛОКИРОВАН — красные гейты: %s%s\n' "$red" "${failed[*]}" "$reset" >&2
  printf 'Починить в ветке %s и повторить. Не мержить кнопкой в обход.\n' "$SOURCE" >&2
  exit 1
fi

if [[ "$DRY_RUN" == "1" ]]; then
  printf '\n%smerge_guard: всё зелено (DRY_RUN=1, мерж не выполнен)%s\n' "$green" "$reset"
  exit 0
fi

git checkout --quiet "$TARGET"
git merge --no-ff --no-edit "$SOURCE"
printf '\n%smerge_guard: %s слит в %s после зелёных гейтов%s\n' "$green" "$SOURCE" "$TARGET" "$reset"
```

Класть в `scripts/merge_guard.sh`, `chmod +x`. Правило для агента и человека:
**мерж поставки — только этой командой** (или через PR с required checks, если
тариф позволяет). `git merge` руками — то же, что `commit -n`.

#### 8.5.3. Усиление: branch protection, если тариф позволяет

⚠ **Ручной шаг вне репозитория** — его не проверит ни `pre-commit`, ни workflow,
ни `stack_selftest`. Если тариф даёт защиту ветки, это строго лучше базы: гейт
переезжает на сервер, где его нельзя обойти локально.

| Пункт защиты ветки | Чем закрыт на бесплатном тарифе (§8.5.1) |
|---|---|
| [ ] `gates` / `delivery` как **required status checks** | `merge_guard.sh` — те же гейты на слитом состоянии + `main-guard` открывает issue на красное |
| [ ] `Require branches to be up to date` | `merge_guard.sh` проверяет **слитое** состояние по определению |
| [ ] **1 approving review** (= Builder ≠ Verifier) | `verifier:`/`Verifier:` + гейт `delivery_check`; независимость — отдельный проход другой моделью/человеком (Delivery §5.2) |
| [ ] **Block force pushes**, запрет удаления ветки | hook `protect-main` (Delivery A.11) — только машина агента; серверного аналога на Free **нет**, это остаётся дырой |
| [ ] `enforce_admins` | ничем; на Free владелец обходит всё по определению |
| [ ] Нет `bypass_pull_request_allowances` у бота | правило «мерж только `merge_guard.sh`» |

Две строки закрыть на бесплатном тарифе нечем — **force-push и админ-обход**.
Это честный остаток, а не решённая задача: пиши его в `STATUS.md`
(`ci-oracles: tooling`, см. Delivery §10.4) и не выдавай за `deployed`.

Готовая команда (GitHub, `gh` авторизован; подставь `OWNER/REPO`):

```bash
gh api -X PUT repos/OWNER/REPO/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  -F "required_status_checks[strict]=true" \
  -F "required_status_checks[contexts][]=gates" \
  -F "required_status_checks[contexts][]=delivery" \
  -F "enforce_admins=true" \
  -F "required_pull_request_reviews[required_approving_review_count]=1" \
  -F "restrictions=" \
  -F "allow_force_pushes=false" \
  -F "allow_deletions=false"
```

Проверка, что применилось:

```bash
gh api repos/OWNER/REPO/branches/main/protection \
  --jq '{checks: .required_status_checks.contexts, admins: .enforce_admins.enabled,
         reviews: .required_pull_request_reviews.required_approving_review_count,
         force: .allow_force_pushes.enabled}'
```

GitLab-эквивалент: Protected branches (`no one` для force-push) + Merge request
approvals ≥1 + `Pipelines must succeed` в Merge checks.

---

---

> ## ⬇ Ниже — BOOTSTRAP PAYLOAD (строки ~710–2029, 65% файла)
>
> Дословные исходники 6 скриптов и 8 конфигов. **В обычной работе не читай** —
> правила и пороги закончились выше (§1–§8). Читай отсюда только когда
> **разворачиваешь** гейты или правишь конкретный скрипт.
>
> | Что | Где |
> |---|---|
> | 6 скриптов `scripts/lint/**` | Приложение A |
> | pyproject / eslint / prettier / importlinter / pre-commit / requirements | Приложение B |
> | `check_baseline_ratchet.sh`, CI-workflow | **§8.2 / §8.3** (выше, внутри канона) |

---

# Приложение A — скрипты (`scripts/lint/`)

Полные исходники, дословно. Скрипты — `chmod +x`. `.sh` требуют `bash` (используют `BASH_SOURCE`, `[[ ]]`);
`check_ast_gate.py` — только stdlib Python 3.10+. Пути настраиваются env-переменными из §6.

### `scripts/lint/check_grep_gate.sh`

```bash
#!/usr/bin/env bash
# Grep-гейты для конвенций, у которых нет готового линтера.
#
# Механика — per-file baseline-ratchet: текущие (легаси) нарушения живут в снимке
# `<count>:<path>` и тают по мере правки файлов; файл ВНЕ снимка (в т.ч. любой новый)
# обязан иметь 0 нарушений. Ратчет только вниз: файл из baseline проходит при
# count <= снимок; --generate пере-снимает снимок вниз.
#
# Правила:
#   config-access      — getattr(config,...) / os.getenv / os.environ вне config/
#                        (опечатка в настройке должна падать, а не тихо дефолтиться)
#   di-indirection     — (pkg|session|ctx): Any + importlib.import_module("...") reach-back
#                        (DI вместо importlib-магии; Any в новых сигнатурах запрещён)
#   service-no-web     — импорт web-фреймворка (fastapi) в сервис-слое
#   no-grab-bag-module — файлы-помойки utils/misc/common/helpers.py без темы
#
# Настройка (env):
#   LINT_PY_SRC  — корневой каталог прод-Python для гейтов, от repo-root (дефолт: backend/features)
#
# Режимы:
#   check_grep_gate.sh --rule config-access             # проверка; exit 1 при регрессии
#   check_grep_gate.sh --rule config-access --generate  # пересобрать baseline правила
#   STRICT=0 check_grep_gate.sh --rule ...              # soft (warning, exit 0)

set -uo pipefail

STRICT=${STRICT:-1}
PY_SRC=${LINT_PY_SRC:-backend/features}
RULE=""
GENERATE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rule) RULE="${2:-}"; shift 2 ;;
    --generate) GENERATE=1; shift ;;
    *) shift ;;
  esac
done

# SCRIPT_DIR резолвим ДО cd в REPO_ROOT (BASH_SOURCE относителен cwd вызова).
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Токен-граница делается через (^|[^A-Za-z_.]) вместо \b: BSD grep (macOS) \b не держит.
# FILTER (опц.) — grep -E по путям: сузить правило до подмножества файлов по имени.
FILTER=""
case "$RULE" in
  config-access)
    PATTERN='getattr\([[:space:]]*config|(^|[^A-Za-z_.])os\.getenv|(^|[^A-Za-z_.])os\.environ'
    BASELINE="$SCRIPT_DIR/config_access_baseline.txt"
    LABEL='config-access: getattr(config,...) / os.getenv вне config/'
    HINT='Читай настройку через типизированный config.X (опечатку ловит type-checker). Дефолт — один раз в config/.'
    ;;
  di-indirection)
    PATTERN='(^|[^A-Za-z_])(pkg|session|ctx)[[:space:]]*:[[:space:]]*Any|import_module\([[:space:]]*["'"'"']'
    BASELINE="$SCRIPT_DIR/di_indirection_baseline.txt"
    LABEL='di-indirection: (pkg|session|ctx): Any / importlib reach-back'
    HINT='Новый код: явные зависимости через параметры/Protocol, конкретные типы вместо Any.'
    ;;
  service-no-web)
    PATTERN='^[[:space:]]*(from fastapi|import fastapi)'
    FILTER='/services/|service\.py$'
    BASELINE="$SCRIPT_DIR/service_no_web_baseline.txt"
    LABEL='service-no-web: сервис-слой не импортирует web-фреймворк'
    HINT='HTTP-примитивы (Request/Depends/HTTPException) — в роутере. Сервис принимает id-параметры и бросает доменные исключения, не HTTP.'
    ;;
  no-grab-bag-module)
    # Любая строка = нарушение: правило имени файла, не содержимого. Новый
    # utils/misc/common/helpers.py (без темы) имеет count>0 -> hard fail; легаси в
    # baseline и не растёт. `_helpers.py` (с подчёркиванием) FILTER не матчит — разрешён.
    PATTERN='^'
    FILTER='/(utils|misc|common|helpers)\.py$'
    BASELINE="$SCRIPT_DIR/no_grab_bag_baseline.txt"
    LABEL='no-grab-bag-module: файлы-помойки utils/misc/common/helpers.py без темы запрещены'
    HINT='Имя модуля описывает ответственность: <topic>.py / <topic>_helpers.py / _helpers.py рядом с фичей.'
    ;;
  *)
    echo "unknown --rule: '${RULE}' (config-access|di-indirection|service-no-web|no-grab-bag-module)" >&2
    exit 2
    ;;
esac

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT" || exit 1

red=$(printf '\033[31m'); yellow=$(printf '\033[33m'); green=$(printf '\033[32m'); reset=$(printf '\033[0m')

# Прод-.py под $PY_SRC, без тестов. git ls-files рекурсивен; пути — от repo-root.
list_targets() {
  local out
  out=$(git ls-files "$PY_SRC/" 2>/dev/null \
    | grep -E '\.py$' \
    | grep -vE '/tests/|/test_[^/]*\.py$')
  [[ -n "${FILTER:-}" ]] && out=$(printf '%s\n' "$out" | grep -E "$FILTER")
  printf '%s\n' "$out"
}

# Число строк-нарушений в файле (grep -c всегда печатает число; 0 при отсутствии).
count_hits() { grep -cE "$PATTERN" "$1" 2>/dev/null; }

# Снимок для точного пути (awk-сравнение точной строки — корректно с пробелами в пути).
baseline_lookup() {
  [[ -f "$BASELINE" ]] || return 0
  awk -v p="$1" '
    /^[[:space:]]*#/ { next }
    /^[0-9]+:/ {
      n=$0; sub(/:.*/, "", n)
      path=$0; sub(/^[0-9]+:/, "", path)
      if (path == p) { print n; exit }
    }
  ' "$BASELINE"
}

# --- --generate: пересобрать baseline --------------------------------------
if [[ "$GENERATE" == "1" ]]; then
  tmp=$(mktemp)
  while IFS= read -r f; do
    [[ -f "$f" ]] || continue
    hits=$(count_hits "$f")
    [[ "$hits" -gt 0 ]] && printf '%s:%s\n' "$hits" "$f" >>"$tmp"
  done < <(list_targets)
  {
    echo "# ${BASELINE##*/} — снимок grep-гейта. Генерируется --generate, НЕ руками."
    echo "# Правило: ${LABEL}"
    echo "# Формат: <count>:<path> (path от repo-root)."
    echo "# Ратчет вниз: файл проходит при count <= снимок; файл ВНЕ снимка (новый) — hard 0."
    LC_ALL=C sort -t: -k2 "$tmp"
  } >"$BASELINE"
  n=$(grep -c '^[0-9]' "$BASELINE" 2>/dev/null || echo 0)
  echo "${green}baseline пересобран${reset}: $BASELINE ($n файлов, правило ${RULE})"
  rm -f "$tmp"
  exit 0
fi

# --- проверка ---------------------------------------------------------------
violations=0
while IFS= read -r f; do
  [[ -f "$f" ]] || continue
  hits=$(count_hits "$f")
  [[ "$hits" -gt 0 ]] || continue
  snap=$(baseline_lookup "$f")
  allowed=${snap:-0}
  if [[ "$hits" -gt "$allowed" ]]; then
    violations=$((violations + 1))
    if [[ "$STRICT" == "1" ]]; then
      printf '%s  ✗  %s: %d нарушений (разрешено %d)%s\n' "$red" "$f" "$hits" "$allowed" "$reset"
    else
      printf '%s  ⚠  %s: %d нарушений (разрешено %d)%s\n' "$yellow" "$f" "$hits" "$allowed" "$reset"
    fi
  fi
done < <(list_targets)

if [[ "$violations" -gt 0 ]]; then
  hdr=$([[ "$STRICT" == "1" ]] && printf '%sERROR%s' "$red" "$reset" || printf '%sWARNING%s' "$yellow" "$reset")
  printf '\n%s: %d файл(ов) нарушают правило %s (вне baseline или сверх снимка).\n' "$hdr" "$violations" "$RULE"
  printf '%s\n' "$HINT"
  echo "Легаси-файл из baseline — ок до его чистки; новый код держим на нуле. Пересъём вниз: --generate."
  [[ "$STRICT" == "1" ]] && exit 1
fi
exit 0
```

### `scripts/lint/check_ast_gate.py`

```python
#!/usr/bin/env python3
"""AST-гейты для конвенций, которые grep не выразит.

Правила:
  silent-except  — «глухой» broad-except: `except Exception/BaseException/голый:`
                   без raise / логирования / record в теле хендлера (ошибка обязана
                   оставить след). Осознанный fail-soft помечается комментарием
                   `# silent-ok: <причина>` внутри хендлера — тогда сайт легален.
  inline-prompt  — LLM-промпт инлайном в .py: не-docstring строка >= 8 строк,
                   начинающаяся с персона-маркера («Ты — …», "You are …", …).
                   Порог по маркеру, не по длине: длинные SQL/Lua/regex легитимны.

Механика — per-file baseline-ratchet: легаси в снимке (`<count>:<path>`, путь от
repo-root); файл проходит при count <= снимок; файл вне снимка (любой новый) — hard 0.
Пересъём вниз: --generate.

Настройка (env):
  LINT_PY_SRC — корневой каталог прод-Python для гейтов, от repo-root (дефолт: backend/features)

Запуск (скрипт лежит в <repo-root>/scripts/lint/):
  python scripts/lint/check_ast_gate.py --rule silent-except
  python scripts/lint/check_ast_gate.py --rule silent-except --generate
  STRICT=0 …  — soft-режим (warning, exit 0), аварийно.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path

FEATURES = Path(os.environ.get("LINT_PY_SRC", "backend/features"))
SKIP_PARTS = ("/tests/", "/migrations/")
SILENT_OK_MARKER = "# silent-ok:"

_LOG_BASES = {"logger", "logging", "log", "warnings"}
_LOG_ATTR_PREFIXES = ("log", "warn", "exception", "error", "record", "capture", "notify")
_PROMPT_MARKERS = ("ты —", "ты -", "you are", "you classify", "act as", "роль:", "system:")
_PROMPT_MIN_LINES = 8


def _is_broad(handler: ast.ExceptHandler) -> bool:
    t = handler.type
    if t is None:
        return True
    if isinstance(t, ast.Name) and t.id in ("Exception", "BaseException"):
        return True
    if isinstance(t, ast.Tuple):
        return any(isinstance(e, ast.Name) and e.id in ("Exception", "BaseException") for e in t.elts)
    return False


def _handler_leaves_trace(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                base = func.value
                if isinstance(base, ast.Name) and base.id in _LOG_BASES:
                    return True
                if func.attr.startswith(_LOG_ATTR_PREFIXES):
                    return True
            if isinstance(func, ast.Name) and func.id.startswith(("log", "record", "capture", "notify")):
                return True
    return False


def _handler_has_silent_ok(handler: ast.ExceptHandler, src_lines: list[str]) -> bool:
    end = handler.body[-1].end_lineno if handler.body else handler.lineno
    for i in range(handler.lineno - 1, min(end, len(src_lines))):
        if SILENT_OK_MARKER in src_lines[i]:
            return True
    return False


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def find_silent_except(tree: ast.AST, src_lines: list[str]) -> list[int]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and _is_broad(node) and not _handler_leaves_trace(node) and not _handler_has_silent_ok(node, src_lines):
            out.append(node.lineno)
    return out


def find_inline_prompt(tree: ast.AST, src_lines: list[str]) -> list[int]:  # noqa: ARG001
    doc_ids = _docstring_ids(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
            if node.value.count("\n") + 1 < _PROMPT_MIN_LINES:
                continue
            head = node.value.strip().lower()
            if head.startswith(_PROMPT_MARKERS):
                out.append(node.lineno)
    return out


RULES = {
    "silent-except": {
        "find": find_silent_except,
        "baseline": "silent_except_baseline.txt",
        "label": "silent-except: broad-except без raise/лога",
        "hint": "Оставь след: logger.warning/exception с контекстом, либо пробрось. Осознанный fail-soft — пометь `# silent-ok: <причина>` в хендлере.",
    },
    "inline-prompt": {
        "find": find_inline_prompt,
        "baseline": "inline_prompt_baseline.txt",
        "label": "inline-prompt: LLM-промпт инлайном в .py",
        "hint": "Промпт — в отдельный <name>.md + lazy-load, не строкой в коде.",
    },
}


def iter_target_files(repo_root: Path):
    for path in sorted((repo_root / FEATURES).rglob("*.py")):
        rel = path.as_posix()
        if any(part in rel for part in SKIP_PARTS):
            continue
        if path.name.startswith("test_") or path.name == "conftest.py":
            continue
        yield path


def repo_rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def load_baseline(baseline_path: Path) -> dict[str, int]:
    snap: dict[str, int] = {}
    if not baseline_path.is_file():
        return snap
    for line in baseline_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or ":" not in line:
            continue
        count, _, p = line.partition(":")
        if count.isdigit():
            snap[p] = int(count)
    return snap


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rule", required=True, choices=sorted(RULES))
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()

    strict = os.environ.get("STRICT", "1") == "1"
    rule = RULES[args.rule]

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent  # <repo-root>/scripts/lint/ -> repo-root
    baseline_path = script_dir / rule["baseline"]

    counts: dict[str, int] = {}
    for path in iter_target_files(repo_root):
        try:
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        hits = rule["find"](tree, src.splitlines())
        if hits:
            counts[repo_rel(path, repo_root)] = len(hits)

    if args.generate:
        lines = [
            f"# {rule['baseline']} — снимок AST-гейта. Генерируется --generate, НЕ руками.",
            f"# Правило: {rule['label']}",
            "# Формат: <count>:<path> (path от repo-root). Ратчет вниз: файл проходит при count <= снимок;",
            "# файл ВНЕ снимка (новый) — hard 0.",
        ]
        lines += [f"{c}:{p}" for p, c in sorted(counts.items())]
        baseline_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"baseline пересобран: {baseline_path.name} ({len(counts)} файлов, {sum(counts.values())} сайтов)")
        return 0

    snap = load_baseline(baseline_path)
    violations = []
    for p, c in sorted(counts.items()):
        allowed = snap.get(p, 0)
        if c > allowed:
            violations.append((p, c, allowed))

    if violations:
        mark = "✗" if strict else "⚠"
        for p, c, allowed in violations:
            print(f"  {mark}  {p}: {c} нарушений (разрешено {allowed})")
        print(f"\n{'ERROR' if strict else 'WARNING'}: {len(violations)} файл(ов) нарушают правило {args.rule}.")
        print(rule["hint"])
        print("Легаси из baseline — ок до чистки; новый код держим на нуле. Пересъём вниз: --generate.")
        return 1 if strict else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `scripts/lint/check_file_length.sh`

```bash
#!/usr/bin/env bash
# Длина файлов кода: prod <= 500 / tests <= 1000 строк, с baseline-ratchet.
#
# Одномоментный сплит всех god-файлов невозможен, поэтому вводится снимок текущих
# превышений (file_length_baseline.txt), который ТАЕТ по мере сплитов. Файл из
# baseline проходит при size <= снимок+HEADROOM; новый / вне baseline — hard 500/1000.
# Exemption-секция (файлы без шва для сплита) не тает.
#
#   Тип файла                 | Hard limit (вне baseline)
#   Production .py/.ts/.tsx    |    500
#   Tests (*/tests/*, *.test)  |   1000
#   (миграции / node_modules — без лимита; настрой is_excluded под себя)
#
# Настройка (env): MAX_LINES_PROD, MAX_LINES_TESTS, BASELINE_HEADROOM, EXEMPTION_HEADROOM.
#
# Режимы:
#   check_file_length.sh            # проверка; exit 1 при нарушении
#   check_file_length.sh --generate # пересобрать baseline из текущего дерева
#   check_file_length.sh --tighten  # опустить снимки ужавшихся baseline-файлов
#   STRICT=0 check_file_length.sh   # soft (warning, exit 0) — аварийно, виден в PR

MAX_LINES_PROD=${MAX_LINES_PROD:-500}
MAX_LINES_TESTS=${MAX_LINES_TESTS:-1000}
# Headroom к снимку baseline: точечные правки god-файла не блокируются до его сплита.
# Exemption получает больше (швов нет — рост правдоподобнее).
BASELINE_HEADROOM=${BASELINE_HEADROOM:-30}
EXEMPTION_HEADROOM=${EXEMPTION_HEADROOM:-50}
STRICT=${STRICT:-1}

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# SCRIPT_DIR резолвим ДО cd в REPO_ROOT (BASH_SOURCE относителен cwd вызова).
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BASELINE="$SCRIPT_DIR/file_length_baseline.txt"

cd "$REPO_ROOT" || exit 1

red=$(printf '\033[31m')
yellow=$(printf '\033[33m')
green=$(printf '\033[32m')
reset=$(printf '\033[0m')

# --- helpers ---------------------------------------------------------------

# Пропустить путь (генерируемое / vendored). Настрой под свой проект.
is_excluded() {
  case "$1" in
    */migrations/*) return 0 ;;
    */node_modules/*) return 0 ;;
  esac
  return 1
}

# Тестовый файл? (feature-local tests/ тоже считаются.)
is_test() {
  case "$1" in
    *.test.ts | *.test.tsx | */tests/*) return 0 ;;
  esac
  return 1
}

# Файлы под exemption (нет шва для сплита — держим сознательно, лимит = снимок+EXEMPTION_HEADROOM).
# По умолчанию пусто; впиши сюда свои случаи через case-паттерны.
is_exempt_path() {
  case "$1" in
    __never_matches__) return 0 ;;
  esac
  return 1
}

base_limit_for() {
  if is_test "$1"; then echo "$MAX_LINES_TESTS"; else echo "$MAX_LINES_PROD"; fi
}

# Снимок baseline для точного пути (или пусто). Печатает "<snapshot>:<section>".
# awk-сравнение точной строки пути -> корректно с пробелами в пути.
baseline_lookup() {
  [[ -f "$BASELINE" ]] || return 0
  awk -v p="$1" '
    /^[[:space:]]*#/ { next }
    /^\[baseline\]/  { sect="baseline"; next }
    /^\[exemption\]/ { sect="exemption"; next }
    /^[0-9]+:/ {
      n=$0; sub(/:.*/, "", n)
      path=$0; sub(/^[0-9]+:/, "", path)
      if (path == p) { print n ":" sect; exit }
    }
  ' "$BASELINE"
}

collect_files() {
  if [[ $# -gt 0 ]]; then
    printf '%s\n' "$@"
  else
    git ls-files '*.py' '*.ts' '*.tsx' 2>/dev/null
  fi
}

# --- --generate: пересобрать baseline из текущего дерева ---------------------

if [[ "${1:-}" == "--generate" ]]; then
  tmp_base=$(mktemp)
  tmp_exempt=$(mktemp)
  while IFS= read -r f; do
    is_excluded "$f" && continue
    [[ -f "$f" ]] || continue
    limit=$(base_limit_for "$f")
    lines=$(wc -l <"$f" | tr -d ' ')
    [[ "$lines" -gt "$limit" ]] || continue
    if is_exempt_path "$f"; then
      printf '%s:%s\n' "$lines" "$f" >>"$tmp_exempt"
    else
      printf '%s:%s\n' "$lines" "$f" >>"$tmp_base"
    fi
  done < <(git ls-files '*.py' '*.ts' '*.tsx' 2>/dev/null)

  {
    echo "# file_length_baseline.txt — снимок file-length гейта. Генерируется --generate, НЕ руками."
    echo "# Формат: <lines>:<path> (path в нотации git ls-files от repo-root)."
    echo "# [baseline] тает по мере сплитов (--tighten опускает снимки); файл проходит при size <= снимок+${BASELINE_HEADROOM}."
    echo "# [exemption] не тает (швов нет); лимит = снимок+${EXEMPTION_HEADROOM}, рост сверх — пере-ревью в PR."
    echo "# Вне обоих списков (в т.ч. любой новый файл) — hard ${MAX_LINES_PROD}/${MAX_LINES_TESTS}."
    echo "[baseline]"
    LC_ALL=C sort -t: -k2 "$tmp_base"
    echo "[exemption]"
    LC_ALL=C sort -t: -k2 "$tmp_exempt"
  } >"$BASELINE"

  rm -f "$tmp_base" "$tmp_exempt"
  n_base=$(grep -c '^[0-9]' "$BASELINE")
  echo "${green}baseline пересобран${reset}: $BASELINE ($n_base записей)"
  exit 0
fi

# --- проверка (и --tighten как её вариант) ----------------------------------

TIGHTEN=0
if [[ "${1:-}" == "--tighten" ]]; then
  TIGHTEN=1
  shift
  tmp_tight=$(mktemp)
fi

violations=0
tightened=0

check_file() {
  local file=$1
  local limit lines snap sect info allowed newsnap

  is_excluded "$file" && return
  [[ -f "$file" ]] || return

  limit=$(base_limit_for "$file")
  lines=$(wc -l <"$file" | tr -d ' ')

  info=$(baseline_lookup "$file")
  if [[ -n "$info" ]]; then
    snap=${info%%:*}
    sect=${info##*:}
    if [[ "$sect" == "exemption" ]]; then
      allowed=$((snap + EXEMPTION_HEADROOM))
    else
      allowed=$((snap + BASELINE_HEADROOM))
    fi
    # --tighten перезаписывает всю [baseline]-секцию из $tmp_tight, поэтому КАЖДАЯ
    # baseline-запись обязана сюда попасть — иначе неизменённые файлы молча выпадут.
    # Ратчет только ВНИЗ: снимок = min(строки, снимок); ужался <= лимита -> выпадает.
    if [[ "$TIGHTEN" == "1" && "$sect" == "baseline" ]]; then
      newsnap=$snap
      [[ "$lines" -lt "$snap" ]] && newsnap=$lines
      if [[ "$newsnap" -le "$limit" ]]; then
        tightened=$((tightened + 1))  # выпал из baseline (не пишем в tmp)
      else
        printf '%s:%s\n' "$newsnap" "$file" >>"$tmp_tight"
        [[ "$newsnap" -lt "$snap" ]] && tightened=$((tightened + 1))
      fi
      return
    fi
  else
    allowed=$limit
  fi

  if [[ "$lines" -gt "$allowed" ]]; then
    violations=$((violations + 1))
    if [[ "$STRICT" == "1" ]]; then
      printf '%s  ✗  %s: %d lines (> %d)%s\n' "$red" "$file" "$lines" "$allowed" "$reset"
    else
      printf '%s  ⚠  %s: %d lines (> %d)%s\n' "$yellow" "$file" "$lines" "$allowed" "$reset"
    fi
  fi
}

# --tighten перезаписывает всю [baseline]-секцию -> ОБЯЗАН видеть всё дерево, иначе
# усечёт baseline до переданных файлов. Обычная проверка уважает список файлов из хука.
while IFS= read -r f; do
  [[ -n "$f" ]] && check_file "$f"
done < <(if [[ "$TIGHTEN" == "1" ]]; then collect_files; else collect_files "$@"; fi)

if [[ "$TIGHTEN" == "1" ]]; then
  # Перезаписать [baseline]-секцию ужатыми снимками, [exemption] оставить как есть.
  # Шапку и exemption-секцию ЧИТАЕМ ДО редиректа: '>"$BASELINE"' усекает файл до
  # выполнения блока, поэтому чтение из него внутри {} вернуло бы пусто.
  header=$(grep '^#' "$BASELINE")
  exempt_section=$(awk '/^\[exemption\]/{p=1} p' "$BASELINE")
  {
    printf '%s\n' "$header"
    echo "[baseline]"
    LC_ALL=C sort -t: -k2 "$tmp_tight" 2>/dev/null
    [[ -n "$exempt_section" ]] && echo "$exempt_section"
  } >"$BASELINE"
  rm -f "$tmp_tight"
  echo "${green}--tighten: обновлено снимков/выпало из baseline: $tightened${reset}"
  exit 0
fi

if [[ "$violations" -gt 0 ]]; then
  hdr=$([[ "$STRICT" == "1" ]] && printf '%sERROR%s' "$red" "$reset" || printf '%sWARNING%s' "$yellow" "$reset")
  printf '\n%s: %d файл(ов) превышают лимит длины (вне baseline/exemption).\n' "$hdr" "$violations"
  echo "Лимиты: prod ${MAX_LINES_PROD} / tests ${MAX_LINES_TESTS}. Новый код держим под лимитом;"
  echo "баг-фикс god-файла из baseline — ок до его сплита."
  [[ "$STRICT" == "1" ]] && exit 1
fi

exit 0
```

### `scripts/lint/check_jscpd_gate.sh`

```bash
#!/usr/bin/env bash
# DRY / copy-paste гейт (jscpd). Глобальный clone-count ратчет.
#
# jscpd считает clone-пары в прод-Python; снимок хранится в jscpd_baseline.txt; гейт
# падает, если число дублей ВЫРОСЛО (добавили копипаст). После консолидации дублей
# число падает — пере-снять baseline вниз через --generate. Порог jscpd: min-tokens 50.
#
# Бинарь jscpd ищется в node_modules фронта, затем в PATH. Нет бинаря — гейт не
# блокирует, только предупреждает (свежий clone без npm ci).
#
# Настройка (env):
#   LINT_PY_SRC  — каталог прод-Python для анализа, от repo-root (дефолт: backend/features)
#   LINT_FE_DIR  — фронт-каталог с node_modules (дефолт: frontend)
#
# Режимы:
#   check_jscpd_gate.sh             # проверка; exit 1 при росте дублей
#   check_jscpd_gate.sh --generate  # пере-снять baseline (текущее число дублей)
#   STRICT=0 check_jscpd_gate.sh    # soft (warning, exit 0)

set -uo pipefail

STRICT=${STRICT:-1}
PY_SRC=${LINT_PY_SRC:-backend/features}
FE_DIR=${LINT_FE_DIR:-frontend}
GENERATE=0
[[ "${1:-}" == "--generate" ]] && GENERATE=1

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BASELINE="$SCRIPT_DIR/jscpd_baseline.txt"

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT" || exit 1

red=$(printf '\033[31m'); yellow=$(printf '\033[33m'); green=$(printf '\033[32m'); reset=$(printf '\033[0m')

if [[ -x "$FE_DIR/node_modules/.bin/jscpd" ]]; then
  JSCPD="$FE_DIR/node_modules/.bin/jscpd"
elif command -v jscpd >/dev/null 2>&1; then
  JSCPD="jscpd"
else
  printf '%s⚠ jscpd не найден — DRY-гейт пропущен. Установка: npm i -D jscpd%s\n' "$yellow" "$reset"
  exit 0
fi

# Число clone-пар в $PY_SRC (python, min-tokens 50, без tests).
current_clones() {
  "$JSCPD" "$PY_SRC" -f python -k 50 -i "**/tests/**,**/test_*.py" -r console 2>/dev/null \
    | grep -oE 'Found [0-9]+ clones' | grep -oE '[0-9]+' | head -1
}

count=$(current_clones)
count=${count:-0}

if [[ "$GENERATE" == "1" ]]; then
  {
    echo "# jscpd_baseline.txt — снимок DRY-гейта. Генерируется --generate, НЕ руками."
    echo "# Одно число = кол-во clone-пар в прод-Python (python, min-tokens 50, без tests)."
    echo "# Гейт падает при РОСТЕ; после консолидации дублей пере-снять вниз (--generate)."
    echo "$count"
  } >"$BASELINE"
  echo "${green}jscpd baseline пересобран${reset}: $count clone-пар"
  exit 0
fi

baseline=$(grep -m1 -oE '^[0-9]+' "$BASELINE" 2>/dev/null)
baseline=${baseline:-0}

if [[ "$count" -gt "$baseline" ]]; then
  if [[ "$STRICT" == "1" ]]; then
    printf '%sERROR%s: дубли выросли: %d clone-пар (baseline %d).\n' "$red" "$reset" "$count" "$baseline"
    echo "Не копируй код: вынеси общий helper/константу (rule-of-three для логики)."
    echo "Если рост оправдан (напр. split-facade) — пере-снять снимок: --generate."
    exit 1
  fi
  printf '%sWARNING%s: дубли выросли: %d (baseline %d).\n' "$yellow" "$reset" "$count" "$baseline"
fi
exit 0
```

### `scripts/lint/check_eslint_warnings.sh`

```bash
#!/usr/bin/env bash
# ESLint warning-count ратчет (фронт). Глобальный счётчик предупреждений.
#
# Per-file eslint-хук блокирует только errors (без --max-warnings=0), поэтому warnings
# росли бы молча. Здесь: полный прогон eslint по фронт-src, снимок суммы warnings в
# eslint_warnings_baseline.txt; гейт падает, если счётчик ВЫРОС. Правишь файл с
# warnings -> счисти часть и пере-сними вниз (--generate). Только вниз.
#
# Бинарь eslint ищется в node_modules фронта, затем в PATH. Нет бинаря — гейт не
# блокирует, только предупреждает (свежий clone без npm ci). Нет самого каталога
# фронта — тоже skip: backend-only проект не должен падать на фронт-гейте.
#
# Настройка (env): LINT_FE_DIR — фронт-каталог с package.json/src (дефолт: frontend)
#
# Режимы:
#   check_eslint_warnings.sh             # проверка; exit 1 при росте
#   check_eslint_warnings.sh --generate  # пере-снять baseline (текущее число warnings)
#   STRICT=0 check_eslint_warnings.sh    # soft (warning, exit 0)

set -uo pipefail

STRICT=${STRICT:-1}
FE_DIR=${LINT_FE_DIR:-frontend}
GENERATE=0
[[ "${1:-}" == "--generate" ]] && GENERATE=1

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BASELINE="$SCRIPT_DIR/eslint_warnings_baseline.txt"

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

red=$(printf '\033[31m'); yellow=$(printf '\033[33m'); green=$(printf '\033[32m'); reset=$(printf '\033[0m')

# Каталога фронта нет (backend-only проект / другой layout) — не наша забота, skip.
# Без этой проверки `cd` печатал сырую ошибку шелла и ронял коммит на exit 1.
if [[ ! -d "$REPO_ROOT/$FE_DIR" ]]; then
  printf '%s⚠ нет каталога фронта (%s) — eslint warning-ратчет пропущен. Настройка: LINT_FE_DIR%s\n' \
    "$yellow" "$FE_DIR" "$reset"
  exit 0
fi
cd "$REPO_ROOT/$FE_DIR" || exit 1

if [[ -x "node_modules/.bin/eslint" ]]; then
  ESLINT="node_modules/.bin/eslint"
elif command -v eslint >/dev/null 2>&1; then
  ESLINT="eslint"
else
  printf '%s⚠ eslint не найден — warning-ратчет пропущен. Установка: npm ci%s\n' "$yellow" "$reset"
  exit 0
fi

# Полный прогон по src: сумма warnings из JSON-репорта. Errors здесь не считаем —
# их блокирует per-file eslint-хук на каждом коммите.
current_warnings() {
  "$ESLINT" src --format json 2>/dev/null \
    | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{try{const r=JSON.parse(d);console.log(r.reduce((a,f)=>a+f.warningCount,0));}catch{console.log("");}})'
}

count=$(current_warnings)
if [[ -z "$count" ]]; then
  printf '%sERROR%s: не удалось посчитать eslint warnings (пустой/битый JSON-вывод eslint).\n' "$red" "$reset"
  exit 1
fi

if [[ "$GENERATE" == "1" ]]; then
  {
    echo "# eslint_warnings_baseline.txt — снимок warning-count ратчета. Генерируется --generate, НЕ руками."
    echo "# Одно число = сумма ESLint warnings полного прогона фронт-src (errors гейтит сам eslint-хук)."
    echo "# Гейт падает при РОСТЕ; счистил предупреждения — пере-снять вниз (--generate). Вверх не переснимается."
    echo "$count"
  } >"$BASELINE"
  echo "${green}eslint warnings baseline пересобран${reset}: $count"
  exit 0
fi

baseline=$(grep -m1 -oE '^[0-9]+' "$BASELINE" 2>/dev/null)
if [[ -z "$baseline" ]]; then
  printf '%sERROR%s: baseline не найден (%s) — сними снимок: --generate\n' "$red" "$reset" "$BASELINE"
  exit 1
fi

if [[ "$count" -gt "$baseline" ]]; then
  if [[ "$STRICT" == "1" ]]; then
    printf '%sERROR%s: ESLint warnings выросли: %d (baseline %d).\n' "$red" "$reset" "$count" "$baseline"
    echo "Новые предупреждения не проходят: почини правило (частые — max-lines-per-function, react-hooks/exhaustive-deps)."
    echo "Рост оправдан (редко) — пере-снять снимок: --generate."
    exit 1
  fi
  printf '%sWARNING%s: ESLint warnings выросли: %d (baseline %d).\n' "$yellow" "$reset" "$count" "$baseline"
elif [[ "$count" -lt "$baseline" ]]; then
  echo "${yellow}warnings уменьшились ($count < baseline $baseline) — ужми снимок: --generate${reset}"
fi
exit 0
```

### `scripts/lint/check_diff_coverage.sh`

```bash
#!/usr/bin/env bash
# coverage-on-diff — DoD-отчёт покрытия ИЗМЕНЁННЫХ prod-файлов.
#
# НЕ pre-commit хук (полный сьют = минуты): запускается руками перед push / в DoD.
# Гоняет pytest c coverage-json, затем печатает покрытие каждого изменённого
# prod-файла (diff против BASE, дефолт origin/main) и сравнивает с целью (70%).
#
# База диффа:
#   • дифф до BASE пуст, но есть НЕзакоммиченные правки -> ЖЁЛТЫЙ ворнинг (рабочее
#     дерево скрипт не меряет — закоммить и повторить); STRICT=1 -> exit 1;
#   • дифф пуст и дерево чистое (только что запушено) -> авто-fallback на origin/main@{1}
#     (прошлая позиция = последний пуш); fallback отключается, если BASE задан снаружи.
#
# Настройка (env):
#   LINT_BE_DIR   — каталог backend с venv/pyproject/pytest (дефолт: backend)
#   LINT_COV_PKG  — пакет для --cov (дефолт: features)
#   LINT_PY_SRC   — прод-Python корень от repo-root (дефолт: $BE_DIR/$COV_PKG)
#   LINT_VENV     — путь к venv относительно backend (дефолт: .venv)
#
# Режимы:
#   check_diff_coverage.sh              # отчёт (exit 0 всегда)
#   STRICT=1 check_diff_coverage.sh     # exit 1: файл < MIN_PCT / грязное дерево
#   BASE=<ref> …                        # база диффа (дефолт origin/main)
#   SKIP_TESTS=1 …                      # переиспользовать существующий coverage.json

set -uo pipefail

STRICT=${STRICT:-0}
BASE_WAS_SET=${BASE+set}
BASE=${BASE:-origin/main}
MIN_PCT=${MIN_PCT:-70}
SKIP_TESTS=${SKIP_TESTS:-0}

BE_DIR=${LINT_BE_DIR:-backend}
COV_PKG=${LINT_COV_PKG:-features}
PY_SRC=${LINT_PY_SRC:-$BE_DIR/$COV_PKG}
VENV=${LINT_VENV:-.venv}

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT/$BE_DIR" || exit 1

red=$(printf '\033[31m'); yellow=$(printf '\033[33m'); green=$(printf '\033[32m'); reset=$(printf '\033[0m')

# git diff — от repo-root (git -C): pathspec от корня не матчится из cwd backend/.
list_changed() { # $1 = base-реф; закоммиченный дифф prod-файлов (без тестов)
  git -C "$REPO_ROOT" diff --name-only "$1"...HEAD -- "$PY_SRC/*.py" 2>/dev/null \
    | grep -vE '/tests/|/test_[^/]*\.py$' \
    | sed "s#^$BE_DIR/##"
}

# Незакоммиченные правки — их дифф-списком не увидеть, а сьют их исполняет:
# источник ложного зелёного.
dirty=$(git -C "$REPO_ROOT" status --porcelain -- "$PY_SRC/*.py" 2>/dev/null \
  | cut -c4- | grep -vE '/tests/|/test_[^/]*\.py$' || true)

changed=$(list_changed "$BASE")

if [[ -z "$changed" && -n "$dirty" ]]; then
  echo "${yellow}diff-coverage: коммитов относительно $BASE нет, но есть НЕзакоммиченные правки —${reset}"
  echo "${yellow}рабочее дерево скрипт не меряет. Закоммить и повторить. Незакоммичено:${reset}"
  echo "$dirty" | sed 's/^/  • /'
  [[ "$STRICT" == "1" ]] && exit 1
  exit 0
fi

# Запушено (origin/main == HEAD) и дерево чистое -> меряем последний пуш через reflog
# remote-tracking ветки. Только для дефолтного BASE: явный BASE=<ref> уважаем как есть.
if [[ -z "$changed" && -z "$BASE_WAS_SET" ]] \
  && git -C "$REPO_ROOT" rev-parse --verify -q 'origin/main@{1}' >/dev/null 2>&1; then
  changed=$(list_changed 'origin/main@{1}')
  if [[ -n "$changed" ]]; then
    prev_short=$(git -C "$REPO_ROOT" rev-parse --short 'origin/main@{1}')
    BASE="origin/main@{1} = $prev_short"
    echo "${yellow}diff-coverage: origin/main == HEAD (всё запушено) — меряю последний пуш: BASE=$BASE${reset}"
  fi
fi

if [[ -z "$changed" ]]; then
  echo "${green}diff-coverage: изменённых prod-файлов нет (BASE=$BASE)${reset}"
  exit 0
fi

if [[ -n "$dirty" ]]; then
  echo "${yellow}внимание: есть незакоммиченные правки — сьют их исполняет, но в отчёте ниже их нет:${reset}"
  echo "$dirty" | sed 's/^/  • /'
fi

if [[ "$SKIP_TESTS" != "1" ]]; then
  echo "diff-coverage: гоняю сьют с coverage (может занять минуты)…"
  "$VENV/bin/python" -m pytest -q --cov="$COV_PKG" --cov-report=json:coverage.json >/dev/null 2>&1
fi
if [[ ! -f coverage.json ]]; then
  echo "${red}coverage.json не найден (сьют не отработал?)${reset}"
  exit 1
fi

# changed — через env: пайп в `python - <<heredoc` не работает (heredoc занимает stdin).
CHANGED="$changed" "$VENV/bin/python" - "$MIN_PCT" "$STRICT" <<'PY'
import json
import os
import sys

min_pct = float(sys.argv[1])
strict = sys.argv[2] == "1"
changed = [line.strip() for line in os.environ.get("CHANGED", "").splitlines() if line.strip()]
files = json.load(open("coverage.json"))["files"]

fails = 0
print(f"{'файл':70s} {'stmts':>6s} {'miss':>5s} {'cov%':>6s}")
for path in changed:
    info = files.get(path)
    if info is None:
        print(f"{path:70s} {'—':>6s} {'—':>5s} {'0.0':>6s}  <- не исполнялся тестами вовсе")
        fails += 1
        continue
    s = info["summary"]
    pct = s["percent_covered"]
    mark = "" if pct >= min_pct else f"  <- ниже цели {min_pct:.0f}%"
    if pct < min_pct:
        fails += 1
    print(f"{path:70s} {s['num_statements']:6d} {s['missing_lines']:5d} {pct:6.1f}{mark}")

if fails:
    print(f"\n{fails} изменённых файл(ов) ниже цели {min_pct:.0f}%.")
    sys.exit(1 if strict else 0)
PY
rc=$?
[[ "$STRICT" == "1" ]] && exit "$rc"
exit 0
```

### `scripts/lint/check_gate_coverage.sh`

```bash
#!/usr/bin/env bash
# МЕТА-ГЕЙТ: каждый гейт обязан быть ПОДКЛЮЧЁН, а не просто существовать.
#
# Зачем. `pre-commit run --all-files` доказывает исправность хуков, ПЕРЕЧИСЛЕННЫХ
# в конфиге, и молчит о недостающих: невключённый гейт неотличим от проходящего.
# Реальный случай (2026-07-27): скрипт jscpd был извлечён и даже адаптирован под
# язык проекта, но не вписан в .pre-commit-config.yaml — приёмка показала 7/7
# зелёных, потому что проверяла «работает ли подключённое», а не «подключено ли
# всё требуемое». Этот гейт закрывает класс ошибки, а не тот один случай.
#
# Что проверяет (в обе стороны):
#   1. Каждый скрипт в $LINT_DIR упомянут хотя бы в одном месте принуждения
#      (pre-commit / CI-workflow / merge_guard / Makefile / justfile).
#   2. Каждый путь `scripts/...`, упомянутый в конфигах, существует на диске
#      (ловит опечатку и удалённый скрипт — «хук есть, гейта нет»).
#
# Осознанно неподключённые перечисляются в is_exempt() С ПРИЧИНОЙ. Отсутствие
# в конфиге должно быть решением в коде, а не пробелом.
#
# Настройка (env): LINT_DIR (дефолт scripts/lint), STRICT=0 — soft.
#
# Режимы:
#   check_gate_coverage.sh          # проверка; exit 1 при непокрытом гейте
#   STRICT=0 check_gate_coverage.sh # soft (warning, exit 0)

set -uo pipefail

STRICT=${STRICT:-1}
LINT_DIR=${LINT_DIR:-scripts/lint}

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT" || exit 1

red=$(printf '\033[31m'); yellow=$(printf '\033[33m'); green=$(printf '\033[32m'); reset=$(printf '\033[0m')

# Осознанно НЕ подключённые — причина ОБЯЗАТЕЛЬНА и печатается на каждом прогоне.
# Не список имён в комментарии: причина — это состояние проекта, которое меняется
# («тестов нет», «нет TS»), и когда оно изменится, устаревшее исключение должно
# быть видно глазами на каждом прогоне, а не лежать в коде.
# `case`, а не `declare -A`: на macOS системный bash 3.2 без ассоциативных массивов.
#
# Исключение здесь часто означает `*-oracles: weak` в delivery/active/STATUS.md
# (Delivery §3.1) — не забудь отметить там же.
#
# Этот файл в исключения НЕ вносится: мета-гейт, который сам никем не вызывается,
# — ровно та дыра, от которой он защищает, на уровень выше.
not_wired_reason() {
  case "$1" in
    check_diff_coverage.sh)
      echo "ручной DoD-шаг (§3.5): полный сьют — минуты; в CI подключён отдельным шагом" ;;
    *) return 1 ;;
  esac
}

# nullglob убирает нераскрывшиеся ГЛОБЫ, но не литеральные имена: каждый
# фиксированный путь проверяется через [[ -f ]], иначе список «мест принуждения»
# никогда не бывает пустым и проверка ниже становится мёртвым кодом.
shopt -s nullglob
CONFIGS=()
for fixed in .pre-commit-config.yaml .gitlab-ci.yml scripts/merge_guard.sh Makefile justfile; do
  [[ -f "$fixed" ]] && CONFIGS+=("$fixed")
done
CONFIGS+=(.github/workflows/*.yml .github/workflows/*.yaml)

if (( ${#CONFIGS[@]} == 0 )); then
  printf '%sERROR%s: не найдено ни одного места принуждения (.pre-commit-config.yaml / CI).\n' "$red" "$reset" >&2
  printf 'Гейты без подключения не работают — см. §5 шаги 5 и 8.\n' >&2
  exit 1
fi

# git ls-files, а не файловый glob: считаем только ОТСЛЕЖИВАЕМЫЕ файлы — так же,
# как остальные гейты CQG (§4). Локальный черновик в рабочем дереве гейтом не
# является, и ругаться на него — ложное срабатывание.
gates=()
while IFS= read -r p; do
  [[ -n "$p" ]] && gates+=("$p")
done < <(git ls-files "$LINT_DIR/check_*.sh" "$LINT_DIR/check_*.py")

# Ноль гейтов — ОШИБКА, а не «пропуск». Этот скрипт лежит в $LINT_DIR, значит CQG
# разворачивается; пустой список означает «скрипты не закоммичены» или «сломан
# LINT_DIR». Мягкий пропуск здесь был бы тем самым тихо-зелёным проходом, ради
# которого гейт и написан.
if (( ${#gates[@]} == 0 )); then
  printf '%sERROR%s: в %s нет отслеживаемых гейт-скриптов (check_*.sh|py).\n' "$red" "$reset" "$LINT_DIR" >&2
  printf 'Только что создал? `git add %s` — untracked не считается.\n' "$LINT_DIR" >&2
  exit 1
fi

unwired=()
exempted=0
for path in "${gates[@]}"; do
  base=$(basename "$path")
  if reason=$(not_wired_reason "$base"); then
    printf '  ○ %-30s не подключён осознанно: %s\n' "$base" "$reason"
    exempted=$((exempted + 1))
    continue
  fi
  # -F: имя содержит точку, как regex она матчила бы лишний символ.
  if ! grep -qsF -- "$base" "${CONFIGS[@]}"; then
    unwired+=("$base")
  fi
done

# Обратная сторона: конфиг ссылается на скрипт, которого нет.
missing=()
while IFS= read -r ref; do
  [[ -n "$ref" ]] || continue
  [[ -e "$ref" ]] || missing+=("$ref")
done < <(grep -ohsE 'scripts/[A-Za-z0-9_/.-]+\.(sh|py)' "${CONFIGS[@]}" | sort -u)

if (( ${#unwired[@]} == 0 && ${#missing[@]} == 0 )); then
  printf '%sgate-coverage: OK%s — %d гейт(ов), подключено %d, осознанно нет %d (%d конфиг(ов))\n' \
    "$green" "$reset" "${#gates[@]}" "$(( ${#gates[@]} - exempted ))" "$exempted" "${#CONFIGS[@]}"
  exit 0
fi

# Циклы под защитой (( ${#arr[@]} )): в bash 3.2 — штатном на macOS — раскрытие
# пустого массива "${arr[@]}" падает по `set -u`, даже если массив объявлен.
if (( ${#unwired[@]} )); then
  for b in "${unwired[@]}"; do
    printf '%s  ✗  %s: скрипт есть, но НЕ подключён (pre-commit / CI / merge_guard)%s\n' "$red" "$b" "$reset" >&2
  done
fi
if (( ${#missing[@]} )); then
  for m in "${missing[@]}"; do
    printf '%s  ✗  %s: упомянут в конфиге, но файла нет%s\n' "$red" "$m" "$reset" >&2
  done
fi

if [[ "$STRICT" == "0" ]]; then
  printf '%sgate-coverage: WARNING (STRICT=0)%s\n' "$yellow" "$reset" >&2
  exit 0
fi
printf '\n%sERROR%s: гейт без подключения = гейта нет. Впиши его в `.pre-commit-config.yaml`\n' "$red" "$reset" >&2
printf 'или в CI-шаг, либо объяви исключение с причиной в not_wired_reason() этого скрипта.\n' >&2
printf 'Сверься с таблицей §3 построчно — не собирай конфиг «по смыслу».\n' >&2
exit 1
```

# Приложение B — конфиги

### `backend/pyproject.toml (фрагмент)`

> Фрагмент. `[[tool.mypy.overrides]]` под свой легаси добавляй по мере правок — не копируй чужие.

```toml
# --- ruff (backend) -----------------------------------------------------------
[tool.ruff]
target-version = "py312"
line-length = 100
extend-exclude = ["migrations", ".venv", "venv", "__pycache__"]

[tool.ruff.lint]
select = ["E","W","F","I","N","UP","B","C4","C90","SIM","RUF","ASYNC","S","PT","RET","PIE","PL","TRY400","DTZ"]
ignore = [
    "E501",                 # длину разрулит форматтер
    "S101",                 # assert разрешён
    "S104","S105","S106","S301","S311","S324","S603","S607",  # bandit-шум / осознанные кейсы
    "PLR0913",              # too-many-args — web-фреймворк DI часто > 5
    "PLR2004",              # magic-value — шумно
    "B008",                 # DI-объект как default аргумента (напр. FastAPI Depends())
    "RUF001","RUF002","RUF003",  # ambiguous unicode — не-ASCII в строках/логах
    "PLC0415",              # import-outside-top-level — осознанный lazy-import паттерн
]
# tests-код имеет свои послабления:
per-file-ignores = { "tests/**/*.py" = ["S","PLR2004","PLR0915","PLR0912","C901","PLC0415","B017","PT011","PT012","PT018","N806","N803","N802","E402","SIM117","PT006","E741","PLW0108","DTZ"] }

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 8
max-branches = 12
max-returns = 6
max-statements = 50

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true

# --- mypy (чистый strict; НЕ копируй сюда легаси [[overrides]] чужого проекта) -
[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true
warn_return_any = true
enable_incomplete_feature = ["NewGenericSyntax"]   # PEP 695 generics на mypy < 1.12
explicit_package_bases = true
namespace_packages = true
implicit_reexport = true                            # facade-модули с re-export
exclude = ["migrations/", "tests/", ".venv/", "venv/", "scripts/"]
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]
ignore_missing_imports = true
follow_imports = "silent"
```

### `<frontend>/eslint.config.js`

> `prettier` идёт ПОСЛЕДНИМ в массиве — отключает конфликтующие стилевые правила. Требует tsconfig со strict-флагами (§2.2).

```javascript
// ESLint flat config (ESLint 9+).
import js from '@eslint/js';
import ts from 'typescript-eslint';
import reactPlugin from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import importPlugin from 'eslint-plugin-import';
import prettier from 'eslint-config-prettier';

export default ts.config(
  { ignores: ['dist/**', 'coverage/**', 'node_modules/**', '*.config.js', '*.config.ts', 'src/test/**'] },

  js.configs.recommended,
  ...ts.configs.strict,
  ...ts.configs.stylistic,

  {
    files: ['src/**/*.{ts,tsx}'],
    plugins: { react: reactPlugin, 'react-hooks': reactHooks, import: importPlugin },
    languageOptions: {
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
      },
    },
    settings: { react: { version: 'detect' } },
    rules: {
      // React 17+ автоматический JSX runtime — импорт React не нужен
      'react/react-in-jsx-scope': 'off',
      'react/jsx-uses-react': 'off',
      'react/prop-types': 'off', // используем TypeScript

      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // unused vars с _ префиксом игнорируем
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],

      // warning-ратчет держит их суммой на нуле-в-росте (цель — 0)
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      'no-console': ['warn', { allow: ['warn', 'error'] }],

      // Function-level limits
      'max-lines-per-function': ['warn', { max: 80, skipBlankLines: true, skipComments: true }],
      complexity: ['warn', 10],
      'max-depth': ['warn', 4],
      'max-params': ['warn', 5],

      'import/order': [
        'warn',
        { 'newlines-between': 'always', groups: ['builtin', 'external', 'internal', 'parent', 'sibling', 'index'] },
      ],
    },
  },

  // Prettier — ПОСЛЕДНИМ, чтобы отключить конфликтующие стилевые правила
  prettier,
);
```

### `<frontend>/.prettierrc`

> Версию Prettier пинь EXACT в package.json (без caret).

```json
{ "singleQuote": true, "trailingComma": "all", "printWidth": 100, "tabWidth": 2 }
```

### `backend/.importlinter`

> **Пример.** Замени `<pkg>` и домены на свои; легаси-нарушения — в `ignore_imports` с `TODO`.

```ini
# Static dependency direction enforcement (import-linter).
# Запуск: lint-imports (из каталога с этим конфигом, обычно backend/).
# Стратегия: enforce то, что уже соблюдается; расширять по мере добавления слоёв.
# Легаси-нарушения выносить в ignore_imports с пометкой "TODO: <тикет>".
#
# ЗАМЕНИ <pkg> и имена доменов на свои.

[importlinter]
root_packages =
    <pkg>

# --------------------------------------------------------------------
# Контракт 1: слой интеграций — ЛИСТ. Ни одна интеграция не импортирует
# другие домены, иначе теряется смысл leaf-слоя.
# --------------------------------------------------------------------
[importlinter:contract:integrations-are-leaves]
name = integrations не импортирует другие домены
type = forbidden
source_modules =
    <pkg>.integrations
forbidden_modules =
    <pkg>.core
    <pkg>.<other_domain>
allow_indirect_imports = True
ignore_imports =
    # <pkg>.integrations.x -> <pkg>.auth.y   # TODO: <тикет>

# --------------------------------------------------------------------
# Контракт 2: core — слоистый домен: api -> services -> repository -> models.
# --------------------------------------------------------------------
[importlinter:contract:core-layered]
name = core: api -> services -> repository -> models
type = layers
layers =
    api
    services
    repository
    models
containers =
    <pkg>.core
exhaustive = False

# --------------------------------------------------------------------
# Контракт 3: models — листовой слой (не импортирует верхние слои).
# --------------------------------------------------------------------
[importlinter:contract:core-models-leaf]
name = core.models не импортирует api / services / repository
type = forbidden
source_modules =
    <pkg>.core.models
forbidden_modules =
    <pkg>.core.api
    <pkg>.core.services
    <pkg>.core.repository
allow_indirect_imports = True
```

### `.pre-commit-config.yaml`

> В корне репозитория. Пути под backend/-frontend/-layout — поправь `files:`/`entry:`/путь к venv под свою структуру.

```yaml
# pre-commit hooks. Установка: pip install pre-commit && pre-commit install.
# Прогон по всему дереву: pre-commit run --all-files.
#
# Пути ниже — под backend/-и-frontend/-layout (git-root = корень проекта).
# Поправь files:/exclude:/entry: и путь к venv (.venv) под свою структуру.
# Скрипт-хуки читают структуру из env LINT_PY_SRC/LINT_FE_DIR/... (см. §6 документа) —
# задай их здесь через `entry: bash -c 'LINT_PY_SRC=... && …'`, если дефолты не подходят.

default_install_hook_types: [pre-commit]
fail_fast: false

repos:
  # -------------------------------------------------------------------------
  # Python: ruff (lint + format) — под backend.
  # -------------------------------------------------------------------------
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.13
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
        files: ^backend/
      - id: ruff-format
        files: ^backend/

  # -------------------------------------------------------------------------
  # Python: mypy strict на изменённых файлах через проектный venv (local hook,
  # НЕ mirrors-mypy: у того изолированное venv без проектных плагинов/модулей).
  # -------------------------------------------------------------------------
  - repo: local
    hooks:
      - id: mypy
        name: mypy strict (изменённые файлы)
        language: system
        types_or: [python]
        files: ^backend/
        exclude: /tests/
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)/backend" && files=(); for f in "$@"; do files+=("${f#backend/}"); done; .venv/bin/mypy --config-file pyproject.toml "${files[@]}"' --
        pass_filenames: true

  # -------------------------------------------------------------------------
  # TypeScript / React: ESLint (per-file errors) + warning-ратчет + Prettier.
  # -------------------------------------------------------------------------
  - repo: local
    hooks:
      - id: eslint
        name: ESLint (TypeScript)
        language: system
        types_or: [ts, tsx]
        files: ^frontend/src/
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)/frontend" && files=(); for f in "$@"; do files+=("${f#frontend/}"); done; npx --no-install eslint "${files[@]}"' --
        pass_filenames: true

      - id: eslint-warning-ratchet
        name: ESLint warnings — рост запрещён (count-ratchet)
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)" && bash scripts/lint/check_eslint_warnings.sh'
        files: ^frontend/src/.*\.(ts|tsx)$
        pass_filenames: false

      - id: prettier
        name: Prettier (TypeScript / JSON / CSS)
        language: system
        types_or: [ts, tsx, javascript, json, css]
        files: ^frontend/src/
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)/frontend" && files=(); for f in "$@"; do files+=("${f#frontend/}"); done; npx --no-install prettier --check "${files[@]}"' --
        pass_filenames: true

  # -------------------------------------------------------------------------
  # Файлы кода: prod <= 500 / tests <= 1000 строк (baseline-ratchet).
  # -------------------------------------------------------------------------
  - repo: local
    hooks:
      - id: file-length
        name: Файлы кода <= 500/1000 строк (baseline-ratchet)
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)" && bash scripts/lint/check_file_length.sh'
        types_or: [python, ts, tsx]
        pass_filenames: false

  # -------------------------------------------------------------------------
  # Греп-гейты конвенций (per-file baseline-ratchet).
  # -------------------------------------------------------------------------
  - repo: local
    hooks:
      - id: config-access-gate
        name: config-access — типизированный config.X, не getattr/os.getenv
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)" && bash scripts/lint/check_grep_gate.sh --rule config-access'
        files: ^backend/.*\.py$
        pass_filenames: false
      - id: di-indirection-gate
        name: di-indirection — без pkg/session/ctx Any и importlib reach-back
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)" && bash scripts/lint/check_grep_gate.sh --rule di-indirection'
        files: ^backend/.*\.py$
        pass_filenames: false
      - id: service-no-web-gate
        name: service-no-web — сервис-слой не импортирует web-фреймворк
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)" && bash scripts/lint/check_grep_gate.sh --rule service-no-web'
        files: ^backend/.*\.py$
        pass_filenames: false
      - id: no-grab-bag-module-gate
        name: no-grab-bag — utils/misc/common/helpers.py без темы запрещены
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)" && bash scripts/lint/check_grep_gate.sh --rule no-grab-bag-module'
        files: ^backend/.*\.py$
        pass_filenames: false
      - id: silent-except-gate
        name: silent-except — broad-except без raise/лога (AST)
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)" && backend/.venv/bin/python scripts/lint/check_ast_gate.py --rule silent-except'
        files: ^backend/.*\.py$
        pass_filenames: false
      - id: inline-prompt-gate
        name: inline-prompt — LLM-промпт инлайном в .py (AST)
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)" && backend/.venv/bin/python scripts/lint/check_ast_gate.py --rule inline-prompt'
        files: ^backend/.*\.py$
        pass_filenames: false

  # -------------------------------------------------------------------------
  # DRY / copy-paste гейт (jscpd clone-count ratchet).
  # -------------------------------------------------------------------------
  - repo: local
    hooks:
      - id: jscpd-dry-gate
        name: DRY — рост копипаста (jscpd clone-count ratchet)
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)" && bash scripts/lint/check_jscpd_gate.sh'
        files: ^backend/.*\.py$
        pass_filenames: false

  # -------------------------------------------------------------------------
  # import-linter — направление зависимостей между слоями.
  # -------------------------------------------------------------------------
  - repo: local
    hooks:
      - id: import-linter
        name: import-linter — dependency direction
        language: system
        entry: bash -c 'cd "$(git rev-parse --show-toplevel)/backend" && ./.venv/bin/lint-imports'
        files: ^backend/.*\.py$
        pass_filenames: false

  # Мета-гейт — ПОСЛЕДНИМ. Проверяет, что все гейты выше вообще подключены:
  # забытый в этом файле скрипт молча не работает (§3, gate-coverage).
  - repo: local
    hooks:
      - id: gate-coverage
        name: every gate script is wired into pre-commit/CI
        entry: bash scripts/lint/check_gate_coverage.sh
        language: system
        pass_filenames: false
        always_run: true
```

### `backend/requirements-dev.txt`

```text
# backend/requirements-dev.txt — dev-инструменты гейтов.
ruff>=0.6.9
mypy>=1.11.2
types-PyYAML>=6.0        # + прочие type-stubs под свои untyped-либы
pre-commit>=3.8.0
import-linter>=2.0

# ------------------------------------------------------------------------
# frontend: package.json -> devDependencies (менеджер на выбор):
#   "eslint": "^9",
#   "typescript-eslint": "^8",
#   "@eslint/js": "^9",
#   "eslint-config-prettier": "^9",
#   "eslint-plugin-react": "^7",
#   "eslint-plugin-react-hooks": "^5",
#   "eslint-plugin-import": "^2",
#   "prettier": "3.8.3",   <-- ПИН EXACT, без caret (caret-дрейф форматтера = ложные diff'ы)
#   "jscpd": "^5"
# ------------------------------------------------------------------------
```

---

## Changelog этого канона

| Дата | Версия | Изменение |
|---|---|---|
| 2026-07-26 | 1.0 | Initial: 10 commit-гейтов на baseline-ratchet + ручной diff-coverage; полные исходники скриптов и конфигов; §2.7 secrets |
| 2026-07-27 | **1.3** | **Багфикс** `check_eslint_warnings.sh`: `cd` в отсутствующий каталог фронта ронял гейт сырой ошибкой шелла (backend-only проект не мог закоммитить) — добавлен мягкий skip, как у jscpd. Баннер `⬇ BOOTSTRAP PAYLOAD` перед Приложением A + «стоимость чтения» в §0: приложения (65% файла) в обычной работе не читаются |
| 2026-07-27 | **1.2** | §8.5 branch protection (без required checks + review CI декоративен, готовые `gh api` команды); workflow расширен: circuit breakers, гейт code↔canon, метрики в step summary, `fetch-depth: 0` в delivery-джобе; §8.1 — полная таблица дыр |
| 2026-07-27 | **1.1** | Review pass: §8 CI как обязательный слой + новый гейт `check_baseline_ratchet.sh` (снимок вверх больше не переснять молча) + workflow в §8.3; блок «Применимость» (документ не stack-agnostic: что переносится, что адаптировать); счёт гейтов приведён к таблице (10 + 1 ручной + 11-й secrets); canon version в шапке; шаг 8 в §5 |

---

*Конец. Соседние каноны: [AGENT_STACK.md](AGENT_STACK.md) ·
[AGENT_DELIVERY_HARNESS.md](AGENT_DELIVERY_HARNESS.md) ·
[OKF_KNOWLEDGE_BUNDLE.md](OKF_KNOWLEDGE_BUNDLE.md)*
