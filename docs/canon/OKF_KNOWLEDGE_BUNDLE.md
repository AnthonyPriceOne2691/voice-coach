# OKF Knowledge Bundle — канон для агентного knowledge-контура

> **Карта канонов (вход для агента):** [AGENT_STACK.md](AGENT_STACK.md)  
> **Слой контура:** ③ knowledge / канон домена — после
> [AGENT_DELIVERY_HARNESS.md](AGENT_DELIVERY_HARNESS.md) и
> [CODE_QUALITY_GATES.md](CODE_QUALITY_GATES.md).  
> §0 ниже — **первый шаг внутри развёртывания OKF** (сверка upstream SPEC),
> не «первый файл всего набора». Начинай с
> [AGENT_STACK.md](AGENT_STACK.md). Как вести фичу — Delivery; форма кода — CQG.

**Canon version:** `okf@1.17` · 2026-08-13 (Changelog — в конце файла). Не путать с
`Pinned OKF version` (§0.1) — это версия *upstream-спеки*, а `okf@1.12` — версия
*этого канона развёртывания*. Обе записываются в проект: `okf_version` во frontmatter
корневого `index.md`, канон-версия — в `delivery/CONSTITUTION.md` / `STATUS.md` (`stack:`).

**Самодостаточный универсальный документ.** Кладёшь этот один файл в проект — агент
разворачивает OKF-контур (bundle, index/log, seed-concept’ы, librarian-protocol,
hook в `AGENTS.md` / Cursor rule). Ничего больше копировать не нужно.

> **Язык:** проза — русский, идентификаторы / пути / frontmatter / код — английские.
>
> **Базовая спецификация:** Open Knowledge Format **v0.2** (Google Cloud /
> `GoogleCloudPlatform/knowledge-catalog`). Этот файл — **операционный канон
> развёртывания** поверх спеки: сжатый нормативный минимум + project profile
> для software-репозиториев + протокол агента-библиотекаря + шаблоны + два
> гейта (формат bundle и синхронизация канона с кодом).
>
> **Связанные каноны:** [AGENT_STACK.md](AGENT_STACK.md) ·
> [AGENT_DELIVERY_HARNESS.md](AGENT_DELIVERY_HARNESS.md) ·
> [CODE_QUALITY_GATES.md](CODE_QUALITY_GATES.md).

---

## ⚠️ 0. ОБЯЗАТЕЛЬНЫЙ ПЕРВЫЙ ШАГ (до развёртывания *этого* OKF-контура)

**Перед тем как создавать файлы, править структуру или «разворачивать контур»,
агент ОБЯЗАН:**

1. **Открыть актуальную спецификацию OKF на GitHub:**
   - Spec (raw / canonical):  
     https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md
   - Spec (readable on GitHub):  
     https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
   - Репозиторий (примеры bundles, agents):  
     https://github.com/GoogleCloudPlatform/knowledge-catalog
2. **Прочитать заголовок версии** в upstream (`**Version X.Y**`) и сравнить с
   полем `Pinned upstream` ниже и с `okf_version` в корневом `index.md` проекта
   (если bundle уже есть).
3. **Если upstream новее или расходится** с этим документом (обязательные поля,
   reserved filenames, семантика links/index/log, conformance, breaking changes):
   - **сначала обновить этот файл** (`OKF_KNOWLEDGE_BUNDLE.md`) — §2 и затронутые
     шаблоны/скрипты — под новую спеку;
   - зафиксировать в §0.1 дату сверки и новую pinned-версию;
   - **только после этого** разворачивать или мигрировать контур в проекте.
4. **Если сети нет** и upstream недоступен — разворачивать по этому файлу
   допустимо, но в корневом `log.md` bundle’а сразу записать:
   `**Warning**: upstream SPEC not fetched; deploy based on pinned snapshot only.`
   При первой возможности — шаг 1–3.

**Инвариант:** этот документ — удобный bootstrap для агента, **не** замена
upstream SPEC. Порядок при конфликте: (1) правь этот канон под upstream,
(2) только потом пиши/мигрируй bundle. Пока канон не обновлён — для
формата опирайся на upstream SPEC, не на устаревший абзац здесь.

### 0.1. Pinned upstream (сверка)

| Поле | Значение |
|---|---|
| **Pinned OKF version** | `0.2` |
| **Источник правды** | https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md |
| **Дата последней сверки этого файла** | 2026-07-26 |
| **Что делать при minor bump upstream** | Добавить optional fields / conventions в §2; шаблоны; не ломать существующие bundles |
| **Что делать при major bump upstream** | Breaking: обновить §2, §5 deploy, Приложения; миграционный note в §6 |

### 0.2. Как пользоваться остальным документом

| Секция | Когда читать |
|---|---|
| §1 Философия | Всегда — зачем OKF, vs RAG, границы |
| §2 Спека v0.2 (сжато) | Норматив для чтения/записи concept’ов |
| §3 Project profile | Наш слой для software-репо (таксономия, размеры, семьи) |
| §4 Librarian protocol | Правила агента при изменении кода/знаний |
| §5 Развёртывание | Команда агенту + ручной чеклист |
| §6 Миграция с плоского `docs/` | Легаси → ratchet, без big-bang rewrite |
| §7 Сопровождение | Синхронизация с upstream, freshness |
| Приложение A | Шаблоны файлов (дословно) |
| Приложение B | `okf_validate.py` — формат bundle (в CI) |
| Приложение C | `okf_sync_gate.py` — гейт code↔canon + freshness (в CI) |

**Стоимость чтения.** Канон — §0–§7 (≈800 строк). Приложения — **bootstrap
payload** (≈770 строк): при развёртывании и при создании concept'а по шаблону.
Чтобы **ответить на доменный вопрос**, приложения не нужны вовсе — нужен
`knowledge/index.md` проекта.

---

## 1. Философия

### 1.1. Зачем OKF

Три года дефолтом на enterprise-контекст был RAG: chunk → embed → cosine.
Это хорошо для **широкого неструктурированного** архива. Плохо для
**канонических истин** (определение метрики, контракт API, HITL-политика,
схема гейта): chunking ломает структуру, retrieval вероятностный, embeddings
дрейфуют.

OKF формализует паттерн **LLM Wiki** (Karpathy и др.): знание — это
**git-native дерево Markdown + YAML frontmatter**, которое агент
**обходит по явным ссылкам**, а не угадывает similarity.

### 1.2. Три опоры (операционный фрейминг, не термины SPEC)

Официальная спека формулирует goals/non-goals; ниже — сжатый фрейм для
агента (совпадает по смыслу с мотивацией SPEC §1 + паттерном LLM Wiki):

1. **Format over platform.** Нет обязательного SDK, cloud-аккаунта, registry.
   `cat` + `git` достаточно. Bundle = директория.
2. **Agent as librarian.** Knowledge corpus **непрерывно пишется и
   поддерживается** агентами; frontmatter фиксирует provenance / trust /
   lifecycle (SPEC §5). Люди плохо держат wiki в актуальном состоянии —
   агенты как раз хороши в bookkeeping (cross-links, index, log).
3. **Deterministic graph.** Связи — обычные markdown-ссылки
   (`[customers](/tables/customers.md)`), не vector nearest-neighbor.
   Path файла (без `.md`) = **Concept ID** (SPEC §2).

### 1.3. Hybrid: OKF + RAG

| Слой | Что хранит | Как достаём |
|---|---|---|
| **OKF bundle** | Канон: метрики, схемы, ADR, политики, runbooks, design-решения | `index.md` → link traversal |
| **RAG / search** | Архив: PDF, старые тикеты, сырые логи, exploratory | embeddings / full-text |

Роутер (агент или человек): high-stakes / «как у нас принято» → OKF;
«когда-то кто-то писал / найди похожее» → RAG.

### 1.4. Non-goals (из спеки + наш акцент)

- Не фиксируем единую таксономию `type` на весь мир (спека) — но **project
  profile (§3)** задаёт рекомендованный набор для software-репо.
- Не предписываем storage/serving/query runtime.
- Не заменяем OpenAPI / Protobuf / Avro — OKF **ссылается** на них через
  `resource` и links.
- Не заменяем продукт-доки для людей в Confluence — OKF = **agent+human
  канон в git**; при желании Confluence генерируется из bundle.

---

## 2. Спека OKF v0.2 — нормативный минимум

Ниже — сжатое, достаточное для работы агента изложение. При сомнении —
upstream SPEC (§0). Нумерация секций здесь **локальная** (`§2.x`);
отсылки вида «SPEC §N» — к GitHub-спеке.

### 2.1. Термины (SPEC §2)

| Термин | Смысл |
|---|---|
| **Knowledge Bundle** | Самодостаточное дерево concept-документов; единица поставки |
| **Concept** | Одна единица знания = один `.md` файл |
| **Concept ID** | Путь файла внутри bundle **без** суффикса `.md` |
| **Frontmatter** | YAML между `---` в начале файла |
| **Body** | Всё после frontmatter |
| **Link** | Стандартная markdown-ссылка между concept’ами |
| **Actor** | Кто сделал действие: `<agent>/<model>`, `human:<id>`, `process:<name>` |

### 2.2. Структура bundle (SPEC §3)

```
<path/to/bundle>/
  index.md                 # optional; progressive disclosure (корень)
  log.md                   # optional; хронология изменений
  <concept>.md
  <subdir>/
    index.md
    log.md
    <concept>.md
    ...
```

Распространение: git (рекомендуется), tarball/zip, или subdirectory в
большем репо.

**Reserved filenames** (на любом уровне; **не** concept’ы):

| Файл | Назначение |
|---|---|
| `index.md` | Листинг директории (SPEC §8) |
| `log.md` | История обновлений (SPEC §9) |

Все остальные `.md` — concept documents.

### 2.3. Concept document (SPEC §4)

Две части: YAML frontmatter + markdown body.

**Обязательно:**

- `type` — непустая строка. Центрального registry типов **нет**. Consumers
  MUST терпеть неизвестные `type`.

**Рекомендуется (SPEC §4.1 Recommended — не обязательны):**

- `title` — display name (иначе — из имени файла)
- `description` — одно предложение (для index / preview)
- `resource` — URI underlying asset (нет у чисто абстрактных идей)
- `tags` — список коротких строк

`type` — единственный always-required ключ; concept только с `type` уже
fully conformant (SPEC §11).

**Расширения:** любые доп. ключи разрешены. Consumers SHOULD сохранять
unknown keys; MUST NOT reject bundle из‑за них.

**Legacy v0.1 (если встретится в старых текстах/примерах):** поле
`timestamp` superseded → `generated.at`; body `# Citations` superseded →
`sources` (SPEC §13). Consumers MAY читать legacy; **новые** concept’ы
писать только в форме v0.2.

**Body:** обычный markdown. Producers SHOULD предпочитать структуру
(заголовки, списки, таблицы, fenced code), а не сплошную прозу.

Условные заголовки (когда применимо):

| Heading | Назначение |
|---|---|
| `# Schema` | Поля/колонки ассета |
| `# Examples` | Примеры использования |
| `# Computation` | Тело Attested Computation (SPEC §10) |

### 2.4. Provenance, trust, lifecycle (SPEC §5) — optional families

Отсутствие семейства **имеет смысл** (например unverified ≠ reject).

**`sources`** — из чего выведен concept. Каждый entry: `resource` обязателен
внутри entry; опц. `id`, `title`, credibility signals (`author`,
`usage_count`, `last_modified`). Per-claim attribution — markdown footnotes
с label = `sources[].id` (не позиционный индекс).

**`generated`:** `{ by: <actor>, at: <ISO-8601> }` — кто/когда написал
текущее содержимое. Если блок `generated` присутствует, **`by` обязателен**
внутри него (SPEC §5.2); `at` — ISO 8601 datetime последней смысловой правки.

**`verified`:** список `{ by, at }` (или один bare mapping = one-element
list — consumers MUST так трактовать). Кто подтвердил против
sources/`resource`. Trust tiers:

| Сигнал | Tier |
|---|---|
| нет `verified` | **unverified** |
| только non-`human:` | **machine-confirmed** |
| есть `human:` | **human-reviewed** |

**`status`:** `draft` | `stable` | `deprecated` (absent ⇒ `stable`).

**`stale_after`:** абсолютная дата `YYYY-MM-DD`; stale когда `today >= stale_after`.

### 2.5. Cross-linking (SPEC §6)

Два вида ссылок:

1. **Absolute (bundle-relative)** — начинается с `/`, от корня bundle.
   **Рекомендуемая** форма (стабильна при переносах внутри subdir):

   ```markdown
   See the [customers table](/tables/customers.md).
   ```

2. **Relative** — обычный relative path:

   ```markdown
   See the [neighbor](./other.md).
   ```

Вид отношения (depends-on, joins-with, …) — в окружающей прозе, не в
типе ссылки. **Broken links не делают bundle невалидным** (могут быть
ещё не написанные concept’ы).

Path-valued fields (`resource`, `sources[].resource`, …): absolute URL,
bundle-relative `/…`, или relative path.

Convention: `references/` — зеркало внешних материалов / executor /
attester кода как first-class concepts (не требование).

**Не путать с Obsidian `[[wiki-links]]`:** в OKF v0.2 — **стандартные**
markdown links. Wiki-links в body — вне спеки (можно как локальный soft
alias, но канон записи — SPEC §6).

### 2.6. Actors (SPEC §7)

- `<agent_or_tool>/<model_or_version>` — например `cursor_agent/composer`
- `human:<id>` — человек
- `process:<name>` — автоматический процесс

Trust tiers ключуются по префиксу `human:` — producers MUST использовать
его для hand-authored / human-confirmed.

### 2.7. `index.md` (SPEC §8)

- MAY в любой директории.
- **Без frontmatter**, кроме одного исключения: **bundle-root** `index.md`
  MAY содержать `okf_version` (SPEC §12).
- Body: секции с heading + bullet list ссылок с short description.
- Producers MAY генерировать index автоматически; consumers MAY
  синтезировать на лету, если файла нет.

Пример корневого index:

```markdown
---
okf_version: "0.2"
---

# Product

* [LinkBuilder overview](product/overview.md) - what the system does

# Engineering

* [Gates](engineering/gates/) - donor quality gate chain
* [Outreach](engineering/outreach/) - AI outreach policies and pipelines
```

### 2.8. `log.md` (SPEC §9)

Плоский список, **newest first**, даты `YYYY-MM-DD`:

```markdown
# Directory Update Log

## 2026-07-26
* **Creation**: Established bundle root and seed concepts.
* **Update**: Added [HITL policy](/engineering/outreach/hitl-policy.md).

## 2026-07-20
* **Initialization**: Created foundational directory structure.
```

Convention для bold-глаголов: `**Creation**`, `**Update**`,
`**Deprecation**` (не жёсткое требование спеки).

### 2.9. Attested Computation (SPEC §10) — кратко

Отдельный concept `type: Attested Computation` с sanctioned способом
**вычислить** значение (не только описать).

Ключевые поля: `runtime` (REQUIRED для этого type), `parameters`,
опц. `computation` (path) или inline `# Computation`, `executor`,
`attester`.

- **`verified`** = определение всё ещё совпадает с политикой (в bundle).
- **Attestation** = конкретный *run* сделан sanctioned способом (runtime
  artifact, **не** хранится в bundle).

Для MVP software-bundle (§5) Attested Computation **не обязателен**.
Включать, когда появляются high-stakes числа/SQL, которые агент не должен
импровизировать.

### 2.10. Conformance (SPEC §11)

Bundle **conformant OKF v0.2**, если:

1. Каждый non-reserved `.md` имеет parseable YAML frontmatter.
2. В каждом frontmatter есть non-empty `type`.
3. Если есть `index.md` / `log.md` — они следуют структуре SPEC §8 / §9.

Consumers MUST NOT reject из‑за: missing optional fields, unknown `type`,
unknown keys, broken links, missing `index.md`.

### 2.11. Versioning (SPEC §12)

- Minor — backward-compatible additions.
- Major — breaking.
- Bundle MAY declare `okf_version: "0.2"` в root `index.md`.

---

## 3. Project profile — software repository (наш слой)

Спека намеренно не фиксирует таксономию. Этот профиль — **рекомендация
для кодовых репозиториев** (backend/frontend/CRM/automation). Не часть
OKF conformance; нарушение профиля ≠ non-conformant upstream, но **нарушение
для агента в проекте, куда положен этот канон**.

### 3.1. Где лежит bundle

| Переменная / соглашение | Дефолт | Смысл |
|---|---|---|
| Bundle root | `knowledge/` | OKF tree в корне репо |
| Legacy docs (если есть) | `docs/` | Плоский архив; мигрирует ratchet’ом (§6) |
| Этот канон | `OKF_KNOWLEDGE_BUNDLE.md` (корень репо) или путь, указанный человеком | Bootstrap |

Альтернативы (`docs/okf/`, `brain/`, `.okf/`) — ок, если путь bundle явно
зафиксирован в `AGENTS.md` / Cursor rule и упомянут в body корневого
`index.md` (у `index.md` нет поля `description` в frontmatter — там
допустим только `okf_version`).

### 3.2. Рекомендуемые `type` values

| `type` | Когда |
|---|---|
| `Overview` | Обзор продукта / домена (мало; чаще index) |
| `Design` | Дизайн фичи / рефакторинга (канон «что строим») |
| `ADR` | Architecture Decision Record (принято/отклонено) |
| `Policy` | Продуктовые/безопасность/HITL правила |
| `Runbook` | Ops: деплой, rollback, инцидент |
| `Playbook` | Пошаговый сценарий (oncall, ручной процесс) |
| `Schema` | Модель данных, API contract summary, таблицы |
| `Metric` | Бизнес/продуктовая метрика + определение |
| `Reference` | Ссылка на внешний канон / inventory |
| `Pipeline` | Описание пайплайна / state machine |
| `Attested Computation` | Sanctioned compute (SPEC §10) |

Неизвестные типы — допустимы; для нового домена лучше **описательный**
type, чем `misc`.

### 3.3. Атомарность concept’а

| Правило | Порог / суть |
|---|---|
| **Один concept = одна тема** | Не смешивать design + полный changelog калибровок + ops в одном файле |
| **Soft size** | Concept body ideally **≤400 строк**; signal to split при **>600** |
| **Hard smell** | **>1000 строк** / **>80KB** — почти наверняка нужен split (family или subdir) |
| **Document family** | Связанные куски: `foo.md` (Design) + `foo-risks.md` + `foo-ops.md` с взаимными links и общей секцией «Document family» в body |
| **Эпические design-логи** | Живут как `status: deprecated` snapshot **или** вне bundle в `docs/archive/`; канон — выжимка |

### 3.4. Типовое дерево для software-репо

```
knowledge/
  index.md
  log.md
  product/
    index.md
    overview.md
  engineering/
    index.md
    architecture/
      index.md
      queues-rq-vs-celery.md          # ADR
    gates/
      index.md
      overview.md
      gate-a-prospecting.md
      gate-b-prepayment.md
    outreach/
      index.md
      hitl-policy.md
      inbound-pipeline.md
    prospecting/
      index.md
  ops/
    index.md
    deploy-single-vm.md
  references/
    index.md
```

Домены — под проект. Пустые папки без `index.md` не оставлять.

### 3.5. Frontmatter-профиль проекта (поверх спеки)

Минимум для **нового** concept в проекте с этим каноном:

```yaml
---
type: Design
title: Human title
description: One sentence.
status: draft          # draft | stable | deprecated
tags: [domain-tag]
generated:
  by: cursor_agent/composer
  at: 2026-07-26T12:00:00Z
# Карта реализации — обязательна, если concept описывает поведение кода.
# Её читает гейт okf_sync_gate.py (Приложение C): тронул путь — тронь concept.
# implementation: [] означает «сознательно не привязан к коду» (глоссарий, Reference).
implementation:
  - backend/features/<area>/
# optional but encouraged:
# resource: https://youtrack.example/issue/PROJ-123
# verified: { by: human:owner, at: 2026-07-26T15:00:00Z }
# stale_after: 2026-10-01        # обязателен для high-stakes Policy/Metric (§7.2)
# sources: [...]
---
```

| Поле | Кто проверяет |
|---|---|
| `type`, frontmatter вообще | `okf_validate.py` (error) |
| `implementation:` vs изменённый код | `okf_sync_gate.py` (error) |
| `stale_after` в прошлом | `okf_sync_gate.py --check-stale` (weekly) |
| `status`, `title`, `description`, `generated` | ревью + librarian checklist §4.3 |

### 3.5a. Карта репозитория — concept, а не документация

Bundle держит канон **домена** и молчит про канон **репозитория**: где входные
точки, где что лежит, где грабли. Поэтому каждая сессия переоткрывает структуру
заново — самая дешёвая из всех потерь и самая незамечаемая, потому что выглядит
как «агент осваивается».

Лечится одним concept'ом: `knowledge/references/repo-map.md`, `type: Reference`.
Ключевое — **не текст, а два поля**, иначе через месяц это устаревший файл,
которому верят.

**① `implementation:` — только структурные якоря.** Здесь легко убить гейт:
если вписать `backend/`, `okf_sync_gate` будет требовать правки карты на каждой
поставке, а по Delivery §4.3b такой гейт сначала бесит, потом его снимают. Область
обязана совпадать с тем, что карта **утверждает**:

| Вписывать | Не вписывать |
|---|---|
| Входные точки: `main.py`, `app.py`, `cli.py`, `manage.py` | Модули фич — их тело меняется, структура нет |
| Проводку: `router.py`, `urls.py`, `container.py`, `di.py` | Тесты |
| Манифесты: `pyproject.toml`, `package.json` (новая зависимость меняет «где что живёт») | Миграции |
| `__init__.py` пакетов верхнего уровня, если они задают слои | Конфиги окружений |

Критерий одной фразой: **тронули этот файл — предложение в карте стало ложным?**
Если нет, файла в `implementation:` быть не должно.

**② `stale_after` — потому что самая ценная часть карты негейтируема.** «Где
грабли» не привязано ни к одному пути: грабли перестают быть граблями молча,
когда кто-то починил причину. Ни один гейт этого не увидит, поэтому карта живёт
по §7.2 как high-stakes concept: `stale_after` +90 дней, дальше
`--check-stale` требует перечитать.

```yaml
---
type: Reference
title: Repository map
description: Где входные точки, где что лежит, где грабли.
status: stable
tags: [repo, onboarding]
stale_after: 2026-10-27        # §7.2 — «грабли» гейтом не покрываются
implementation:                # ТОЛЬКО структурные якоря, см. таблицу выше
  - backend/main.py
  - backend/features/__init__.py
  - pyproject.toml
---
```

Тело — три раздела, и третий главный:

| Раздел | Что в нём | Чем полезен |
|---|---|---|
| **Входные точки** | Как запускается прод, как тесты, как воркеры | Снимает вопрос «откуда дёргается этот код» |
| **Где что лежит** | Слои и их границы, куда класть новый модуль | Снимает спор о размещении в каждой поставке |
| **Грабли** | Что выглядит рабочим и не работает; почему так, а не иначе | Единственный раздел, который **нельзя** вывести из кода |

Читается **до** implement — правило в чеклисте [AGENT_STACK.md](AGENT_STACK.md) §3.
Это парная вещь к Delivery §2.2a: индекс архива отвечает «на чём мы уже
спотыкались в этом модуле», карта — «как этот репозиторий вообще устроен».

**Чего не даёт.** Гейт заставляет **тронуть** карту при смене якоря, а не описать
изменение верно: правка в одну строку с новым `generated.at` создаёт вид
пересмотра, которого не было (тот же случай, что в Delivery §4.3a). Против этого
работает только `verified: by: human:` на карте — и он честен ровно до даты рядом.

### 3.5b. Runbook на каждый алерт (post-merge половина)

`type: Runbook` есть в таблице §3.2 с самого начала, но не было сказано, **когда
он обязателен**. Ответ из Delivery §13.3: на верхней ступени наблюдаемости
**каждый алерт обязан иметь runbook**. Алерт без него — не усиление, а ухудшение:
он будит человека в три часа ночи и не помогает, и после второго раза его
отключают вместе с полезной частью.

Минимум в теле:

| Раздел | Зачем |
|---|---|
| **Симптом** | Что именно сработало и как это выглядит в мониторинге |
| **Как проверить** | Запрос/команда, отличающая реальную проблему от шума |
| **Как откатить** | Конкретная команда или ссылка на revert-процедуру |
| **Кого звать** | Если откат не помог — имя роли, не «команду» |

Обязателен `stale_after` (§7.2): **runbook стареет быстрее кода**, и процедура
откатa, написанная под прошлую архитектуру, вредна активно — она уверенно ведёт
не туда. Гейта на «у каждого алерта есть runbook» нет и не может быть: список
алертов живёт в мониторинге, вне репозитория, и связать его механически нечем.
Это открытый остаток, а не покрытая область — так и записано в Delivery §13.3.

### 3.6. Что класть в OKF vs что оставить снаружи

| В bundle (канон) | Вне bundle / RAG / archive |
|---|---|
| Актуальные design-решения | Сырые отчёты прогонов на 300KB |
| ADR, политики, runbooks | Одноразовые regression dumps |
| Определения метрик и гейтов | Полные CSV локаций / coverage XML |
| Контракты поведения агентов | Стенограммы калибровок (выжимка → Metric/Design) |
| Опц. `type: Reference` на стабильный skill | Тела промптов / `skills/**` (каталог в репо; см. Delivery §11) |
| — | Eval smoke scripts (`delivery/evals/`) — это Delivery, не OKF |

---

## 4. Librarian protocol (агент-библиотекарь)

### 4.1. Когда агент **обязан** трогать bundle

| Событие | Действие |
|---|---|
| Новая фича / рефакторинг с design-фазой | Создать `type: Design` (и family при необходимости) **до или вместе** с кодом |
| Принято архитектурное решение | `type: ADR`, `status: stable`, link из related Design |
| Изменён инвариант гейта / HITL / контракта | Обновить соответствующий concept в **том же PR/сессии** — **прибито** `okf_sync_gate.py` (Приложение C) для concept'ов с `implementation:` |
| Concept устарел | `status: deprecated` + pointer на successor link; запись в `log.md` |
| Создан/переименован/удалён concept | Обновить ближайший `index.md` + `log.md` scope |
| Человек явно попросил «внеси в knowledge» | Сделать; не ждать |

### 4.2. Правила записи

1. **Сначала index.** Не знаешь куда писать — открой root `index.md`,
   спустись по секциям (progressive disclosure). Не создавай orphan
   concept без ссылки из index родителя.
2. **Links bundle-relative с `/`** для меж-concept ссылок (§2.5).
3. **Обновляй `generated.at`** при смысловом изменении body/frontmatter.
4. **Не стирай историю молча.** Deprecate > delete. Delete только если
   файл ошибочный/пустой и на него нет входящих ссылок (или ссылки починены).
5. **Не дублируй канон.** Один факт — один concept; остальные ссылаются.
6. **Код — источник правды для поведения; OKF — для intent/контракта.**
   Если код и concept разошлись — либо чини код, либо обновляй concept
   и пиши в log почему; молчаливый drift запрещён.
7. **Attested Computation:** агент MAY подставлять только `parameters`
   values; MUST NOT переписывать sanctioned computation (SPEC §10.3).

### 4.3. Минимальный checklist после правок bundle

- [ ] У всех новых `.md` (кроме reserved) есть `type`
- [ ] Parent `index.md` содержит ссылку
- [ ] Scope `log.md` обновлён (дата сегодня, newest first)
- [ ] Cross-links ведут на существующие пути **или** явно TODO-concept
- [ ] `generated` актуален
- [ ] У concept'ов, описывающих поведение кода, заполнено `implementation:`
      (иначе гейт синхронизации их не видит — Приложение C)
- [ ] Если менялся high-stakes канон — запросить / отметить `verified`
      (`human:` когда человек подтвердил)

### 4.4. Hook для `AGENTS.md` / Cursor rule

Агент при работе в репо с OKF **читает** root `knowledge/index.md` (или
путь bundle) **до** догадок из памяти/RAG по каноническим вопросам.
Фрагмент для вставки — Приложение A.4.

---

## 5. Развёртывание

### 5.0. Preflight (ещё раз)

Выполнить **§0** (fetch upstream SPEC → diff → обновить этот канон при
расхождениях). Без этого шага deploy считается неполным.

### 5.1. Способ 1 — через агента (рекомендуется)

Положи `OKF_KNOWLEDGE_BUNDLE.md` в корень проекта (или укажи путь) и дай
команду:

> «Сначала открой актуальную OKF-спеку:
> https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
> (raw: https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md).
> Сравни с `OKF_KNOWLEDGE_BUNDLE.md`: если upstream новее или есть
> расхождения — обнови канон-файл, затем продолжай.
> После сверки разверни OKF-контур по канону: создай bundle
> `knowledge/` (или согласованный путь), корневой `index.md` с
> `okf_version` во frontmatter, корневой `log.md`, минимальные
> domain-`index.md` (без frontmatter), 3–8 seed-concept’ов по реальной
> структуре проекта, вставь librarian-hook в `AGENTS.md` или
> `.cursor/rules/`. Легаси `docs/` не переписывай big-bang — только
> каркас + правила §6. Положи `scripts/okf_validate.py` (Приложение B) и
> `scripts/okf_sync_gate.py` (Приложение C), заполни `implementation:` хотя бы
> у concept'ов, описывающих поведение кода, и добавь оба скрипта в CI-джобу
> `delivery` (CQG §8.3) плюс weekly-workflow `--check-stale` (§7.2).»

### 5.2. Способ 2 — вручную

1. Создай `knowledge/` + скопируй шаблоны A.1–A.3.
2. Проставь `okf_version: "0.2"` в root `index.md`.
3. Нарежь 2–4 домена под проект (`engineering/`, `ops/`, …) с `index.md`.
4. Напиши 3–8 seed concepts (overview продукта, главный ADR или pipeline,
   одна policy, один runbook) — лучше мало и правда, чем пустые заглушки.
5. Вставь A.4 в `AGENTS.md` / Cursor rule.
6. Приложение B → `scripts/okf_validate.py` и Приложение C →
   `scripts/okf_sync_gate.py`; прогон на bundle, затем оба в CI (CQG §8.3).
7. Первый commit: `docs(okf): bootstrap knowledge bundle v0.2`.

### 5.3. Seed-стратегия

Не импортируй 100 файлов из старого `docs/` в первый день.

1. **Каркас** (index/log/domains).
2. **Канон, без которого агент врёт** (HITL, очереди, главные гейты).
3. Дальше — ratchet (§6): тронул тему → перенёс/сжал в concept.

### 5.4. Definition of Done для bootstrap

- [ ] Upstream SPEC сверен (§0), pinned version актуальна
- [ ] `knowledge/index.md` с `okf_version`
- [ ] `knowledge/log.md` с записью Initialization
- [ ] ≥1 domain subdir с `index.md`
- [ ] ≥3 concept’а с валидным frontmatter `type`
- [ ] Librarian-hook в agent instructions
- [ ] `okf_validate.py` exit 0 — и **подключён в CI** (Delivery §10.4 / CQG §8):
      шаг `python scripts/okf_validate.py knowledge/` в той же джобе, что
      `delivery_check.py`. Иначе bundle тихо разъезжается с каноном:
      orphan-concept’ы и файлы без `type` никто не поймает
- [ ] `okf_sync_gate.py` (Приложение C) положен и подключён в CI; хотя бы у
      **одного** concept'а заполнено `implementation:` — иначе гейт инертен
- [ ] `--check-stale` повешен на периодический прогон (§7.2)
- [ ] `knowledge/references/repo-map.md` создан (§3.5a): `type: Reference`,
      `implementation:` **только структурные якоря** (входные точки, проводка,
      манифесты — не модули фич), `stale_after` выставлен. Раздел «Грабли»
      непустой: он единственный, который нельзя вывести из кода
- [ ] Версия канона (`okf@1.12`) записана в `stack:` STATUS/constitution

---

## 6. Миграция с плоского `docs/` (ratchet)

Как у code-quality baseline-ratchet: **не** переписываем всё разом.

### 6.1. Правила

1. **Новое знание** (design фичи с даты введения OKF) — **только** в bundle.
2. **Легаси `docs/*.md`** остаются readable; в root index можно секция
   `Legacy docs` со ссылкой на `../docs/README.md` (вне bundle path —
   обычная relative link из репо).
3. **При касании** легаси-темы в работе:
   - выдели канонический concept (≤400–600 строк выжимки);
   - положи в правильный subdir с frontmatter;
   - в старом файле сверху: banner «Canonical: `/path/in/bundle.md`» +
     `status` смысла «archive»;
   - обнови index + log.
4. **Эпики >100KB** — не копировать целиком. Split: Design / Risks / Ops /
   Calibration-log (log можно оставить в `docs/archive/`).
5. **`DOCUMENTATION_COMPENDIUM` / гигантские dumps** — не bundle material.
   Index bundle **заменяет** их роль как карты.
6. **Снимок прогресса:** в `knowledge/log.md` или `knowledge/migration.md`
   (`type: Reference`) вести счётчик «migrated concepts / remaining epics».

### 6.2. Banner для легаси-файла

```markdown
> **Canonical OKF concept:** [`/engineering/gates/overview.md`](../knowledge/engineering/gates/overview.md)
> This file is an archive snapshot; do not extend. Update the OKF concept instead.
```

---

## 7. Сопровождение

### 7.1. Синхронизация с upstream

| Триггер | Действие |
|---|---|
| Старт любого OKF-deploy / крупной миграции | §0 fetch + diff |
| Раз в квартал / при новости про OKF | §0 сверка |
| Upstream major bump | Обновить канон, затем migration note для bundles |

После сверки обновить таблицу §0.1 (`Pinned OKF version`, дата).

### 7.2. Freshness внутри проекта

- High-stakes Policy/Metric — ставить `stale_after` (например +90 дней).
- Агент при чтении stale concept — предупредить пользователя, не молча
  опираться как на истину.
- Механически: `okf_validate.py` в CI (§5.4) плюс **`okf_sync_gate.py --check-stale`**
  периодически (cron-джоба раз в неделю) — падает на `stale_after` в прошлом,
  результат идёт в issue, а не в тишину. В PR-режиме та же просрочка выдаётся
  предупреждением, чтобы не блокировать несвязанную работу.

```yaml
# .github/workflows/canon-freshness.yml
name: canon-freshness
on:
  schedule: [{cron: "0 7 * * 1"}]     # понедельник, 07:00 UTC
  workflow_dispatch:
jobs:
  stale:
    runs-on: ubuntu-latest
    # §8.7 CQG: предохранитель на КАЖДОЙ джобе — дефолт GitHub 6 часов.
    timeout-minutes: 5
    steps:
      # ⚠ Версии держатся В СОГЛАСИИ с CI-шаблоном CQG §8 и сверяются
      # `tests/test_action_pins_agree.py`: здесь стояли `v4`/`v5`, снятые с
      # поддержки, и раннер печатал про них предупреждение в ЗЕЛЁНОМ прогоне.
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with: {python-version: "3.12"}
      - run: python scripts/okf_sync_gate.py --check-stale
```
- `verified` с `human:` для политик, влияющих на деньги/безопасность/автоотправку.

### 7.3. Что не делать

- Не превращать bundle в свалку PR-отчётов.
- Не держать второй «теневой» канон только в чате агента.
- Не требовать Attested Computation на каждый чих.
- Не считать Medium-статьи источником правды — только GitHub SPEC + этот канон.

---

---

> ## ⬇ Ниже — BOOTSTRAP PAYLOAD (строки ~800–1470)
>
> Шаблоны concept'ов и исходники двух скриптов. **В обычной работе не читай** —
> норматив формата и librarian protocol закончились выше (§1–§7). Читай отсюда
> при **развёртывании** bundle или когда создаёшь новый concept по шаблону.
>
> | Что | Где |
> |---|---|
> | Шаблоны `knowledge/**` (index, log, concept, ADR, hook) | Приложение A (A.1–A.6) |
> | `scripts/okf_validate.py` — формат | Приложение B |
> | `scripts/okf_sync_gate.py` — code↔canon + freshness | Приложение C |

---

# Приложение A — шаблоны

Копировать дословно, подставляя значения.

### A.1. `knowledge/index.md` (bundle root)

```markdown
---
okf_version: "0.2"
---

# Product

* [Overview](product/overview.md) - what this system does and for whom

# Engineering

* [Engineering index](engineering/) - design, ADRs, pipelines, policies

# Ops

* [Ops index](ops/) - deploy, runbooks, incident playbooks

# References

* [References](references/) - external specs, inventories, mirrored assets

# Legacy (optional)

* [Legacy docs folder](../docs/) - pre-OKF archive; migrate via ratchet
```

### A.2. `knowledge/log.md` (bundle root)

```markdown
# Knowledge Bundle Update Log

## 2026-07-26
* **Initialization**: Created OKF v0.2 bundle structure (`knowledge/`).
* **Creation**: Seed concepts under product/, engineering/, ops/.
```

### A.3. Concept template

```markdown
---
type: Design
title: Short human title
description: One sentence summary for indexes and previews.
status: draft
tags: [example-domain]
generated:
  by: cursor_agent/composer
  at: 2026-07-26T12:00:00Z
resource: https://example.com/issue/PROJ-1
# Машиночитаемая карта реализации: пути (от repo-root), поведение которых
# описывает этот concept. Гейт okf_sync_gate.py (Приложение C) падает, если
# такой путь изменён, а concept — нет. Каталог = префикс; допустим glob-хвост /**.
implementation:
  - backend/features/gates/
  - backend/features/gates/service.py
stale_after: 2026-10-01        # для Policy/Metric высокой ставки
---

# Purpose

Why this concept exists.

# Canonical rules

- Rule one
- Rule two

# Related

- See [neighbor concept](/engineering/example/neighbor.md).

# Implementation map

| Area | Path |
|---|---|
| Code | `backend/features/gates/` |

<!-- Таблица — для людей; гейт читает frontmatter `implementation:`. Держи их
     согласованными: расхождение = concept врёт про то, что описывает. -->
```

**Про `implementation:`** — это то, что превращает librarian protocol из
соглашения в гейт. Concept без этого поля живёт нормально (гейт его просто не
видит), поэтому миграция идёт ратчетом: заполняй поле у тех concept'ов, чей
дрейф уже кусал. Пустой список ≠ отсутствие поля: `implementation: []`
означает «сознательно не привязан к коду» (глоссарий, внешний Reference).

### A.4. Фрагмент для `AGENTS.md` / Cursor rule

```markdown
## OKF knowledge bundle

- **Stack map first:** `AGENT_STACK.md` (Delivery → CQG → OKF).
- Bundle root: `knowledge/` (Open Knowledge Format).
- **Before answering canonical questions** (policies, gate invariants,
  metrics definitions, ADR outcomes, runbooks): read
  `knowledge/index.md` and follow links. Do not invent from memory.
- **When changing invariants** in code: update the related OKF concept in
  the same change; refresh parent `index.md` and scope `log.md`.
  This is enforced, not advisory: `scripts/okf_sync_gate.py` fails CI when a path
  listed in a concept's `implementation:` changed but the concept did not.
  Declare that field on any concept that describes code behaviour.
- New durable knowledge goes into the bundle (YAML frontmatter with `type`),
  not into a new orphan markdown dump.
- Bootstrap / format rules: `OKF_KNOWLEDGE_BUNDLE.md`.
- Process / quality siblings: `AGENT_DELIVERY_HARNESS.md`, `CODE_QUALITY_GATES.md`.
- Upstream spec (check on OKF deploy/migrate): 
  https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
```

### A.5. Domain `index.md` template

```markdown
# Engineering

* [Gates](gates/) - donor quality gates and calibration canon
* [Outreach](outreach/) - AI outreach policies and pipelines
```

### A.6. ADR concept skeleton

```markdown
---
type: ADR
title: "ADR-001: RQ vs Celery"
description: Decision to use Redis Queue for background jobs.
status: stable
tags: [architecture, queues]
generated:
  by: human:owner
  at: 2026-03-20T00:00:00Z
verified:
  by: human:owner
  at: 2026-03-22T00:00:00Z
---

# Status

Accepted.

# Context

…

# Decision

…

# Consequences

…

# Related

- [Scalable automation methodology](/engineering/architecture/methodology.md)
```

---

# Приложение B — валидатор формата (`okf_validate.py`)

Файл: `scripts/okf_validate.py`  
Зависимости: Python 3.10+ stdlib only.  
Проверяет **project + conformance soft subset**: frontmatter/`type`,
reserved files shape hints, optional size smells. Не заменяет полный
consumer SPEC.

```python
#!/usr/bin/env python3
"""OKF bundle soft validator (project profile + SPEC §11 subset).

Usage:
  python scripts/okf_validate.py                 # bundle=knowledge/
  python scripts/okf_validate.py path/to/bundle
  OKF_MAX_LINES=600 python scripts/okf_validate.py

Exit 0 = no errors (warnings allowed). Exit 1 = conformance errors.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

RESERVED = {"index.md", "log.md"}
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
# `[ \t]`, а НЕ `\s`: `\s` включает перевод строки, и на пустом `type:` регулярка
# уходила на следующую строку — `type:` + `title: t` давало type == "title: t".
# Валидатор печатал `0 error(s)` там, где SPEC §11 требует непустой type: ложное
# зелёное. Найдено дописыванием регрессии, а не прогоном (тест на пустой тип был
# первым, который вообще это спросил).
TYPE_RE = re.compile(r"(?m)^type:[ \t]*(.+?)[ \t]*$")


def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    raw = m.group(1)
    meta: dict[str, str] = {}
    # minimal: only need type; ignore nested YAML complexity
    tm = TYPE_RE.search(raw)
    if tm:
        meta["type"] = tm.group(1).strip().strip("\"'")
    meta["_raw"] = raw
    return meta, text[m.end() :]


def check_body_smells(rel: str, path: Path, body: str,
                      warnings: list[str]) -> None:
    """Мягкие пределы concept'а: строк в теле и байт в файле (§3.3, атомарность).

    Отдельный шов, потому что это единственный читатель порогов из окружения:
    пока они жили в `validate_bundle`, каждый следующий разрез тащил бы их
    через ещё одну сигнатуру. Замер: −4 к цикломатике `check_file`.
    """
    max_lines = int(os.environ.get("OKF_MAX_LINES", "600"))
    max_bytes = int(os.environ.get("OKF_MAX_BYTES", str(80 * 1024)))
    lines = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    size = path.stat().st_size
    if lines > max_lines:
        warnings.append(f"{rel}: body ~{lines} lines > soft max {max_lines} (split?)")
    if size > max_bytes:
        warnings.append(f"{rel}: {size} bytes > soft max {max_bytes} (split?)")


def check_links(rel: str, root: Path, body: str, warnings: list[str]) -> None:
    """Bundle-абсолютные ссылки ведут в существующий файл (SPEC §6, soft).

    Шов здесь потому, что это единственная проверка, которой нужен КОРЕНЬ
    bundle'а рядом с телом файла, и единственная, что кладёт цикл внутрь цикла:
    вынос забирает у `check_file` сразу два ветвления.
    """
    for link in re.findall(r"\[[^\]]*\]\((/[^)]+?\.md)\)", body):
        if not (root / link.lstrip("/")).is_file():
            warnings.append(f"{rel}: broken bundle link {link}")


def check_file(path: Path, root: Path, errors: list[str],
               warnings: list[str]) -> None:
    """Один markdown bundle'а: кодировка, зарезервированное имя, frontmatter, type.

    Шов по потоку управления: каждый `continue` тела цикла означал «по этому
    файлу всё» — и стал ранним `return` помощника, поэтому смысл через границу
    не изменился, а решение «идти ли дальше» осталось внутри одного файла.
    Свободными в блоке `ast` называл ровно `path`, `root`, `errors`, `warnings`
    (пороги ушли в `check_body_smells` — там их единственный читатель).
    """
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{rel}: not UTF-8")
        return

    if path.name in RESERVED:
        if path.name == "log.md" and not re.search(
                r"(?m)^## \d{4}-\d{2}-\d{2}\s*$", text):
            warnings.append(f"{rel}: no ## YYYY-MM-DD headings (SPEC §9 shape)")
        return

    meta, body = parse_frontmatter(text)
    if meta is None:
        errors.append(f"{rel}: missing YAML frontmatter (SPEC §11)")
        return
    if not meta.get("type"):
        errors.append(f"{rel}: frontmatter missing non-empty type (SPEC §11)")

    check_body_smells(rel, path, body, warnings)
    check_links(rel, root, body, warnings)


def check_root_index(root: Path, warnings: list[str]) -> None:
    """Корень bundle'а: `index.md` существует и называет `okf_version` (SPEC §12).

    Шов проведён по данным: блок судил ОДИН файл и отдавал наружу только строки
    `warnings` — `ast` показывает свободными ровно `root` и `warnings`, а имя
    `text` из него ниже никто не читал (в цикле оно связывалось заново). Ветка
    «файла нет» восстановлена ранним `return`, чтобы охрана условия осталась
    частью блока, а не превратилась во вложенность.
    """
    root_index = root / "index.md"
    if not root_index.is_file():
        warnings.append(
            "missing root index.md (optional in SPEC, required by project profile)")
        return
    if "okf_version" not in root_index.read_text(encoding="utf-8"):
        warnings.append("root index.md has no okf_version (SPEC §12 recommended)")


def validate_bundle(root: Path) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not root.is_dir():
        print(f"ERROR: bundle root not a directory: {root}", file=sys.stderr)
        return 1

    md_files = sorted(root.rglob("*.md"))
    if not md_files:
        errors.append(f"no markdown files under {root}")

    check_root_index(root, warnings)

    for path in md_files:
        check_file(path, root, errors, warnings)

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    print(
        f"okf_validate: {len(errors)} error(s), {len(warnings)} warning(s), "
        f"files={len(md_files)}, root={root}"
    )
    return 1 if errors else 0


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "knowledge")
    return validate_bundle(root.resolve())


if __name__ == "__main__":
    sys.exit(main())
```

Активация:

```bash
chmod +x scripts/okf_validate.py
python scripts/okf_validate.py knowledge/
```

---

# Приложение C — `scripts/okf_sync_gate.py` (гейт code ↔ canon)

Файл: `scripts/okf_sync_gate.py`
Зависимости: Python 3.10+ stdlib only (+ `git` в PATH).

**Что закрывает.** §4.1 требует «изменён инвариант — обнови concept в том же
PR/сессии», DoD Delivery §3.2.4 повторяет это как условие закрытия поставки —
но проверить это было нечем, и это была единственная часть контура, где «Done =
oracles» держалась на честном слове. Гейт сравнивает изменённые файлы с полем
`implementation:` каждого concept'а: тронул код, который concept описывает, —
тронь concept (или явно заяви waiver).

**Ратчет.** Concept без `implementation:` невидим для гейта, поэтому на пустом
bundle гейт зелёный и не мешает. Сила растёт по мере заполнения поля — как
baseline-ратчет в CQG, только вверх по покрытию, а не вниз по нарушениям.

```python
#!/usr/bin/env python3
"""OKF code<->canon sync gate + freshness check.

Usage:
  python scripts/okf_sync_gate.py --base origin/main        # sync (PR-режим)
  python scripts/okf_sync_gate.py --staged                  # sync (pre-commit)
  python scripts/okf_sync_gate.py --check-stale             # freshness, без git
  OKF_BUNDLE=brain python scripts/okf_sync_gate.py --base origin/main

Exit 0 = OK (warnings allowed). Exit 1 = drift/staleness errors.

Waiver (осознанный дрейф — например, чистый рефакторинг без смены инварианта):
  ALLOW_CANON_DRIFT=1 python scripts/okf_sync_gate.py --base origin/main
Обязан быть виден и объяснён в PR. STRICT=0 — soft-режим (warning, exit 0).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

BUNDLE = os.environ.get("OKF_BUNDLE", "knowledge")
STRICT = os.environ.get("STRICT", "1") != "0"
ALLOW_DRIFT = os.environ.get("ALLOW_CANON_DRIFT", "0") == "1"
RESERVED = {"index.md", "log.md"}
DELIVERY_STATUS = "delivery/active/STATUS.md"

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def git(*args: str) -> str:
    """git с подавлением ошибок: пустая строка = git не смог (не блокер сам по себе)."""
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return ""
    return out.stdout if out.returncode == 0 else ""


def repo_root() -> Path:
    top = git("rev-parse", "--show-toplevel").strip()
    return Path(top) if top else Path.cwd()


def frontmatter(text: str) -> str:
    m = FRONTMATTER_RE.match(text)
    return m.group(1) if m else ""


def parse_list_field(fm: str, name: str) -> list[str] | None:
    """YAML-подмножество: "name:" + block-list, или "name: [a, b]", или "name: []".

    Возвращает None, если поля нет (concept невидим для гейта), и [] если поле
    объявлено пустым (сознательно не привязан к коду).
    """
    inline = re.search(rf"(?m)^{name}:[ \t]*\[(.*?)\][ \t]*$", fm)
    if inline:
        items = [i.strip().strip("\"'") for i in inline.group(1).split(",")]
        return [i for i in items if i]
    block = re.search(rf"(?m)^{name}:[ \t]*$", fm)
    if not block:
        return None
    out: list[str] = []
    for line in fm[block.end() :].splitlines():
        if re.match(r"^[ \t]*-[ \t]*", line):
            out.append(re.sub(r"^[ \t]*-[ \t]*", "", line).strip().strip("\"'"))
        elif line.strip() and not line.startswith((" ", "\t")):
            break  # началось следующее поле верхнего уровня
    return out


def scalar_field(fm: str, name: str) -> str:
    m = re.search(rf"(?m)^{name}:[ \t]*(.+?)[ \t]*$", fm)
    return m.group(1).strip().strip("\"'") if m else ""


def status_waiver(root: Path) -> str:
    """Строка `canon_drift_waiver:` из STATUS активной поставки ("" если нет).

    Waiver обязан жить там, где идёт ревью. env-переменная для этого не годится:
    в CI её иначе как правкой workflow не задать — то есть НАВСЕГДА, а локально
    она не оставляет следа в диффе, и ревьюер обхода не видит. Строка в STATUS
    попадает в дифф, видна в PR и умирает вместе с поставкой (уходит в archive).

    Зачем waiver вообще нужен: гейт видит «файл тронут», а не «инвариант изменён».
    Типизация, формат, логи, переименования трогают код под `implementation:`, не
    меняя смысла. Правка concept'а в таком PR была бы ЛОЖНЫМ «обновлено»: свежий
    `generated.at` создаёт вид пересмотра канона, которого не было.
    """
    p = root / DELIVERY_STATUS
    if not p.is_file():
        return ""
    m = re.search(
        r"(?im)^[ \t]*[-*]?[ \t]*\**canon_drift_waiver\**[ \t]*:\**[ \t]*(.*)$",
        p.read_text(encoding="utf-8"),
    )
    if not m:
        return ""
    val = re.sub(r"<!--.*?-->", "", m.group(1)).strip()
    if not val or val.lower() in {"no", "none", "-", "…"} or val.startswith("<"):
        return ""
    return val


def covers(declared: str, changed: str) -> bool:
    """Совпадение пути: точное, префикс каталога или glob-хвост /**."""
    d = declared.strip().lstrip("./").rstrip()
    if d.endswith("/**"):
        d = d[:-3]
    if d.endswith("/*"):
        d = d[:-2]
    d = d.rstrip("/")
    if not d:
        return False
    return changed == d or changed.startswith(d + "/")


def changed_files(base: str | None, staged: bool) -> tuple[list[str], list[str]]:
    """(файлы, проблемы). Пустой список файлов при проблеме = гейт не судит."""
    if staged:
        out = git("diff", "--name-only", "--cached")
        if not out.strip():
            return [], ["nothing staged"]
        return [f for f in out.splitlines() if f], []
    if not base:
        return [], ["no --base and no --staged"]
    if not git("rev-parse", "--verify", "--quiet", base).strip():
        return [], [f"ref '{base}' unavailable (shallow clone? need full history)"]
    merge_base = git("merge-base", base, "HEAD").strip() or base
    out = git("diff", "--name-only", f"{merge_base}..HEAD")
    return [f for f in out.splitlines() if f], []


def collect_concepts(root, bundle) -> tuple[dict, list]:
    """Карта `concept → объявленные пути` и список просроченных.

    Шов `main` (`okf@1.13`): блок только СОБИРАЕТ данные и ничего не судит,
    поэтому отделяется чисто и возвращает ровно две структуры.
    """
    concepts: dict[str, list[str]] = {}
    stale: list[tuple[str, str]] = []
    today = date.today()
    for path in sorted(bundle.rglob("*.md")):
        if path.name in RESERVED:
            continue
        rel = path.relative_to(root).as_posix()
        fm = frontmatter(path.read_text(encoding="utf-8"))
        if not fm:
            continue
        declared = parse_list_field(fm, "implementation")
        if declared:
            concepts[rel] = declared
        after = scalar_field(fm, "stale_after")
        m = DATE_RE.search(after) if after else None
        if m:
            when = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if when < today:
                stale.append((rel, after))
    return concepts, stale


def check_concept_sync(files, concepts: dict, errors: list[str],
                       warnings: list[str]) -> None:
    """Код тронут, а concept — нет: рассинхрон знания и реализации (§7.2).
    """
    if files:
        touched_bundle = {f for f in files if f.startswith(f"{BUNDLE}/")}
        code = [f for f in files if f not in touched_bundle]
        for rel, declared in sorted(concepts.items()):
            if rel in touched_bundle:
                continue  # concept обновлён — синхронизация заявлена
            hits = sorted(
                {c for c in code for d in declared if covers(d, c)}
            )[:5]
            if hits:
                errors.append(
                    f"{rel}: implementation changed but concept untouched -> "
                    f"{', '.join(hits)}"
                )
        if not concepts:
            warnings.append(
                "no concept declares implementation: — gate is inert; "
                "start filling the field (Приложение A.3)"
            )


def report(args, root, concepts: dict, errors: list[str],
           warnings: list[str]) -> int:
    """Печать итога и код возврата.

    Шов `main` (`okf@1.13`): вывод отделён от суждения — так `main` остаётся
    диспетчером, а советы не мешают читать логику.
    """
    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if not errors:
        # ⚠ Слово `OK` — это то, что уезжает в таблицу прогонов verify-report'а,
        # и до `okf@1.16` оно было одинаковым у «проверил и сошлось» и у
        # «проверять было нечем». Пустой дифф теперь ошибка (см. `judge_sync`),
        # а вторая инертность — карта без единого `implementation:` — законна на
        # развёртывании и остаётся warning'ом; но в СТРОКЕ ИТОГА она называется,
        # иначе снова попадёт в отчёт неотличимой от проверки.
        inert = "" if concepts else " — INERT: 0 concepts mapped, судить нечем"
        print(
            f"okf_sync_gate: OK ({len(concepts)} mapped concepts, "
            f"{len(warnings)} warning(s)){inert}"
        )
        return 0
    # Waiver из STATUS — основной механизм: виден в диффе, живёт одну поставку.
    # На --check-stale не действует: просроченный concept — это не «код тронут без
    # смены смысла», а отдельная проблема (§7.2).
    if not args.check_stale:
        waiver = status_waiver(root)
        if waiver:
            print(
                f"okf_sync_gate: drift разрешён waiver'ом из {DELIVERY_STATUS}: "
                f"{waiver}\n"
                f"({len(errors)} concept(s) не тронуты — waiver виден в PR и умрёт "
                f"с поставкой)"
            )
            return 0

    if ALLOW_DRIFT:
        print(
            f"okf_sync_gate: drift allowed by ALLOW_CANON_DRIFT=1 "
            f"({len(errors)} finding(s)).\n"
            f"⚠ env-обход НЕ виден ревьюеру и в CI задаётся только правкой workflow "
            f"(то есть навсегда). Предпочитай строку `canon_drift_waiver:` в "
            f"{DELIVERY_STATUS}.",
            file=sys.stderr,
        )
        return 0
    if not STRICT:
        print(f"okf_sync_gate: WARNING (STRICT=0) — {len(errors)} finding(s)", file=sys.stderr)
        return 0
    if args.check_stale:
        print(
            f"okf_sync_gate: FAIL — {len(errors)} concept(s) past stale_after.\n"
            "Fix: re-verify the canon and set `verified:` + a new `stale_after`, "
            "or mark the concept `status: deprecated` (§7.2).",
            file=sys.stderr,
        )
    else:
        print(
            f"okf_sync_gate: FAIL — {len(errors)} concept(s) out of sync with code.\n"
            "Варианты, в порядке предпочтения:\n"
            "  1. Инвариант правда изменился → обнови concept + scope log.md (§4.1).\n"
            "  2. Смысл не менялся (типы, формат, логи, переименование) → строка\n"
            f"     `canon_drift_waiver: reason=… by=human:…` в {DELIVERY_STATUS}:\n"
            "     она видна в PR и умрёт вместе с поставкой. Правка concept'а «чтобы\n"
            "     позеленело» — ложное «обновлено», так делать нельзя.\n"
            "  3. Путь больше не описывает этот concept → убери его из "
            "`implementation:`\n"
            "     (или сузь до конкретных файлов, если срабатывания повторяются).",
            file=sys.stderr,
        )
    return 1


def parse_cli() -> argparse.Namespace:
    """Разбор аргументов вместе с фолбэком на `BASE` из окружения.

    Шов по данным: блок отдаёт наружу ровно одно имя — `args`, свободных имён у
    него нет вовсе (`ast`), поэтому граница проходит по нему без остатка. Держать
    фолбэк здесь же обязательно: «чем судить» — часть разбора входа, а не
    логики, и разъехавшись с ним, гейт снова запускался бы без базы.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="ref to diff against (e.g. origin/main)")
    ap.add_argument("--staged", action="store_true", help="use staged diff")
    ap.add_argument("--check-stale", action="store_true", help="stale_after check")
    args = ap.parse_args()

    # Фолбэк на BASE из окружения: гейты CQG получают базу именно так, и
    # расхождение конвенций (флаг здесь, переменная там) само приводило к
    # запуску без базы — то есть к зелёному гейту, не проверившему ничего.
    if not args.base and not args.staged:
        args.base = os.environ.get("BASE") or None
    return args


def judge_freshness(concepts: dict, stale: list, errors: list[str]) -> None:
    """`--check-stale`: просроченный `stale_after` — ошибка, а не предупреждение.

    Половина развилки `main`, вырезанная целиком: `ast` называет свободными
    ровно `concepts`, `stale`, `errors`, а решение о коде возврата остаётся у
    `report` — через шов не проходит ни `return`, ни `break`.
    """
    for rel, when in stale:
        errors.append(f"{rel}: stale_after {when} is in the past — re-verify or bump")
    if not stale:
        print(f"okf_sync_gate: freshness OK ({len(concepts)} mapped concepts)")


def judge_sync(args, concepts: dict, stale: list, errors: list[str],
               warnings: list[str]) -> None:
    """Sync-режим: дифф против базы против карты `implementation:` (§4.1).

    Вторая половина той же развилки. Шов здесь потому, что режимы делят только
    вход и печать: `stale` в этой ветке даёт warning, а в соседней — ошибку, и
    держать оба смысла в одной функции значило хранить развилку дважды. Замер:
    `main` 152/37 → 46/10 после `okf@1.13` и → 18/3 здесь.
    """
    for rel, when in stale:
        warnings.append(f"{rel}: stale_after {when} is in the past (§7.2)")

    files, issues = changed_files(args.base, args.staged)
    for i in issues:
        # ERROR, а не warning: невозможность вычислить дифф в sync-режиме — это
        # неверная конфигурация обязательного входа, а не отсутствие внешнего
        # инструмента. Гейт, вышедший 0 и не посмотревший ни одного файла,
        # хуже отсутствующего (Delivery §3.1a). Найдено развёртыванием: вызов
        # без --base давал WARNING и exit 0, то есть зелёный гейт, проверивший
        # ноль. Отдельно от этого база теперь берётся и из окружения BASE —
        # у гейтов CQG конвенция именно такая, и расхождение конвенций само
        # приводило к «забыл флаг».
        errors.append(
            f"cannot compute diff: {i} — передай --base <ref> (или BASE=<ref>) "
            "либо --staged; иначе гейт не проверяет ничего"
        )
    if not files and not issues:
        # Пустой дифф = гейт не судил НИЧЕГО, и это ERROR, а не warning
        # (`okf@1.16`, поле). Прежняя редакция честно печатала «inert this run»
        # и выходила 0 — развёртывание прочло зелёное и записало в таблицу
        # прогонов «okf_sync_gate — OK». Warning против этого не работает: в
        # отчёте всё равно остаётся строка гейта, и inert от проверенного там
        # неотличим. Класс здесь был НАЗВАН верно и раньше — прежний комментарий
        # говорил «молчаливый no-op читается как «проверено»» — и лечился
        # надписью о самом себе. Знание класса не заменяет вердикта.
        #
        # Довод написан ветвью ВЫШЕ и применяется дословно: «гейт, вышедший 0 и
        # не посмотревший ни одного файла, хуже отсутствующего» (Delivery
        # §3.1a). Невозможность вычислить дифф и пустой дифф — одна ситуация для
        # читателя отчёта; вторая половина получила вердикт мягче первой только
        # потому, что выглядит штатной.
        #
        # Законный повод (прогон до коммита, push в саму базу) от этого не
        # исчезает — он теперь НАЗЫВАЕТСЯ вместо того, чтобы пройти молча.
        # Ровно так поле и ошиблось: гейт прогнали ДО коммита, дифф против
        # origin/main был пуст, гейт напечатал inert, и два расхождения нашёл
        # потом CI. «Локально зелено» и «CI зелёный» разошлись не окружением, а
        # МОМЕНТОМ прогона, и различить это может только сам гейт.
        errors.append(
            f"diff vs '{args.base or 'staged'}' is empty — gate judged NOTHING. "
            "Прогон до коммита либо база, совпадающая с HEAD: возьми базу, "
            "против которой поставка мержится (`--base origin/main`), и уже "
            "ПОСЛЕ коммита. Зелёное здесь читалось бы как «проверено», а "
            "проверено ноль файлов"
        )
    check_concept_sync(files, concepts, errors, warnings)


def main() -> int:
    args = parse_cli()

    root = repo_root()
    bundle = root / BUNDLE
    errors: list[str] = []
    warnings: list[str] = []

    if not bundle.is_dir():
        print(f"okf_sync_gate: no bundle at {BUNDLE}/ — skip (deploy OKF first)")
        return 0

    concepts, stale = collect_concepts(root, bundle)

    if args.check_stale:
        judge_freshness(concepts, stale, errors)
    else:
        judge_sync(args, concepts, stale, errors, warnings)

    return report(args, root, concepts, errors, warnings)


if __name__ == "__main__":
    sys.exit(main())
```

Активация:

```bash
chmod +x scripts/okf_sync_gate.py
python scripts/okf_sync_gate.py --base origin/main    # как в CI
python scripts/okf_sync_gate.py --check-stale         # freshness (cron/недельно)
```

В CI — шаг в той же джобе, где `okf_validate.py` (CQG §8.3). Локально можно
повесить на pre-commit с `--staged`, но это опционально: гейт осмысленнее на
полном диффе ветки, чем на одном коммите.

---

## Changelog этого канона

| Дата | Изменение |
|---|---|
| 2026-08-13 | **v1.17**: **версия действия GitHub — число, и жило оно в трёх местах с двумя ответами.** Раннер на зелёном прогоне печатал «Node.js 20 is deprecated… forced to run on Node.js 24»: CI-шаблон CQG §8 стоял на `v7`, а шаблон `canon-freshness` здесь и собственный workflow канон-репозитория — на `v4`/`v5`. **Замер, а не догадка** (`gh api repos/actions/*/releases/latest`): актуальны `checkout v7.0.1`, `setup-python v7.0.0`, `setup-node v7.0.0`, `cache v6.1.0`, то есть CQG был прав, а отстали двое. Первый диагноз («поставляемый шаблон несёт старые версии») оказался неточным ровно наполовину, и это стоит записать: чинить собирались не то место. **Класс — тот же, что у счёта гейтов и версий канонов:** README требует «каждое число живёт в одном месте», а версия действия под это правило не попадала ни разу. Неприятен он тем, что отставший пин НЕ КРАСНЕЕТ — он предупреждает, и предупреждение живёт в логе УСПЕШНОГО прогона, где его никто не читает; к моменту, когда форсирование выключат, шаблон уже уехал во все развёртывания. Источником истины назван CI-шаблон CQG: он единственный, что копируется целиком, и правится чаще прочих. Оракул — `tests/test_action_pins_agree.py`, три прогона: согласие версий (на старом каноне красный, называет каждое место с его версией), «источник знает каждое используемое действие» (иначе пин, живущий только здесь, не с чем сверять — так он и отстал) и защита от пустоты (сменится формат — разбор перестанет находить пины и позеленеет ничем). **Прямо сказано, чего оракул не даёт:** он держит СОГЛАСИЕ, а не СВЕЖЕСТЬ — отстань все пины разом, останется зелёным. Свежесть спрашивают у сети, а сьют обязан быть герметичным (`cqg@2.03`); команда сверки записана в шапке теста. **веса эта правка не добавила** — ратчет считает `scripts/**`, а тронуты шаблон workflow и комментарии; названо, чтобы отсутствие цены не читалось как забытая запись. **объём: +4 строк, за что** — три строки предупреждения в шаблоне и эта запись |
| 2026-08-13 | **v1.16** (полевой отчёт `voice-interview-coach`): **прогон, не посмотревший ни одного файла, больше не зелёный.** `okf_sync_gate` на пустом диффе печатал «inert this run», выходил 0 — и развёртывание записало в таблицу прогонов verify-report'а «`okf_sync_gate --base origin/main` — OK». Гейт прогнали ДО коммита, дифф против `origin/main` был пуст, два расхождения нашёл потом CI; одно (`transcript-durability`) действительно требовало нового правила. **«Локально зелено» и «CI зелёный» разошлись не окружением, а МОМЕНТОМ прогона**, и различить это может только сам гейт. Пустой дифф теперь ERROR — довод не новый, он написан ВЕТВЬЮ ВЫШЕ и применяется дословно: «гейт, вышедший 0 и не посмотревший ни одного файла, хуже отсутствующего» (Delivery §3.1a); невозможность вычислить дифф и пустой дифф — одна ситуация для читателя отчёта, и вторая половина получила вердикт мягче первой только потому, что выглядит штатной. Законный повод (push в саму базу) не исчез, он НАЗЫВАЕТСЯ вместо того, чтобы пройти молча, и текст ошибки называет починку: база, против которой поставка мержится, и ПОСЛЕ коммита. Отдельно — **строка итога**: слово `OK` и есть то, что уезжает в отчёт, поэтому вторая инертность (карта без единого `implementation:`, на развёртывании штатная и оставшаяся warning'ом) теперь печатается как `INERT: 0 concepts mapped`. **Класс здесь был назван верно и раньше** — прежний комментарий говорил «молчаливый no-op читается как «проверено»» — и лечился надписью о самом себе; знание класса не заменяет вердикта. Оракул на класс общий с `delivery@1.72`: `tests/test_green_without_the_thing.py`, форма «пустотой» — четыре прогона, из них три красных на старом каноне, включая отдельный прогон «строки `OK` в выводе нет» (код возврата и строка итога — два разных наблюдения, и поле читало вторую). Цена — в записи `delivery@1.72`: **вес: +30 строк** из общих +83 |
| 2026-08-10 | **v1.15**: **объявление стоимости чтения исправлено числом по факту** — payload стоял ≈670 при фактических 774. Расхождение сверх допуска ±10% жило незамеченным потому, что оракул `selftest_sizes.py` искал объявление в форме CQG («строк» + процент в скобках), а здесь записана другая форма — то есть проверка молчала не от отсутствия расхождения, а от того, что не видела запись. Механика починена на свойство в `stack-map@1.45` |
| 2026-07-26 | Initial: OKF v0.2 operational canon; mandatory upstream-check gate; project profile; librarian protocol; templates; soft validator |
| 2026-07-26 | Review pass: fix okf_version wording in deploy prompt; clarify pillars ≠ SPEC terms; v0.1 legacy note; `generated.by` required; index path wording |
| 2026-07-26 | Cross-link stack: `AGENT_STACK.md`; §0 scoped to OKF deploy (not whole stack); AGENTS hook updated |
| 2026-07-26 | Pointer: skills/evals live outside OKF; optional Reference to `skills/` (Delivery §11) |
| 2026-07-27 | **v1.3** (review pass): canon version в шапке (отделена от pinned upstream `okf_version`); `okf_validate.py` переведён из «опционально» в обязательный CI-шаг (§5.4, §7.2); freshness — механический прогон, а не соглашение |
| 2026-07-27 | **v1.4**: Приложение C — `okf_sync_gate.py`, гейт code↔canon (§4.1 стал прибитым, а не соглашением); поле `implementation:` во frontmatter concept'а (A.3) как машиночитаемая карта реализации + `implementation: []` для несвязанных с кодом; `--check-stale` + weekly workflow закрывают §7.2; DoD §5.4 расширен |
| 2026-07-27 | **v1.5**: `implementation:` дописано в §3.5 (профиль frontmatter) и в hook A.4 — без этого агент, читающий профиль, о поле не узнавал и гейт оставался инертным; убран лишний ``` в конце файла (нашла самопроверка `AGENT_STACK.md` §7); баннер `⬇ BOOTSTRAP PAYLOAD` + «стоимость чтения» |
| 2026-07-28 | **v1.6**: терминология по словарю `AGENT_STACK.md` §1.1 — «Карта канонов», «Слой контура», часть контура вместо «часть стека» |
| 2026-08-10 | **v1.14**: **Скрипты OKF под §2.1 целиком.** `okf_validate::validate_bundle` 67/cx21 → 27/cx7 (тело цикла целиком стало `check_file`, каждый `continue` — ранним `return`; пороги `OKF_MAX_LINES`/`OKF_MAX_BYTES` ушли к единственному читателю и перестали течь через сигнатуры), `okf_sync_gate::main` 56/cx13 → 20/cx3 (разбор CLI, суждение о свежести, суждение о синхронности — половины развилки `--check-stale`/sync разошлись явно: `stale` в одной ветке warning, в другой ошибка). Найдено вырезом: лишний ```-фенс во вставке закрывает блок и молча обрезает payload — закрыто оракулом `tests/test_payload_not_truncated.py` (CQG 1.97) |
| 2026-08-10 | **v1.13**: **`okf_sync_gate.py::main` разрезана: 152 строки → 56, cx 37 → 13.** Три шва: `collect_concepts` (сбор карты и просроченного — блок только СОБИРАЕТ и ничего не судит), `check_concept_sync` (код тронут, а concept нет), `report` (печать итога и код возврата). **Дефект самой правки поймал не глаз, а сьют:** вставка шла в первый попавшийся `def main(` файла, а в OKF их ДВА — три функции уехали в `okf_validate.py` и там же исчезли из своего скрипта; тесты гейта прошли, а тест соседа упал `NameError`. Урок к процедуре: якорь вставки берётся от ЗАГОЛОВКА приложения нужного скрипта, а не по первому совпадению в файле. Второе — `root` остался в `report` свободным именем и уронил ветку waiver'а: счёт свободных имён показывал его, я прочёл невнимательно |
| 2026-07-29 | **v1.12**: `timeout-minutes` на джобах weekly-workflow'а `--check-stale` — предохранитель §8.7 CQG требует его на КАЖДОЙ джобе (дефолт GitHub — 6 часов), а здесь его не было. **Запись восстановлена 2026-07-31 по истории git:** версия была поднята в `c29f6f6` без строки в журнале, и это обнаружилось только когда появилась проверка «у каждой версии есть запись». До неё три версии подряд (1.10–1.12) существовали как номер в шапке без описания — журнал молчал о том, что менялось |
| 2026-07-29 | **v1.11** (находка регрессии, не прогона): `okf_validate.py` **принимал пустой `type:`**. В `TYPE_RE` стояло `\s*`, а `\s` включает перевод строки, поэтому на `type:` с пустым значением регулярка уходила на следующую строку и `type:` + `title: t` давало `type == "title: t"`. Валидатор печатал `0 error(s)` там, где SPEC §11 требует непустой `type` — ложное зелёное того же класса, что F17 («OK на стеке, который гейт не поддерживает»). Теперь `[ \t]`. Нашлось при дописывании регрессии на непокрытые скрипты: тест на пустой тип был первым, который вообще задал этот вопрос — четыре полевых развёртывания и `stack_selftest` проходили мимо, потому что валидный bundle такого файла не содержит |
| 2026-07-29 | **v1.10** (полевая находка F10): `okf_sync_gate` при невозможности вычислить дифф в sync-режиме теперь **ошибка, а не warning** — прежде запуск без `--base` печатал предупреждение и выходил **0**, то есть зелёный гейт, не посмотревший ни одного файла (Delivery §3.1a: такой гейт хуже отсутствующего). Отдельно снято расхождение конвенций, которое к этому и приводило: гейты CQG получают базу через переменную `BASE`, а этот — через флаг, поэтому привычка `BASE=… python scripts/okf_sync_gate.py` давала молча зелёный прогон. Теперь `BASE` из окружения читается как фолбэк. Проверено полем: без базы exit 1 с указанием, что передать; с базой — работает |
| 2026-07-29 | **v1.9** (бэклог №12): §3.5b — `type: Runbook` был в таблице §3.2 с начала, но не было сказано, **когда он обязателен**. Ответ из Delivery §13.3: на верхней ступени наблюдаемости каждый алерт обязан иметь runbook, потому что алерт без него не усиление, а ухудшение — будит и не помогает, после второго раза его отключают вместе с полезной частью. Минимум в теле: симптом, как проверить, как откатить, кого звать. Обязателен `stale_after` (§7.2): runbook стареет быстрее кода, и процедура откатa под прошлую архитектуру вредна активно — она уверенно ведёт не туда. Гейта на «у каждого алерта есть runbook» нет и быть не может: список алертов живёт в мониторинге, вне репозитория, связать механически нечем — записано как открытый остаток, а не покрытая область |
| 2026-07-29 | **v1.8** (бэклог №2): §3.5a «Карта репозитория — concept, а не документация». Bundle держал канон домена и молчал про канон **репозитория** (входные точки, слои, грабли), поэтому каждая сессия переоткрывала структуру. `knowledge/references/repo-map.md`, `type: Reference`. Главное не текст, а два поля: `implementation:` — **только структурные якоря** (входные точки, проводка, манифесты), потому что широкий путь вроде `backend/` сделал бы `okf_sync_gate` стабильно красным и его бы сняли (Delivery §4.3b); критерий «тронули файл — предложение в карте стало ложным?». И `stale_after` по §7.2 — потому что самый ценный раздел «Грабли» не привязан ни к одному пути и негейтируем в принципе. Требование существования — в DoD bootstrap §5.4; правило чтения до implement — в чеклисте `AGENT_STACK.md` §3, парно к Delivery §2.2a (карта: как устроено; индекс архива: на чём спотыкались) |
| 2026-07-28 | **v1.7**: waiver гейта code↔canon переведён из env-переменной в строку `canon_drift_waiver:` в STATUS (Delivery §4.3a). Причина: `ALLOW_CANON_DRIFT=1` в CI не задать иначе как правкой workflow — то есть навсегда, а локально он невидим ревьюеру. Плюс сообщение об ошибке теперь называет три варианта и прямо запрещает правку concept'а «чтобы позеленело» — ложное «обновлено» хуже красного гейта |

---

*Конец документа. Upstream truth:  
https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md*
