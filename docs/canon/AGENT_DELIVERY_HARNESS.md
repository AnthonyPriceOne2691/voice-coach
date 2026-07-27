# Agent Delivery Harness — каркас предсказуемой AI-разработки

> **Карта стека (вход для агента):** [AGENT_STACK.md](AGENT_STACK.md)  
> **Слой в стеке:** ① процесс (фундамент) → затем
> [CODE_QUALITY_GATES.md](CODE_QUALITY_GATES.md) → затем
> [OKF_KNOWLEDGE_BUNDLE.md](OKF_KNOWLEDGE_BUNDLE.md).  
> Не разворачивай CQG/OKF раньше этого файла, если человек явно не сказал иначе.

**Canon version:** `delivery@1.11` · 2026-07-27 (Changelog — в конце файла).
При развёртывании впиши версию в `delivery/CONSTITUTION.md` и `STATUS.md`
(поле `stack:`) — иначе проект не знает, какую ревизию каркаса он получил.

**Самодостаточный универсальный документ.** Кладёшь этот один файл в **новый или
существующий** проект — агент разворачивает **delivery-контур**: фазы
(specify → plan → tasks → implement → verify → converge → handoff), Definition of Done,
stop-conditions, изоляция изменений, thin behavioral contract для coding-агента,
smoke-evals и hook в `AGENTS.md` / Cursor rule.

> **Язык:** проза — русский, идентификаторы / пути / команды — английские.
>
> **Что это НЕ делает:** не дублирует правила чистого кода и lint-гейты
> (`CODE_QUALITY_GATES.md`) и не дублирует формат knowledge-bundle
> (`OKF_KNOWLEDGE_BUNDLE.md`). Этот файл — **каркас процесса**. Те два — **слои
> усиления**, которые подключаются **после** этого файла (порядок — §0 и
> [AGENT_STACK.md](AGENT_STACK.md)).
> «Рядом в репо» допустимо, но **разворачивать** их раньше delivery нельзя:
> сначала каркас процесса, затем CQG, затем OKF.

---

## 0. Порядок развёртывания стека (обязательно читать первым)

### 0.1. Этот файл — фундамент

В любом проекте (greenfield или brownfield) порядок такой:

| Шаг | Артефакт | Зачем |
|---:|---|---|
| 2026-07-27 | **v1.11**: в A.12 `STACK-ACCEPTANCE.md` добавлена «Карта ролей гейтов» — фиксирует, какой скрипт занял какую роль в этом проекте (иначе таблица CQG §3, ключёванная именами файлов, расходится с репозиторием молча) |
| 2026-07-27 | **v1.10** (уроки первого реального развёртывания): §3.1a — «зелёность ≠ покрытие», класс oracle, которого не хватало (невключённый oracle неотличим от проходящего); §5.4 — критерий «усилил, а не извинился» = воспроизвести ошибку и показать, что новый oracle её ловит; A.12 `STACK-ACCEPTANCE.md` — приёмка + разбор её слепых пятен; в дереве §2.3 |
| 2026-07-27 | **v1.9**: гейт мержа отвязан от платного тарифа — §10.4 правило 3a (база в репозитории: `merge_guard.sh`, pre-push, `needs:`; защита ветки — усиление) + три состояния `ci-oracles` (`deployed`/`tooling`/`weak`, `tooling` — легитимный режим, а не поддавки); §5.2 переписан под оба случая; `--require-ci` принимает `tooling` |
| 2026-07-27 | **v1.8**: в DoD bootstrap (§7.3) помечены два ручных/настраиваемых пункта — подтверждение branch protection и раскладка путей («зелёный гейт, который ничего не видит, хуже красного») |
| **1** | **Этот файл** → контур `delivery/` + hook | Процесс: что строить, как резать, когда «готово», как не врать себе |
| **2** *(рекомендуется)* | `CODE_QUALITY_GATES.md` | Механические oracles на **форму** кода (lint/types/architecture) |
| **3** *(рекомендуется)* | `OKF_KNOWLEDGE_BUNDLE.md` | Канон **смысла** домена (политики, ADR, метрики) вместо RAG-угадывания |
| **4** *(по нужде)* | Agent Behavioral Contracts (ABC) для **продуктовых** агентов | Runtime-контракты ботов/outreach/judges — не путать с coding-delivery |

**Инвариант:** без шага 1 агент умеет писать код; **не умеет** доказуемо
заканчивать работу. Шаги 2–3 без шага 1 дают «чистый код без цели» и «wiki
без поставки».

Если в проекте уже есть CQG и/или OKF — **не сносить**. Разверни `delivery/`
поверх, затем в `AGENTS.md` пропиши порядок чтения: Delivery → Quality Gates →
OKF (см. A.5).

### 0.1a. CI — сквозной слой ④, не часть одного канона

Слои ①–③ отвечают на «что делать». **CI отвечает на «кто это проверит, когда
никто не смотрит»** — и по построению принадлежит всем трём: одна джоба гоняет
`delivery_check` (①), `pre-commit`/ратчеты (②) и `okf_validate`/`okf_sync_gate` (③).

Поэтому:

- **Контракт** («что обязано гоняться, что значит красный») — здесь, §10.4.
- **Реализация** (workflow, скрипты) — [CODE_QUALITY_GATES.md](CODE_QUALITY_GATES.md) §8,
  потому что там живут исходники всех гейт-скриптов и там же их настройка путей.
- **Разворачивается** — вместе с ② (шаг 2 ниже), но обслуживает все три слоя.

Это сознательное исключение из «CQG не ведёт поставку»: workflow — единственный
файл в стеке, который по определению сквозной. Не пытайся расщепить его на три.

### 0.2. Границы: что где живёт

| Вопрос | Этот harness | CQG | OKF | CI ④ |
|---|---|---|---|---|
| «Что и зачем строим?» | **Да** (`spec`) | Нет | Может хранить канон после принятия | Нет |
| «Как режем работу?» | **Да** (`plan`/`tasks`) | Нет | Нет | Нет |
| «Код достаточно чистый?» | Ссылается на CQG | **Да** (правила) | Нет | **Да** (прогон) |
| «Как у нас принято считать X?» | Ссылается на OKF | Нет | **Да** | Нет |
| «Канон не разъехался с кодом?» | Гейт в DoD §3.2.4 | Нет | **Да** (`implementation:`) | **Да** (`okf_sync_gate`) |
| «Можно ли закрыть задачу?» | **Да** (DoD + verify) | Часть DoD (гейты зелёные) | Часть DoD (канон обновлён) | **Да** (единственный неподделываемый прогон) |
| «Агент не ушёл в drift mid-session?» | **Да** (thin ABC §4) | Косвенно | Косвенно | breakers §3.4 |

### 0.3. Как пользоваться документом

| Секция | Содержание |
|---|---|
| §1 | Философия harness (без повторения CQG/OKF) |
| §2 | Фазовый конвейер и артефакты |
| §3 | Oracles, DoD, stop-gates, circuit breakers |
| §4 | Thin ABC для **coding**-агента |
| §5 | Изоляция (worktree default), Builder≠Verifier, anti-oneshot |
| §6 | Eval suite / smoke (product oracles) |
| §7 | Развёртывание (агент / вручную) |
| §8 | Brownfield / стыковка с уже лежащими CQG+OKF |
| §9 | Observability / метрики harness |
| §10 | Agent hooks (enforcement stop-gates) + **§10.4 CI** (необходимый слой) |
| §11 | Skills / prompts catalog (указатель) |
| Приложение A | Шаблоны файлов |
| Приложение B | `delivery_check.py` — фазовый гейт |
| Приложение C | `delivery_metrics.py` — автосбор метрик §9 |

**Стоимость чтения.** Канон — §0–§11 (≈700 строк). Приложения — **bootstrap
payload** (≈900 строк): читаются при развёртывании и при правке конкретного
шаблона, но **не** в обычной работе над фичей. Не тяни весь файл в контекст без
нужды — §0.3 выше говорит, какая секция отвечает на твой вопрос.

---

## 1. Философия

### 1.1. Agent = Model + Harness

Модель рассуждает. Harness делает рассуждение **проверяемым и останавливаемым**.
Ошибка агента → чиним **harness** (новый oracle, лимит, фаза, hook), а не только
промпт «в следующий раз будь внимательнее».

### 1.2. Пять слоёв (этот документ закрывает процессные)

| Слой | Кто закрывает |
|---|---|
| Tool orchestration | IDE/agent runtime (Cursor / Claude Code / …) |
| **Verification loops** | §3 + CQG (код) + §6 (продукт) |
| **Context & memory** | OKF (канон) + `delivery/` (текущая поставка) |
| **Guardrails** | §4–§5 + hooks |
| **Observability** | §9 |

### 1.3. Спека executable, код — следствие

Пока нет принятого `spec` (и для нетривиального — `plan`/`tasks`), агент
**не начинает** широкую реализацию. One-shot «сделай фичу целиком» запрещён
по умолчанию (§5.3).

### 1.4. Done = oracles, не самооценка

Агент **не имеет права** объявить задачу выполненной, пока не зелёны stop-conditions
§3. Victory declaration bias — известный failure mode; harness его режет.

---

## 2. Фазовый конвейер

Вдохновлено Spec-Driven Development ([GitHub Spec Kit](https://github.com/github/spec-kit)),
но **самодостаточно**: CLI Spec Kit не обязателен. Достаточно дерева `delivery/`
и дисциплины ниже.

### 2.1. Фазы

```text
constitution (раз на проект)
    → specify
    → clarify*          (*если дыры)
    → plan
    → tasks
    → analyze*          (*consistency check)
    → implement         (по tasks, slice-ами)
    → verify            (oracles)
    → converge          (дыры → новые tasks → implement…)
    → handoff           (PR / OKF update / log)
```

| Фаза | Артефакт | Вопрос | Human gate? |
|---|---|---|---|
| **constitution** | `delivery/CONSTITUTION.md` | Нерушимые принципы процесса/продукта (не lint-правила) | Да, при создании |
| **specify** | `delivery/active/spec.md` | *Что* и *зачем* (без стека) | **Да** перед plan |
| **clarify** | правки в `spec.md` + список Q→A | Убрать двусмысленности | По необходимости |
| **plan** | `delivery/active/plan.md` | *Как*: стек, границы, риски | **Да** перед tasks на risky work |
| **tasks** | `delivery/active/tasks.md` | Атомарные шаги + зависимости | Нет (ревью по желанию) |
| **implement** | код + отмеченные tasks | Выполнение одного slice | Нет |
| **verify** | `delivery/active/verify-report.md` | Oracles зелёные? | Нет (факт машинный) |
| **converge** | доп. tasks или `CONVERGED` | Spec выполнен? | Да, если scope creep |
| **handoff** | PR + (если есть OKF) concept update | Передано людям | Да (merge) |

`*` — **подфазы**, не отдельные значения `phase:` в `STATUS.md`:
`clarify` идёт внутри/сразу после `specify`; `analyze` — после `tasks`,
перед `implement`. В STATUS остаются только фазы из колонки выше
(`specify` … `handoff`).

**Нельзя** схлопнуть `verify`. На мелких задачах `clarify`/`analyze` можно
пропустить.

### 2.2. Когда полный конвейер, когда короткий

| Класс работы | Минимум фаз |
|---|---|
| **S** — багфикс ≤1 файла, ясен repro | mini-spec (5–10 строк в `tasks.md`) → implement → verify |
| **M** — фича 1–2 дня | specify → plan → tasks → implement → verify → handoff |
| **L** — эпик / новый модуль / greenfield | полный конвейер + constitution + converge |
| **Hotfix** | mini-spec + implement → verify; post-factum `spec` в archive |

Класс **L без human OK на spec** — запрещён.

Перед фазой **implement** обязательно:

| Класс | Минимум артефактов |
|---|---|
| **S** | `tasks.md` (с mini-spec) |
| **M** | `spec.md` + `plan.md` + `tasks.md` + `human_ok_spec: yes` |
| **L** | как M + `human_ok_plan: yes` (risky/L) |

### 2.3. Дерево `delivery/`

```text
delivery/
  CONSTITUTION.md                 # принципы процесса (не CQG)
  README.md                       # как читать контур (коротко)
  STACK-ACCEPTANCE.md             # приёмка стека + разбор её слепых пятен (A.12)
  active/                         # текущая поставка (одна)
    STATUS.md                     # фаза, класс S/M/L, blockers
    spec.md
    plan.md
    tasks.md
    verify-report.md
    eval-smoke.md                 # product oracles для этой поставки
  archive/
    YYYY-MM-DD-<slug>/            # завершённые поставки
  evals/
    smoke/                        # постоянные smoke-сценарии репо
      README.md
```

Одновременно **одна** `active/` поставка. Новая тема → archive старой или
отдельная ветка/worktree со своей `delivery/active`.

### 2.4. Что писать в constitution (и чего не писать)

**Писать:** «сначала spec», «vertical slice», «не пушить в main», «HITL на
миграции/прод», «Builder≠Verifier», «ошибка → усили harness».

**Не писать:** лимиты длины функций, select ruff, import-linter слои — это
**CQG**. Не писать YAML frontmatter OKF — это **OKF**.

Если CQG/OKF уже развёрнуты, constitution содержит **одну строку-указатель**:

```markdown
- Code shape oracles: see `CODE_QUALITY_GATES.md` (deployed).
- Domain canon: see `knowledge/` per `OKF_KNOWLEDGE_BUNDLE.md` (deployed).
```

---

## 3. Oracles, DoD, stop-gates, circuit breakers

### 3.1. Три класса oracle

| Класс | Примеры | Где живёт |
|---|---|---|
| **A. Shape** | lint, types, import direction, file-length | CQG / pre-commit |
| **B. Behavior** | unit/integration tests, diff-coverage | тестовый раннер проекта |
| **C. Product / delivery** | smoke evals §6, «spec acceptance bullets зелёные», фаза verify | этот harness |

Для класса M/L harness **требует** все *доступные* классы oracle:

- **A:** если CQG/pre-commit есть — они; иначе временно `compile` /
  `tsc --noEmit` / «что есть», STATUS: `shape-oracles: weak`, backlog шаг 2 §0.1.
- **B:** если в репо есть тестовый раннер — прогон затронутого; иначе
  `behavior-oracles: weak` + обязательный класс **C**.
- **C:** acceptance / smoke §6 — для M/L обязателен всегда (даже при weak A/B).

**Где они должны запускаться.** Локальный прогон (pre-commit, hooks) — быстрая
петля для агента; **источник истины для DoD — CI** (§10.4). Любой oracle класса
A/B, который есть только локально, обходится одной командой (`git commit -n`) и
потому не является oracle в смысле §1.4.

### 3.1a. Зелёность ≠ покрытие (класс oracle, которого не хватало)

**Невключённый oracle неотличим от проходящего.** Зелёный прогон доказывает
исправность того, что **перечислено** в конфиге, и молчит о недостающем. Поэтому
у каждого класса A/B/C нужен второй вопрос:

| Вопрос | Что отвечает |
|---|---|
| «Зелены ли oracles?» | `pre-commit run --all-files`, тесты, smoke |
| **«А все ли oracles на месте?»** | **гейт покрытия**: CQG `gate-coverage` (каждый скрипт из `scripts/lint/` подключён), `delivery_check` (нужные артефакты фазы есть), `okf_sync_gate` (concept'ы не отстали) |

Разобранный случай (2026-07-27, первое реальное развёртывание): скрипт jscpd был
извлечён и адаптирован под язык проекта, но не вписан в `.pre-commit-config.yaml`.
Приёмка показала 7/7 зелёных — потому что проверяла «работает ли подключённое», а
не «подключено ли всё требуемое». Ошибка агента звучит так: **проверял, работает
ли то, что написал, вместо того чтобы проверить, написал ли всё, что перечислено.**

Правило: вводя новый oracle, сразу отвечай, **что сломается, если его забудут
подключить**. Если ответ «ничего, будет тихо зелено» — нужен гейт покрытия
(§5.4: ошибка → усиление harness).

### 3.2. Definition of Done (закрытие tasks / поставки)

Задачу/поставку **нельзя** считать done, пока:

1. Все релевантные items в `tasks.md` checked **или** явно `wontfix` с причиной.
2. `verify-report.md` существует и все обязательные oracles = PASS.
3. Зелены **и** локальные гейты (pre-commit / CQG), **и** CI-прогон на ветке
   поставки (§10.4). Локальный обход (`git commit -n`, `STRICT=0`, отключённый
   hook) прохождением **не считается**: DoD закрывает только зелёный CI-run,
   на который можно сослаться. Если CI ещё нет — `ci-oracles: weak` в STATUS
   + пункт backlog; на класс L такой режим требует human waiver.
4. Если развёрнут OKF и поставка меняла инвариант — обновлён concept +
   `knowledge/**/log.md` (правила — в OKF-каноне, здесь только гейт «сделано»).
5. `STATUS.md` → `phase: handoff` (после успешного converge) **или** явный
   verdict `CONVERGED` в verify-report при `phase: converge` с нулём открытых
   gaps (затем сразу handoff). Значения `phase: converged` **нет** — только
   `converge` / `handoff` из enum STATUS.
6. Diff в рамках circuit breaker (§3.4) **или** human waiver в STATUS.

### 3.3. Stop-gates (агент останавливается)

| Условие | Действие агента |
|---|---|
| Нет `spec.md` на классе M/L | Не писать prod-код; сначала specify |
| Oracle FAIL | Чинить или эскалировать; **не** «закрыть задачу» |
| Нет human OK на spec (M/L) | Ждать; не переходить к широкому implement |
| Circuit breaker сработал | Стоп; отчёт в STATUS; ждать человека |
| Противоречие spec ↔ plan | Clarify/analyze; не импровизировать в коде |
| Нужен секрет / prod mutate / force-push | HITL; не обходить |

### 3.4. Circuit breakers (дефолты; правятся в STATUS)

| Breaker | Дефолт | Смысл |
|---|---|---|
| `max_files_touched` | 25 за одну implement-сессию | Анти-oneshot |
| `max_loc_diff` | ±800 строк net | Разбиение PR |
| `max_implement_retries` | 3 на одну task | Потом эскалация |
| `max_verify_retries` | 3 | Потом эскалация / сужение scope |
| `max_session_minutes` | 90 (мягкий) | Handoff / новый slice |

Waiver: только человек, одной строкой в `STATUS.md`:
`waiver: max_files_touched=40 reason=… by=human:…`.

**Кто проверяет.** `max_files_touched` и `max_loc_diff` — механически:
`python scripts/delivery_check.py --diff-base origin/main` (шаг в CI, §10.4).
Считается дифф `merge-base..HEAD`; **не считаются** `delivery/**` и
`knowledge/**` — процессные артефакты не blast radius кода. Waiver-строка выше
парсится оттуда же: `max_*=N` в STATUS поднимает лимит без правки скрипта.
`max_implement_retries` / `max_verify_retries` / `max_session_minutes` остаются
самонаблюдением агента — счётчика сессии harness не имеет (см. §9.1,
`implement_retries` — поле MANUAL).

---

## 4. Thin ABC для coding-агента

Не путать с полным фреймворком Agent Behavioral Contracts — *«Agent Behavioral
Contracts: Formal Specification and Runtime Enforcement for Reliable Autonomous
AI Agents»*, V. P. Bhardwaj,
[arXiv:2602.22302](https://arxiv.org/abs/2602.22302) (сверено 2026-07-27) —
для автономных product-агентов. Здесь — **минимальный** контракт сессии
кодирования: \(C = (P, I, G, R)\).

Хранится в `delivery/CONSTITUTION.md` §Coding-agent contract и дублируется
кратко в `AGENTS.md`.

### 4.1. Preconditions \(P\)

- Известен класс работы S/M/L; прочитан `STATUS.md`.
- Рабочая копия: ветка/feature или worktree (§5.1), не «грязный main» без
  явного разрешения.
- **Перед implement** — артефакты из таблицы §2.2 (S: tasks; M: spec+plan+tasks
  + human_ok_spec; L: то же + human_ok_plan на risky/L).
- До implement на фазах specify/plan/tasks достаточно артефактов *текущей*
  фазы (не требовать tasks на этапе specify).

### 4.2. Invariants \(I\)

- Не коммитить секреты; не писать в `.env` с прод-значениями.
- Не `push --force` в `main`/`master`.
- Не объявлять done при красных oracles.
- Не расширять scope за пределы `spec.md` без записи в spec + human note.
- Одна active-поставка.

### 4.3. Governance \(G\)

- Human OK на spec (M/L) и на plan (L / risky).
- HITL: прод-деплой, миграции данных, удаление больших деревьев, платежные/
  security-инварианты (§10.3).
- Секреты в diff → stop (механический скан — CQG §2.7; процесс — §10).
- Builder не принимает свою работу (§5.2).

### 4.4. Recovery \(R\)

| Нарушение | Recovery |
|---|---|
| Oracle red | Fix ≤ `max_verify_retries`, иначе эскалация |
| Превышен breaker | Revert/разбить PR; STATUS |
| Scope creep | Вернуть в spec как open question; откатить лишний код или вынести в новую поставку |
| Потеря контекста / compact | Перечитать STATUS + spec + tasks; не продолжать «по памяти» |
| Опасное действие | Abort; описать в STATUS |

---

## 5. Изоляция, роли, anti-oneshot

### 5.1. Изоляция изменений (worktree — default)

**Дефолт для класса M/L:** отдельный git worktree (или эквивалентный sandbox),
чтобы провал агента не портил `main` и параллельные задачи не мешали друг другу.

```bash
# из корня репо (один раз на поставку)
slug="<short-slug>"          # из STATUS.md
git fetch origin
git worktree add "../$(basename "$PWD")-wt-${slug}" -b "feat/${slug}" origin/main
cd "../$(basename "$PWD")-wt-${slug}"
# дальше: delivery/active живёт на этой ветке; oracles гонять здесь
```

Закрытие worktree после merge:

```bash
cd /path/to/main-clone
git worktree remove "../$(basename "$PWD")-wt-${slug}"
git branch -d "feat/${slug}"   # если уже слита
```

| Режим | Когда |
|---|---|
| **Worktree (default M/L)** | Новая фича, рефакторинг, неизвестный blast radius |
| Feature-branch в том же clone | Класс S; или человек явно сказал «без worktree» |
| Прямо на `main` | **Запрещено** по умолчанию |

Опционально усилить: Docker/devcontainer для evals с БД — не обязательно для
bootstrap; достаточно worktree + локальные oracles.

В `STATUS.md` фиксируй: `worktree: ../repo-wt-<slug>` или `worktree: none (S)`.

### 5.2. Builder ≠ Verifier

| Роль | Делает | Не делает |
|---|---|---|
| **Builder** | Пишет код по tasks | Не ставит финальный PASS на verify |
| **Verifier** | Гоняет oracles, читает diff против spec, пишет verify-report | Не «доделывает фичу молча» в том же проходе без новой task |

На практике Verifier = (1) детерминированные команды + (2) отдельный агентский
проход / другая модель / человек. Self-verify alone на классе M/L — **недостаточно**.

**Кто проверяет.** Полностью механически независимость не проверить — но
самопринятие ловится: в `STATUS.md` есть `builder:`, в `verify-report.md` —
`Verifier:`; `delivery_check` падает, если Verifier не заполнен, и если на M/L
он совпадает с builder. Заявление в markdown — аудит-след.

Принуждение зависит от того, что доступно:

| Есть | Механизм |
|---|---|
| Платный тариф / публичный репо | **required review** в branch protection — PR не мержится без второго участника (строго лучше) |
| Бесплатный тариф | `merge_guard.sh` (CQG §8.5) не мержит, пока `delivery_check` красный, а тот требует заполненного и **отличного от builder** Verifier. Плюс дисциплина: verify-проход делает другая модель/сессия/человек |

Не подменяй Verifier на `process:ci`, если оракулов класса C нет: тогда «CI» не
проверил обещание spec, а только форму кода.

### 5.3. Anti-oneshot

- Implement идёт **task-by-task** (или vertical slice из tasks), с verify soft
  после slice.
- Запрещено в одном ходе: «реализуй весь plan».
- Новый файл в prod без строки в `tasks.md` — сначала дописать task.

### 5.4. Ошибка → усиление harness

После каждого провала, который «агент мог бы не повторить»:

1. Запись в `delivery/active/STATUS.md` (или archive lessons).
2. Если паттерн повторится — добавить oracle / breaker / строку в constitution /
   hook. **Не** оставлять только устное «учти».

**Критерий «усилил, а не извинился»:** воспроизведи исходную ошибку и покажи, что
новый oracle её ловит. Пример из первого развёртывания стека: гейт был извлечён,
но не подключён к `pre-commit` → добавлен мета-гейт `gate-coverage` (CQG §3) →
проверка: временно отключить гейт, убедиться, что мета-гейт падает с точным
указанием. Закрыт **класс** ошибки, а не один случай.

Итог приёмки стека и разбор таких случаев живут в `delivery/STACK-ACCEPTANCE.md`
(шаблон A.12) — чтобы следующий агент видел не только «что развёрнуто», но и где
процедура уже однажды подвела.

---

## 6. Eval suite / smoke-evals (product oracles)

Это не unit-тесты и не CQG. Это короткий набор **наблюдаемых** проверок:
«система делает то, что обещал spec». Eval harness ≠ agent harness: здесь
фиксируем *успех задачи*, а не стиль кода.

### 6.1. Постоянные (`delivery/evals/smoke/`)

Держи **3–10** сценариев на весь репо. Минимум после bootstrap:

| ID | Пример команды | Expected |
|---|---|---|
| S1 | health/curl или `GET /health` | HTTP 200 |
| S2 | `pytest -q` / `npm test` (CI-эквивалент) | exit 0 |
| S3 | (если есть) migrate на пустой БД | exit 0 |

Формат каталога:

```text
delivery/evals/smoke/
  README.md          # таблица ID → command → expected → timeout
  run.sh             # опц.: прогон всех S* подряд, exit 1 при любом fail
```

Каждый сценарий: **id, command, expected, timeout_sec**. Без «проверить
глазами», если можно автоматизировать.

### 6.2. На поставку (`delivery/active/eval-smoke.md`)

Acceptance из `spec.md` → **3–7** проверяемых пуль (класс M/L). Пример:

```markdown
- [ ] POST /items with valid body → 201 + id
- [ ] duplicate key → 409
- [ ] CMS list shows created item
```

**Verify** = прогон постоянных smoke **плюс** acceptance bullets.
Результат — в `verify-report.md` (класс C oracles).

### 6.3. Когда писать / обновлять evals

| Момент | Действие |
|---|---|
| После plan (M/L) | Набросать `eval-smoke.md` из acceptance |
| Перед implement | Зафиксировать; по возможности 1 failing/red сценарий = цель slice |
| После багфикса «агент снова сломал X» | Добавить **постоянный** S* в `evals/smoke/` (ошибка → oracle) |
| Класс S | Хватает существующих tests/smoke; строка в verify-report |

### 6.4. Как гонять

```bash
# постоянные
bash delivery/evals/smoke/run.sh    # если есть
# или построчно из README

# затем acceptance из active/eval-smoke.md (ручные/скриптовые чекбоксы)
python scripts/delivery_check.py --require-verify   # когда phase>=verify
```

Не дублируй сюда весь pytest — smoke = узкий «система жива + обещание spec».

---

## 7. Развёртывание

### 7.1. Способ 1 — через агента (рекомендуется)

Положи `AGENT_DELIVERY_HARNESS.md` в корень проекта и дай команду:

> «Разверни Agent Delivery Harness по `AGENT_DELIVERY_HARNESS.md`: создай
> дерево `delivery/` из Приложения A, заполни `CONSTITUTION.md` под этот
> проект (без дублирования lint-правил CQG и без OKF-спеки), вставь hook
> из A.5 в `AGENTS.md` или `.cursor/rules/`, положи `scripts/delivery_check.py`
> из Приложения B. Впиши версии стека (`stack: delivery@1.11, …`) в constitution и
> `STATUS.md`; проставь `ci-oracles:` по факту (§10.4). Если в корне уже есть
> `CODE_QUALITY_GATES.md` / `OKF_KNOWLEDGE_BUNDLE.md` — не копируй их содержимое;
> только проставь указатели в constitution и соблюди порядок §0.1. CQG и OKF **не**
> разворачивай в этом шаге, если человек отдельно не попросил — сначала
> каркас delivery.»

Greenfield «с нуля под полный стек» — отдельная команда человека, **после**
успешного шага 1:

> «Теперь по порядку §0.1 разверни CODE_QUALITY_GATES, затем OKF_KNOWLEDGE_BUNDLE.»

### 7.2. Способ 2 — вручную

1. Создай `delivery/` по §2.3 + шаблоны **Приложения A** (A.1–A.11): constitution,
   README, active STATUS/spec/plan/tasks/verify/eval-smoke, evals/smoke stub,
   metrics/hook skeletons.
2. Заполни constitution под продукт (10–20 пуль).
3. Вставь A.5 в agent instructions.
4. Скопируй B → `scripts/delivery_check.py`, `chmod +x`.
5. Для первой поставки: `STATUS.md` (`phase: specify`, `class: …`) + черновик
   `spec.md` или пустые скелеты plan/tasks.
6. Commit: `chore(delivery): bootstrap agent delivery harness`.

### 7.3. Definition of Done для bootstrap harness

- [ ] `delivery/CONSTITUTION.md` существует и не копирует CQG/OKF дословно
- [ ] `delivery/active/STATUS.md` с `phase:` и `class:`
- [ ] Hook A.5 в agent instructions
- [ ] `scripts/delivery_check.py` запускается
- [ ] `delivery/evals/smoke/README.md` (+ опц. `run.sh`) созданы
- [ ] В constitution есть указатели на CQG/OKF **если** они уже в репо; иначе
      явный backlog «шаг 2/3 §0.1»
- [ ] В constitution и `STATUS.md` записана версия стека
      (`stack: delivery@1.11, cqg@…, okf@…`) — какую ревизию канона развернули
- [ ] CI-джоба (§10.4) настроена **или** в STATUS стоит `ci-oracles: weak`
      с явным пунктом backlog
- [ ] ⚠ **Branch protection подтверждён человеком** (CQG §8.5) — ручной шаг вне
      репозитория, который никакой скрипт не проверит. Не подтверждён →
      `ci-oracles: weak`, а не «deployed»
- [ ] ⚠ **Раскладка путей настроена** (CQG §6, «Первый прогон»): каждый гейт
      показывает непустое число просканированных файлов. Зелёный гейт, который
      ничего не видит, — хуже красного
- [ ] (Опц.) hooks §10 / A.11 подключены к агенту — `hooks:` в STATUS/constitution

---

## 8. Brownfield и стыковка

### 8.1. Уже есть хаотичные `docs/` и агент «просто кодит»

1. Развернуть этот harness (§7).
2. Новую работу — только через `delivery/active`.
3. Потом CQG (ratchet, не big-bang).
4. Потом OKF (канон + ratchet из плоских docs — по OKF-канону).

### 8.2. Уже есть CQG и/или OKF

1. Delivery поверх (§7.1).
2. В DoD verify включить: `pre-commit` / CQG-скрипты; OKF update при смене
   инвариантов.
3. Не переносить lint-правила в constitution.

### 8.3. Уже есть product-agent contracts (ABC)

Оставить их в коде/доках продукта. Coding thin-ABC (§4) — отдельно, в
`delivery/`. Не сливать в один файл.

---

## 9. Observability / метрики (чтобы harness улучшался)

Без цифр harness не улучшается — остаётся «папка с md». Снимается **раз на
поставку**, автоматически:

```bash
python scripts/delivery_metrics.py --base origin/main --write
```

Скрипт (Приложение C) считает из git всё, что считается, и вставляет блок A.10 в
`verify-report.md`; поля, которые git не знает, помечает `MANUAL` — их дозаполняет
агент/человек. `delivery_check` **не даёт закрыть handoff** без этого блока, поэтому
ритуал §9.2 перестал быть добровольным.

### 9.1. Базовый набор

| Метрика | Как считать | Зачем |
|---|---|---|
| `time_to_accepted_spec` | часы/дни от первой draft spec → `human_ok_spec: yes` | Узкое место в clarify? |
| `implement_retries` | число «починил после fail oracle» на task | Слабый plan/tasks |
| `verify_fails_before_green` | сколько красных прогонов до PASS | Слабые evals / oneshot |
| `files_touched` / `loc_diff` | `git diff --stat` | Ломаются ли breakers §3.4 |
| `rework_after_done` | коммиты/PR после объявленного done до merge | Не было Verifier |
| `harness_hardened` | yes/no: добавлен oracle/hook/breaker после ошибки | Растёт ли система |
| `est_token_or_cost` | грубо: сессии × модель (если видно) | Дорогие oneshot-петли |

**Что считается само** (`delivery_metrics.py`): `files_touched`/`loc_diff`,
`commits`, `time_to_accepted_spec` (от появления `spec.md` до `human_ok_spec: yes`
в истории STATUS), `rework_after_done` (коммиты после первого `phase: handoff`),
`harness_hardened` (тронуты ли `scripts/lint/**`, `delivery/evals/**`, hooks, CI).
**MANUAL:** `implement_retries`, `verify_fails_before_green`, `est_token_or_cost` —
их знает только сессия/биллинг, и выдумывать их скрипт не будет.

Опционально на уровне команды (не обязательно в md): cost per merged PR,
time-to-merge — из Git hosting / биллинга IDE.

### 9.2. Ритуал

1. На handoff — прогони `delivery_metrics.py --write`, дозаполни MANUAL-поля
   (без блока метрик `delivery_check` не пропустит handoff).
2. Если `harness_hardened: no` при `verify_fails_before_green ≥ 2` — **в том же
   PR/следующей поставке** добавь smoke S* или breaker/hook (§5.4).
3. Раз в несколько поставок — просмотри archive: повторяющиеся fails → усили §3/§6/§10.

---

## 10. Agent hooks (enforcement stop-gates)

Текст в `AGENTS.md` агент иногда игнорирует. **Hook** — срабатывает на событии
инструмента (до/после edit, stop) и может **заблокировать** ход.

Полный runtime зависит от IDE (Cursor hooks, Claude Code `hooks`, и т.д.).
Ниже — **контракт поведения**; конкретный JSON/shell — Приложение A.11
(адаптируй под свой агент).

### 10.1. Минимальный набор hooks

| Hook | Когда | Поведение |
|---|---|---|
| **stop-on-red** | Перед объявлением done / Stop | Если `pre-commit` / `delivery_check` / smoke fail → **не** завершать успешно; вернуть stderr агенту |
| **protect-main** | PreToolUse shell/git | Блок `push --force` в main/master; блок commit прямо на main без waiver |
| **secrets-scan** | PreCommit / перед push | Делегировать CQG / gitleaks / detect-secrets (§ CQG 2.7) |
| **circuit-breaker** | Post-edit или stop | Если `git diff --stat` > `max_files_touched` / LOC — предупреждение или блок до human waiver в STATUS |

### 10.2. Правила

1. Hook = детерминированная команда (exit 0/1), не «спроси LLM».
2. `STRICT=0` / soft — только с явного human waiver (как в CQG).
3. Не дублируй в hooks весь CQG — вызывай `pre-commit run` / уже существующие скрипты.
4. После установки hooks — строка в constitution: `hooks: deployed (cursor|claude|…)`.

### 10.3. HITL / security (процессная часть)

Механический «секрет в git» — **CQG §2.7**. Здесь — **когда остановиться**:

- Prod deploy, irreversible data migration, удаление больших деревьев, платежи,
  ротация ключей → **HITL**, не «агент сам».
- Обнаружен секрет в diff → stop + человек; не «почистим потом».

### 10.4. CI — необходимый слой (локальные гейты обходятся)

Hooks и pre-commit живут **на машине агента** и обходятся тремя способами:
`git commit -n`, `STRICT=0`, «hook не установлен в этом клоне». Пока те же
проверки не гоняются **вне** этой машины, «Done = oracles» (§1.4) держится на
добросовестности исполнителя — то есть на самооценке, которую harness как раз
и запрещает.

**Инвариант:** каждый oracle, упомянутый в DoD, должен иметь **CI-эквивалент**
на ветке поставки. CI — не «дубль для красоты», а единственный неподделываемый
прогон.

| Слой | Локально | В CI | Комментарий |
|---|---|---|---|
| **A. Shape** | pre-commit (быстро, на staged) | `pre-commit run --all-files` | CI видит всё дерево, а не staged-файлы |
| **B. Behavior** | затронутые тесты | полный сьют + `check_diff_coverage.sh` | diff-coverage — ручной локально, обязательный в CI |
| **C. Product** | `delivery/evals/smoke/run.sh` | тот же `run.sh` | если нужен БД/сервис — services в CI-джобе |
| **Delivery-фазы** | `delivery_check.py` | `delivery_check.py --require-spec` | ловит «implement без spec» до ревью |
| **Secrets** | secrets-хук | тот же хук + scan истории ветки | soft-режим в CI запрещён (CQG §2.7) |

**Правила**

1. **`STRICT=0` в CI запрещён.** Soft-режим — только локальная аварийная мера,
   и она обязана быть видна в PR. CI гоняет строго.
2. **CI обязателен для класса M/L.** Для S достаточно локальных гейтов + CI на
   PR, если он уже настроен.
3. **Красный CI = stop-gate** (§3.3): не «домержим и починим», не rerun «а вдруг
   позеленеет» без разбора причины.
3a. **Гейт мержа не зависит от тарифа хостинга.** Серверная защита ветки платная
   (GitHub: rulesets — Team+, branch protection приватного репо — Pro+), поэтому
   база принуждения лежит **в репозитории**: мерж только через `merge_guard.sh`
   (гейты на слитом состоянии), тяжёлые проверки на `pre-push`, downstream-джобы
   через `needs:`. Детали и скрипт — CQG §8.5. Защита ветки — усиление сверху,
   не предпосылка.
4. **Нет CI (нет hosting / офлайн-репо)?** Тогда в `STATUS.md`
   `ci-oracles: weak`, и Verifier (§5.2) обязан прогнать `pre-commit run
   --all-files` + полный сьют + smoke **в чистом клоне** и вложить вывод в
   `verify-report.md`. Это компенсация, а не эквивалент.
5. Конкретный workflow (GitHub Actions) — **CQG §8**; здесь только контракт
   «что обязано гоняться».

**Три состояния `ci-oracles:` в STATUS** (не два — иначе бесплатный тариф вечно
числится «weak» и waiver превращается в формальность):

| Значение | Когда | Класс L |
|---|---|---|
| `deployed` | CI + **серверный** гейт мержа (required checks / protected branch) | ок |
| `tooling` | CI есть; гейт мержа — в репозитории (`merge_guard.sh` + pre-push + `needs:`), серверного нет по тарифу | ок; в STATUS одной строкой отметить остаток: force-push и админ-обход не закрыты |
| `weak` | CI нет вообще | нужен human waiver |

Строка в constitution после настройки:
`ci: deployed (github-actions) merge-gate: server|tooling`.

---

## 11. Skills / prompts catalog (указатель)

Промпты и agent skills **не живут внутри этого канона** (и не раздувают OKF
эпиками). Каталог в репо:

```text
skills/                    # или .cursor/skills / prompts/
  README.md                # индекс: имя → путь → когда звать
  <skill-name>/
    SKILL.md               # инструкция
    scripts/…              # опц. детерминированные шаги
```

| Правило | Где enforced |
|---|---|
| LLM-промпт >5–10 строк не inline в `.py` | **CQG** `inline-prompt` |
| Индекс skills + «когда звать» | `skills/README.md`; указатель в [AGENT_STACK.md](AGENT_STACK.md) |
| Стабильный skill как сущность домена | Опц. OKF `type: Reference` → путь в `skills/` |

Агент: не копируй промпты в `delivery/active/`; ссылайся на skill по имени.

---

---

> ## ⬇ Ниже — BOOTSTRAP PAYLOAD (строки ~706–1613)
>
> Шаблоны файлов и исходники скриптов. **В обычной работе (фича/баг) не читай** —
> канон закончился выше. Читай отсюда только когда **разворачиваешь** контур или
> правишь конкретный шаблон/скрипт: тогда бери нужное приложение целиком.
>
> | Что | Где |
> |---|---|
> | Шаблоны `delivery/**` | Приложение A (A.1–A.11) |
> | `scripts/delivery_check.py` | Приложение B |
> | `scripts/delivery_metrics.py` | Приложение C |

---

# Приложение A — шаблоны

### A.1. `delivery/CONSTITUTION.md`

```markdown
# Delivery constitution

**Version:** 1.0
**Ratified:** YYYY-MM-DD
**Canon stack:** delivery@1.11 · cqg@<version|absent> · okf@<version|absent>
<!-- версии из шапок соответствующих *.md; absent = слой не развёрнут -->
**CI:** not-deployed | deployed (github-actions|gitlab|…)   <!-- §10.4 -->

## Non-negotiables

- Done закрывается **зелёным CI-прогоном** (§10.4), не локальным «у меня прошло».
- `STRICT=0` / `git commit -n` — аварийная локальная мера, видимая в PR; в CI запрещены.

## Process principles

1. Spec before broad implementation (class M/L).
2. Vertical slices; no oneshot of the whole plan.
3. Done = oracles (shape + behavior + product), never self-declaration alone.
4. Builder ≠ Verifier.
5. Agent mistake → strengthen harness (oracle / breaker / hook), not only prompts.
6. One `delivery/active` at a time.

## Coding-agent contract (thin ABC)

### Preconditions
- STATUS.md read; class S/M/L known; branch/worktree set.
- Before implement: artifacts per harness §2.2 (S: tasks; M/L: spec+plan+tasks + human_ok_spec).

### Invariants
- No secrets in git; no force-push to main; no done-on-red; no silent scope creep.

### Governance
- Human OK on spec (M/L). Human OK on plan (L / risky). HITL on prod deploy, data migrations, security-sensitive changes.

### Recovery
- On oracle red: fix ≤ retry budget, else escalate in STATUS.md.

## Pointers to sibling layers (fill if deployed)

- Code shape oracles: `CODE_QUALITY_GATES.md` — [ ] not deployed / [ ] deployed
- Domain canon: `OKF_KNOWLEDGE_BUNDLE.md` / `knowledge/` — [ ] not deployed / [ ] deployed
- Agent hooks (§10): [ ] not deployed / [ ] deployed
- CI oracles (§10.4, workflow per CQG §8): [ ] not deployed / [ ] deployed
- Skills catalog: `skills/README.md` — [ ] absent / [ ] present
```

### A.2. `delivery/active/STATUS.md`

**Важно:** значения-плейсхолдеры записаны как `<a|b|c>` и **не проходят**
`delivery_check.py` — незаполненный STATUS падает с ошибкой, а не молча
трактуется как `class: S`. Заполняй **одним** значением без вертикальной черты.

```markdown
# Active delivery status

- **slug:** <short-slug>
- **stack:** delivery@1.11, cqg@<version|absent>, okf@<version|absent>
- **class:** <S|M|L>
- **phase:** <specify|plan|tasks|implement|verify|converge|handoff>
  (подфазы clarify/analyze в STATUS не выносятся — см. §2.1)
- **builder:** <agent:name|human:name>     <!-- кто пишет код; §5.2 -->
- **verifier:** <agent:name|human:name|process:ci>  <!-- обязан отличаться на M/L -->
- **human_ok_spec:** no       <!-- yes (by=human:…, at=…) когда человек подтвердил -->
- **human_ok_plan:** no       <!-- yes (by=…, at=…) | n/a для класса S/M -->
- **shape-oracles:** <weak|cqg-deployed>
- **behavior-oracles:** <weak|tests-present>
- **ci-oracles:** <weak|tooling|deployed>  <!-- §10.4; weak на классе L = нужен waiver -->
  <!-- tooling = CI есть, гейт мержа в репо (merge_guard.sh), серверного нет по тарифу -->
- **worktree:** <../repo-wt-slug|none (S)>
- **hooks:** <not-deployed|cursor|claude|other>
- **blockers:** …
- **waivers:** …
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4
```

Заполненный пример:

```markdown
- **slug:** inbound-dedup
- **stack:** delivery@1.11, cqg@1.1, okf@absent
- **class:** M
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-07-27T10:00:00Z)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **ci-oracles:** deployed
- **worktree:** ../crm-wt-inbound-dedup
- **hooks:** claude
```

### A.3. `delivery/active/spec.md` (скелет)

```markdown
# Spec: <title>

## Problem
…

## Users / stakeholders
…

## In scope
- …

## Out of scope
- …

## Acceptance (observable)
- [ ] …
- [ ] …

## Non-functional
- …

## Open questions
- …
```

### A.4. `delivery/active/tasks.md` (скелет)

```markdown
# Tasks

## Slice 1 — <vertical>
- [ ] T1: …
- [ ] T2: …
- [ ] T3: tests/smoke for slice 1

## Slice 2 — …
- [ ] …
```

### A.5. Hook для `AGENTS.md` / Cursor rule

```markdown
## Canon stack / Agent Delivery Harness

- **Start here:** `AGENT_STACK.md` (order: Delivery → CQG → OKF).
- Process canon: `AGENT_DELIVERY_HARNESS.md`.
- Active delivery: `delivery/active/STATUS.md` — read before coding.
- **Order:** follow delivery phases. Do not oneshot large work.
- **Done:** only when verify oracles pass; never declare done on red.
- Prefer git worktree for class M/L (Delivery §5.1).
- Smoke/evals: `delivery/evals/smoke/` + `active/eval-smoke.md` (Delivery §6).
- Metrics on handoff: Delivery §9 / A.10.
- Hooks if deployed: Delivery §10.
- Skills/prompts: `skills/README.md` (Delivery §11); no inline prompts (CQG).
- Do **not** duplicate code-quality rules here — use `CODE_QUALITY_GATES.md` if present.
- Do **not** invent domain canon — use `knowledge/` / OKF if present.
- Deploy order for missing layers: Delivery → CQG → OKF (see `AGENT_STACK.md`).
```

### A.6. `delivery/README.md`

```markdown
# Delivery contour

Phased AI delivery harness. See root `AGENT_DELIVERY_HARNESS.md`.

- `CONSTITUTION.md` — process principles + thin coding-agent contract
- `active/` — current shipment only
- `archive/` — finished shipments
- `evals/smoke/` — durable product smoke oracles
```

### A.7. `delivery/active/plan.md` (скелет)

```markdown
# Plan: <title>

## Approach
…

## Stack / boundaries
…

## Risks
…

## Rollout / migration
…

## Test / eval strategy
- Link to eval-smoke.md
```

### A.8. `delivery/active/verify-report.md` (скелет)

```markdown
# Verify report

**Date:** YYYY-MM-DD
**Verifier:** <process:ci|agent:NAME|human:NAME>
<!-- Заполнить ОДНИМ значением. Должен отличаться от `builder:` в STATUS (§5.2);
     на M/L совпадение = ошибка delivery_check. -->

## Shape oracles
- [ ] PASS/FAIL — (pre-commit / CQG / tsc / …)

## Behavior oracles
- [ ] PASS/FAIL — tests …

## Product oracles
- [ ] PASS/FAIL — delivery/evals/smoke
- [ ] PASS/FAIL — active/eval-smoke acceptance

## Spec coverage gaps
- …

## Verdict
- [ ] READY FOR HANDOFF
- [ ] NEED CONVERGE (new tasks)
- [ ] BLOCKED
```

### A.9. `delivery/active/eval-smoke.md` + `delivery/evals/smoke/README.md`

`delivery/active/eval-smoke.md`:

```markdown
# Eval smoke — this shipment

Derived from spec acceptance. Run during verify.

- [ ] …
- [ ] …
```

`delivery/evals/smoke/README.md`:

```markdown
# Durable smoke oracles

List 3–10 repo-level checks (command + expected). Example:

| ID | Command | Expected | Timeout |
|---|---|---|---|
| S1 | `curl -sf localhost:8000/health` | HTTP 200 | 10s |
| S2 | `pytest -q` | exit 0 | 120s |

Optional: `run.sh` loops IDs and exits 1 on first failure.
```

`delivery/evals/smoke/run.sh` (скелет):

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
# Добавь реальные команды проекта:
# curl -sf "http://127.0.0.1:8000/health" >/dev/null
# (cd backend && .venv/bin/pytest -q)
echo "TODO: wire smoke commands in delivery/evals/smoke/run.sh" >&2
exit 0   # смени на реальные проверки; bootstrap may keep exit 0 until wired
```

### A.10. Блок метрик (в конец verify-report или archive STATUS)

```markdown
## Harness metrics (this shipment)

| Metric | Value |
|---|---|
| time_to_accepted_spec | … |
| implement_retries | … |
| verify_fails_before_green | … |
| files_touched / loc_diff | … / … |
| rework_after_done | … |
| harness_hardened | yes/no — what changed: … |
| est_token_or_cost | … / n/a |
```

### A.11. Примеры agent hooks (адаптируй под IDE)

Концепт **stop-on-red** (shell, вызывать из Stop / before-finish hook):

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
if [[ -f scripts/delivery_check.py ]]; then
  python scripts/delivery_check.py || {
    echo "delivery_check failed — cannot declare done" >&2
    exit 1
  }
fi
if [[ -x delivery/evals/smoke/run.sh ]]; then
  bash delivery/evals/smoke/run.sh || {
    echo "smoke evals failed — cannot declare done" >&2
    exit 1
  }
fi
# если CQG развёрнут:
# pre-commit run --all-files || exit 1
exit 0
```

Концепт **protect-main** (проверка аргументов shell перед git push):

```bash
#!/usr/bin/env bash
# stdin or $1 = command line; exit 1 to block
cmd="${1:-}"
if echo "$cmd" | grep -Eiq 'push[[:space:]].*(--force|-f).*[[:space:]]+(origin[[:space:]]+)?(main|master)\b'; then
  echo "blocked: force-push to main/master" >&2
  exit 1
fi
exit 0
```

Повесь эти скрипты через механизм hooks своего агента (Cursor / Claude Code /
иной). Детали JSON-схемы — в доке инструмента; контракт поведения — §10.

### A.12. `delivery/STACK-ACCEPTANCE.md`

Результат приёмки стека (AGENT_STACK §6) + разбор случаев, где процедура подвела.
Живёт в `delivery/` (не в `active/` — это про репозиторий, не про поставку).

```markdown
# Stack acceptance

**Date:** YYYY-MM-DD
**Stack:** delivery@… · cqg@… · okf@… (или absent)
**Где лежат каноны:** repo root (коммитятся) | вне репо: <путь> (см. «Остатки»)

## Что развёрнуто

| Слой | Состояние | Примечание |
|---|---|---|
| ① delivery/ | deployed | |
| ② гейты | deployed | хуков: N; адаптация под <язык>: … |
| ③ knowledge/ | deployed / absent | concept'ов с `implementation:`: N |
| ④ CI + гейт мержа | deployed / tooling / weak | merge_guard: да/нет; branch protection: да/нет |

## Карта ролей гейтов

Заполняется по CQG «Применимость → Карта ролей». Инвариант — **роль**, не имя файла:
если роль занял другой скрипт (другой язык/стек), это фиксируется здесь, иначе
таблица CQG §3 и репозиторий расходятся молча.

| Роль | Канонический скрипт | В этом проекте | Статус |
|---|---|---|---|
| … | … | … | как есть / адаптирован / n/a + причина |

## Полнота, не только зелёность

- [ ] `check_gate_coverage.sh` — OK (все гейты подключены)
- [ ] `pre-commit run --all-files` — зелено
- [ ] `stack_selftest.py` — OK (или причина, почему неприменим)
- [ ] Каждый гейт в выводе показал непустое число просканированных файлов

## Остатки (не закрыто — и почему)

| Инвариант | Почему не закрыт | Компенсация |
|---|---|---|
| force-push / обход админом | бесплатный тариф хостинга | правило «мерж только merge_guard.sh» |
| … | | |

## Разбор: где эта процедура подвела

Записывать КАЖДЫЙ случай, когда приёмка показала зелено, а дыра была.
Формат: симптом → корневая причина → что добавлено в harness → как проверено.

### YYYY-MM-DD — <короткое имя>

- **Симптом:** …
- **Причина:** … (не «невнимательность», а механизм: что именно позволило пройти)
- **Усиление:** … (oracle / гейт / шаг процедуры)
- **Проверено воспроизведением:** … (сломал обратно → упало с таким сообщением)
```

---

# Приложение B — `scripts/delivery_check.py`

Фазовый гейт: проверяет наличие каркаса и согласованность STATUS с артефактами.
**Не** заменяет pytest/CQG.

Severity — по документу, а не «всё warning»: то, что §3.3 называет stop-gate
(нет spec/plan/tasks по классу, нет `human_ok_*`, нет verify-report на
converge/handoff, нет `eval-smoke.md` на M/L), даёт **exit 1**. Warning остаётся
для незаполненных мета-полей и режимов `weak`. Незаполненный шаблон STATUS
(`class: <S|M|L>`) — **ошибка**, а не «класс S по умолчанию».

```python
#!/usr/bin/env python3
"""Delivery harness checker.

Usage:
  python scripts/delivery_check.py
  python scripts/delivery_check.py --require-spec

Exit 0 = OK (warnings allowed). Exit 1 = errors.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "delivery"
ACTIVE = DELIVERY / "active"

# §3.4; переопределяются строкой в STATUS: "max_files_touched=40 reason=… by=human:…"
DEFAULT_BREAKERS = {"max_files_touched": 25, "max_loc_diff": 800}

# Процессные артефакты не считаются в breaker'ах: spec/plan/tasks и concept'ы —
# это не blast radius кода, а его описание.
BREAKER_EXCLUDE = ("delivery/", "knowledge/")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def git(*args: str) -> str:
    """git с подавлением ошибок: пустая строка = не смог."""
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    return out.stdout if out.returncode == 0 else ""


def diff_stats(base: str) -> tuple[int, int, int, int] | None:
    """(files, added, deleted, excluded) для base..HEAD; None если ref недоступен."""
    if not git("rev-parse", "--verify", "--quiet", base).strip():
        return None
    merge_base = git("merge-base", base, "HEAD").strip() or base
    files = added = deleted = excluded = 0
    for line in git("diff", "--numstat", f"{merge_base}..HEAD").splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, d, path = parts
        if path.startswith(BREAKER_EXCLUDE):
            excluded += 1
            continue
        files += 1
        added += int(a) if a.isdigit() else 0      # "-" у бинарников
        deleted += int(d) if d.isdigit() else 0
    return files, added, deleted, excluded


def field(status: str, name: str) -> str:
    """Значение поля STATUS: "- **class:** M" -> "M". Inline-комментарий срезается."""
    m = re.search(rf"(?im)^[ \t]*[-*]?[ \t]*\**{name}\**[ \t]*:\**[ \t]*(.*)$", status)
    if not m:
        return ""
    return re.sub(r"<!--.*?-->", "", m.group(1)).strip()


def is_placeholder(value: str) -> bool:
    """Незаполненный шаблон: "<S|M|L>", "S | M | L", "…", пусто.

    Ключевой признак — вертикальная черта: список альтернатив из шаблона не может
    быть выбранным значением. Без этой проверки STATUS с необработанной строкой
    "class: S | M | L" читался бы как class=S, и класс L проезжал бы мимо
    требований spec/plan (§2.2).
    """
    if not value or value in {"…", "...", "-", "TBD", "tbd"}:
        return True
    return "|" in value or value.startswith("<")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-spec", action="store_true")
    ap.add_argument("--require-verify", action="store_true")
    ap.add_argument(
        "--require-ci",
        action="store_true",
        help="fail unless ci-oracles: deployed (§10.4)",
    )
    ap.add_argument(
        "--diff-base",
        metavar="REF",
        help="check circuit breakers §3.4 against REF (e.g. origin/main)",
    )
    args = ap.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    if not (DELIVERY / "CONSTITUTION.md").is_file():
        errors.append("missing delivery/CONSTITUTION.md")
    if not ACTIVE.is_dir():
        errors.append("missing delivery/active/")
        for w in warnings:
            print(f"WARNING: {w}")
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"delivery_check: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1

    status = read(ACTIVE / "STATUS.md")
    if not status:
        errors.append("missing delivery/active/STATUS.md")
    else:
        allowed = {
            "specify",
            "plan",
            "tasks",
            "implement",
            "verify",
            "converge",
            "handoff",
        }
        implement_like = {"implement", "verify", "converge", "handoff"}

        raw_phase = field(status, "phase")
        raw_class = field(status, "class")

        phase_m = (
            re.match(r"(?i)^([a-z_]+)", raw_phase)
            if not is_placeholder(raw_phase)
            else None
        )
        class_m = (
            re.match(r"(?i)^([SML])\b", raw_class)
            if not is_placeholder(raw_class)
            else None
        )
        phase = phase_m.group(1).lower() if phase_m else ""
        klass = class_m.group(1).upper() if class_m else ""

        if is_placeholder(raw_phase):
            errors.append(
                f"STATUS.md: phase not filled in (template placeholder {raw_phase!r})"
            )
        elif not phase:
            errors.append("STATUS.md: missing phase")
        elif phase not in allowed:
            # constitution is project-level file, not active phase
            errors.append(
                f"STATUS.md: unknown phase '{phase}' "
                f"(allowed: {', '.join(sorted(allowed))})"
            )

        if not klass:
            msg = (
                f"STATUS.md: class not resolved (value {raw_class!r}) — "
                "cannot apply §2.2 artifact gates; write exactly one of S|M|L"
            )
            # На specify класс ещё может уточняться; с plan и дальше это блокер:
            # неизвестный класс = молча отключённые требования spec/plan.
            if phase == "specify":
                warnings.append(msg)
            else:
                errors.append(msg)

        spec = ACTIVE / "spec.md"
        plan = ACTIVE / "plan.md"
        tasks = ACTIVE / "tasks.md"
        verify = ACTIVE / "verify-report.md"
        eval_smoke = ACTIVE / "eval-smoke.md"

        if klass in {"M", "L"} and phase in {
            "plan",
            "tasks",
            *implement_like,
        }:
            if not spec.is_file():
                errors.append(f"class {klass} at phase={phase}: missing active/spec.md")

        if klass in {"M", "L"} and phase in implement_like:
            if not plan.is_file():
                errors.append(f"class {klass} at phase={phase}: missing active/plan.md")
            if not tasks.is_file():
                errors.append(f"class {klass} at phase={phase}: missing active/tasks.md")
            # §3.3 называет это stop-gate'ом — значит error, не warning.
            if not field(status, "human_ok_spec").lower().startswith("yes"):
                errors.append(
                    f"class {klass} at phase={phase}: human_ok_spec is not yes "
                    "(stop-gate §3.3)"
                )

        if klass == "L" and phase in implement_like:
            if not field(status, "human_ok_plan").lower().startswith("yes"):
                errors.append(
                    "class L at implement+: human_ok_plan is not yes (stop-gate §3.3)"
                )

        if klass == "S" and phase in implement_like and not tasks.is_file():
            errors.append("class S at implement+: missing active/tasks.md (mini-spec)")

        if not verify.is_file():
            if phase == "verify":
                # Фаза в процессе: отчёт ещё пишется — но выйти из неё без него нельзя.
                warnings.append(
                    "phase=verify: active/verify-report.md not created yet"
                )
            elif phase in {"converge", "handoff"}:
                errors.append(
                    f"phase={phase}: missing active/verify-report.md (DoD §3.2.2)"
                )

        if klass in {"M", "L"} and phase in {"verify", "converge", "handoff"}:
            if not eval_smoke.is_file():
                errors.append(
                    "class M/L at verify+: missing active/eval-smoke.md "
                    "(product oracles are mandatory, §6.2)"
                )

        if phase == "handoff" and verify.is_file():
            vr = read(verify)
            if not re.search(r"READY FOR HANDOFF", vr, re.I):
                errors.append(
                    "phase=handoff: verify-report.md lacks 'READY FOR HANDOFF' verdict"
                )
            # §9.2: метрики снимаются на handoff. Без гейта ритуал не выполняется.
            if "Harness metrics" not in vr:
                errors.append(
                    "phase=handoff: verify-report.md lacks the 'Harness metrics' "
                    "block (§9.2 / A.10) — run: python scripts/delivery_metrics.py "
                    "--base origin/main --write"
                )

        # --- Builder ≠ Verifier (§5.2): не сама независимость, но явное заявление
        # о ней. Настоящее разделение обеспечивает required review в branch
        # protection (CQG §8.5); здесь ловим «сам построил, сам принял».
        if phase in {"verify", "converge", "handoff"} and verify.is_file():
            declared = field(read(verify), "Verifier") or field(status, "verifier")
            builder = field(status, "builder")
            if is_placeholder(declared):
                errors.append(
                    "verify-report.md: Verifier not filled in — Builder must not "
                    "accept own work (§5.2); write process:ci | agent:NAME | human:NAME"
                )
            elif (
                klass in {"M", "L"}
                and not is_placeholder(builder)
                and declared.strip().lower() == builder.strip().lower()
            ):
                errors.append(
                    f"class {klass}: verifier == builder ('{declared}') — §5.2 "
                    "requires a different agent/model/human, or process:ci"
                )

        # --- CI (§10.4): единственный слой, который агент не может обойти локально
        ci = field(status, "ci-oracles").lower()
        waivers = field(status, "waivers").lower()
        if is_placeholder(ci):
            warnings.append(
                "STATUS.md: missing ci-oracles (weak|tooling|deployed) — §10.4"
            )
        elif ci.startswith("weak"):
            if klass == "L" and "ci" not in waivers:
                errors.append(
                    "class L with ci-oracles: weak and no ci waiver in STATUS (§10.4)"
                )
            else:
                warnings.append(
                    "ci-oracles: weak — local gates are bypassable (§10.4); "
                    "Verifier must attach a clean-clone run to verify-report.md"
                )
        # 'tooling' — легитимный режим (гейт мержа в репо, серверного нет по тарифу),
        # а не поддавки: см. §10.4. Недопустим только 'weak'.
        if args.require_ci and not ci.startswith(("deployed", "tooling")):
            errors.append(
                "--require-ci: ci-oracles is neither 'deployed' nor 'tooling'"
            )

        stack = field(status, "stack")
        if is_placeholder(stack) or "delivery@" not in stack:
            warnings.append(
                "STATUS.md: missing stack version "
                "(e.g. 'delivery@1.11, cqg@1.2, okf@absent')"
            )

        # --- Circuit breakers (§3.4): анти-oneshot по объёму поставки
        if args.diff_base:
            limits = dict(DEFAULT_BREAKERS)
            # Одна и та же форма покрывает и override в circuit_breakers,
            # и human waiver: "max_files_touched=40 reason=… by=human:…".
            for m in re.finditer(r"(max_[a-z_]+)[ \t]*=[ \t]*(\d+)", status):
                if m.group(1) in limits:
                    limits[m.group(1)] = int(m.group(2))
            stats = diff_stats(args.diff_base)
            if stats is None:
                warnings.append(
                    f"circuit breakers: ref '{args.diff_base}' unavailable "
                    "(shallow clone? need full history)"
                )
            else:
                n_files, added, deleted, excluded = stats
                net = abs(added - deleted)
                print(
                    f"breakers: files={n_files} net_loc={net} (+{added}/-{deleted}), "
                    f"excluded={excluded} ({'|'.join(BREAKER_EXCLUDE)}), "
                    f"limits={limits}"
                )
                if n_files > limits["max_files_touched"]:
                    errors.append(
                        f"circuit breaker: files_touched {n_files} > "
                        f"{limits['max_files_touched']} — split the PR or add a "
                        "human waiver line to STATUS (§3.4)"
                    )
                if net > limits["max_loc_diff"]:
                    errors.append(
                        f"circuit breaker: net loc_diff {net} > "
                        f"{limits['max_loc_diff']} — split the PR or add a "
                        "human waiver line to STATUS (§3.4)"
                    )

    if args.require_spec and not (ACTIVE / "spec.md").is_file():
        errors.append("--require-spec: active/spec.md missing")
    if args.require_verify and not (ACTIVE / "verify-report.md").is_file():
        errors.append("--require-verify: verify-report.md missing")

    if (ROOT / "CODE_QUALITY_GATES.md").is_file():
        cons = read(DELIVERY / "CONSTITUTION.md")
        if "CODE_QUALITY_GATES" not in cons:
            warnings.append("CQG present but CONSTITUTION.md has no pointer")
    if (ROOT / "OKF_KNOWLEDGE_BUNDLE.md").is_file() or (ROOT / "knowledge").is_dir():
        cons = read(DELIVERY / "CONSTITUTION.md")
        if "OKF" not in cons and "knowledge/" not in cons:
            warnings.append("OKF/knowledge present but CONSTITUTION.md has no pointer")

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    print(f"delivery_check: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

```bash
chmod +x scripts/delivery_check.py
python scripts/delivery_check.py
```

**Обязательно в CI** (§10.4) на ветках с активной поставкой — там же, где гоняются
CQG-гейты (workflow — CQG §8):

```bash
python scripts/delivery_check.py --require-spec              # после фазы specify
python scripts/delivery_check.py --require-ci                # в самой CI-джобе
python scripts/delivery_check.py --diff-base origin/main     # + circuit breakers §3.4
```

Локальный pre-push — та же команда без флагов.

---

# Приложение C — `scripts/delivery_metrics.py`

Считает метрики §9 из git и печатает блок A.10. Нужен потому, что ритуал §9.2
без автосбора не выполняется: заполнять семь полей руками на каждом handoff
никто не будет, а `delivery_check` теперь требует наличие блока (иначе handoff
не закрывается).

**Принцип:** считает то, что git знает; остальное помечает `MANUAL` и **не
выдумывает**. Метрика-догадка хуже отсутствующей — по ней принимают решения об
усилении harness.

```python
#!/usr/bin/env python3
"""Delivery metrics collector (§9 / A.10).

Usage:
  python scripts/delivery_metrics.py --base origin/main
  python scripts/delivery_metrics.py --base origin/main --write

--write вставляет/обновляет блок "## Harness metrics" в
delivery/active/verify-report.md. Exit 0 всегда: это отчёт, не гейт
(гейт на наличие блока — в delivery_check.py на фазе handoff).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "delivery" / "active"
STATUS = ACTIVE / "STATUS.md"
VERIFY = ACTIVE / "verify-report.md"

# Правка любого из этих путей = harness усилен (§5.4): новый oracle / hook / eval.
HARDENING_PATHS = (
    "scripts/lint/",
    "delivery/evals/",
    ".pre-commit-config.yaml",
    ".github/workflows/",
    "scripts/delivery_check.py",
    "scripts/okf_sync_gate.py",
)
DOC_PREFIXES = ("delivery/", "knowledge/")


def git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    return out.stdout if out.returncode == 0 else ""


def first_commit(path: str, needle: str | None = None) -> tuple[str, datetime] | None:
    """Первый коммит, добавивший path (или впервые внёсший needle в path).

    needle — РЕГУЛЯРКА (pickaxe-regex), а не литерал: в STATUS.md поля размечены
    markdown-жирным (`**phase:** handoff`), поэтому поиск литерала "phase: handoff"
    не находил ничего и метрики молча выходили пустыми.
    """
    args = ["log", "--reverse", "--format=%H %aI"]
    if needle:
        args += [f"-S{needle}", "--pickaxe-regex"]
    else:
        args.append("--diff-filter=A")
    args += ["--", path]
    for line in git(*args).splitlines():
        sha, _, iso = line.partition(" ")
        if sha and iso:
            try:
                return sha, datetime.fromisoformat(iso.strip())
            except ValueError:
                return None
    return None


def hours_between(a: datetime, b: datetime) -> str:
    delta = (b - a).total_seconds() / 3600
    return f"{delta:.1f}h" if delta < 48 else f"{delta / 24:.1f}d"


def collect(base: str) -> dict[str, str]:
    m: dict[str, str] = {}

    if not git("rev-parse", "--verify", "--quiet", base).strip():
        m["_error"] = f"ref '{base}' unavailable (shallow clone?)"
        return m
    merge_base = git("merge-base", base, "HEAD").strip() or base

    code_files = doc_files = added = deleted = 0
    hardened: list[str] = []
    for line in git("diff", "--numstat", f"{merge_base}..HEAD").splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, d, path = parts
        if path.startswith(HARDENING_PATHS):
            hardened.append(path)
        if path.startswith(DOC_PREFIXES):
            doc_files += 1
            continue
        code_files += 1
        added += int(a) if a.isdigit() else 0
        deleted += int(d) if d.isdigit() else 0

    m["files_touched / loc_diff"] = (
        f"{code_files} code (+{doc_files} process docs) / "
        f"+{added}/-{deleted} (net {added - deleted:+d})"
    )
    m["commits"] = git("rev-list", "--count", f"{merge_base}..HEAD").strip() or "0"

    spec_created = first_commit("delivery/active/spec.md")
    spec_ok = first_commit("delivery/active/STATUS.md", r"human_ok_spec:\**[ \t]*yes")
    if spec_created and spec_ok:
        m["time_to_accepted_spec"] = hours_between(spec_created[1], spec_ok[1])
    elif spec_created:
        m["time_to_accepted_spec"] = "spec drafted, not yet accepted"
    else:
        m["time_to_accepted_spec"] = "n/a (no spec.md in history — class S?)"

    handoff = first_commit("delivery/active/STATUS.md", r"phase:\**[ \t]*handoff")
    if handoff:
        after = git("rev-list", "--count", f"{handoff[0]}..HEAD").strip() or "0"
        m["rework_after_done"] = f"{after} commit(s) after first phase: handoff"
    else:
        m["rework_after_done"] = "0 (handoff not declared yet)"

    m["harness_hardened"] = (
        f"yes — {', '.join(sorted(set(hardened))[:4])}" if hardened else "no"
    )
    m["implement_retries"] = "MANUAL — fills from session log"
    m["verify_fails_before_green"] = "MANUAL — count red verify runs (CI run list)"
    m["est_token_or_cost"] = "MANUAL / n/a"
    return m


def render(m: dict[str, str], base: str) -> str:
    if "_error" in m:
        rows = f"| (collection failed) | {m['_error']} |"
    else:
        rows = "\n".join(f"| {k} | {v} |" for k, v in m.items())
    return (
        "## Harness metrics (this shipment)\n\n"
        f"<!-- generated by scripts/delivery_metrics.py --base {base} -->\n\n"
        "| Metric | Value |\n|---|---|\n"
        f"{rows}\n\n"
        "MANUAL-поля заполняет агент/человек на handoff. Если "
        "`verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 "
        "добавь oracle/breaker/hook в этой же поставке.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--write", action="store_true", help="upsert block into verify-report.md")
    args = ap.parse_args()

    block = render(collect(args.base), args.base)

    if not args.write:
        print(block)
        return 0

    if not ACTIVE.is_dir():
        print("no delivery/active/ — nothing to write", file=sys.stderr)
        return 0
    text = VERIFY.read_text(encoding="utf-8") if VERIFY.is_file() else "# Verify report\n\n"
    # Заменить существующий блок целиком, чтобы не копить дубли на повторных прогонах.
    pattern = re.compile(r"(?ms)^## Harness metrics.*?(?=^## |\Z)")
    text = pattern.sub("", text).rstrip() + "\n\n" + block
    VERIFY.write_text(text, encoding="utf-8")
    print(f"metrics written to {VERIFY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Активация:

```bash
chmod +x scripts/delivery_metrics.py
python scripts/delivery_metrics.py --base origin/main --write   # на handoff
```

---

## Changelog

| Дата | Изменение |
|---|---|
| 2026-07-26 | Initial: delivery harness as foundation layer; phases; DoD; thin ABC; evals; composition order before CQG/OKF |
| 2026-07-26 | Consistency pass: clarify/analyze as subphases; DoD phase enum; M/L artifact table; oracle weak modes; delivery_check aligned; A.9 eval-smoke |
| 2026-07-26 | Cross-link to `AGENT_STACK.md`; AGENTS hook mentions stack map |
| 2026-07-26 | Gaps 2026: worktree default; eval suite; observability §9; agent hooks §10; skills pointer §11; A.10–A.11 |
| 2026-07-27 | **v1.7**: баннер `⬇ BOOTSTRAP PAYLOAD` перед Приложением A + «стоимость чтения» в §0.3 (канон ~700 строк vs payload ~950; приложения не читаются в обычной работе); самопроверка канонов — `AGENT_STACK.md` §7 |
| 2026-07-27 | **v1.6**: закрыты последние незапринуждённые инварианты — circuit breakers §3.4 механически (`delivery_check --diff-base`, дифф `merge-base..HEAD`, исключены `delivery/**` и `knowledge/**`); Приложение C `delivery_metrics.py` (автосбор §9 из git; MANUAL-поля не выдумываются) + гейт на блок метрик при handoff; Builder≠Verifier через `builder:`/`Verifier:` + указатель на required review; §0.1a — CI объявлен сквозным слоем ④ (снята размытость границы CQG); шаблон verify-report переведён на плейсхолдер |
| 2026-07-27 | **v1.5** (review pass): §10.4 CI как необходимый слой (локальные гейты обходятся) + DoD §3.2.3 / §3.1 «где гоняются oracles»; canon version + `stack:` в constitution/STATUS; STATUS-шаблон переведён на плейсхолдеры `<a\|b>` (незаполненный STATUS больше не читается как `class: S`); `delivery_check.py` — stop-gates §3.3 подняты из warning в error, добавлены `ci-oracles` / `stack` / `--require-ci`; фазовые цепочки приведены к §2.1; ABC-ссылка сверена и подписана названием |

---

*Конец. Соседние каноны (подключать **после** этого файла):  
`CODE_QUALITY_GATES.md`, `OKF_KNOWLEDGE_BUNDLE.md`.  
Product-agent ABC (исследование): https://arxiv.org/abs/2602.22302*
