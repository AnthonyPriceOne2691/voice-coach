# Agent Stack Map — карта для агента

**Входная точка стека канонов.** Если в корне лежат несколько `*.md` канонов —
**начни отсюда**, потом иди по ссылкам. Этот файл короткий специально.

> Язык: проза — русский; имена файлов / пути — английские.

---

## 1. Что за стек (одна картинка)

```text
AGENT_STACK.md          ← ты здесь (карта)
        │
        ▼
① AGENT_DELIVERY_HARNESS.md   — КАК вести работу (фазы, DoD, stop-gates, evals, метрики)
        │
        ▼
② CODE_QUALITY_GATES.md       — КАК не портить код (lint / types / secrets) + CI-workflow
        │
        ▼
③ OKF_KNOWLEDGE_BUNDLE.md     — ГДЕ правда домена (knowledge bundle) + гейт code↔canon
        ╎
        ╎ ④ CI + гейт мержа — СКВОЗНОЙ слой: один прогон проверяет все три
        ╎    (контракт — Delivery §10.4; реализация — CQG §8)
        ▼
   зелёные гейты на СЛИТОМ состоянии = единственное, что закрывает поставку
```

**④ — не четвёртый файл, а место запуска первых трёх.** Локальные хуки обходятся
(`git commit -n`, `STRICT=0`, «хук не установлен»), поэтому «Done = oracles» без CI
означает «Done = самооценка». Разворачивается вместе с ②, обслуживает всё.

**Платного тарифа не требует.** Серверная защита ветки платная (GitHub: rulesets —
Team+, приватный репо — Pro+), поэтому гейт мержа лежит **в репозитории**:
`merge_guard.sh` гоняет гейты на слитом состоянии и мержит только зелёное,
`needs:` не пускает красное в прод, pre-push поднимает цену обхода. Защита ветки —
усиление сверху (CQG §8.5.3), а не предпосылка.

| # | Файл | Версия | Отвечает на | Не делает |
|---|---|---|---|---|
| ① | [AGENT_DELIVERY_HARNESS.md](AGENT_DELIVERY_HARNESS.md) | `delivery@1.11` | Что строить, в каком порядке, когда «готово»; evals; hooks; CI-контракт; метрики | Не задаёт ruff/eslint; не формат OKF |
| ② | [CODE_QUALITY_GATES.md](CODE_QUALITY_GATES.md) | `cqg@1.7` | Форма кода, commit-гейты, CI-workflow, secrets в git | Не ведёт поставку фичи; не knowledge wiki |
| ③ | [OKF_KNOWLEDGE_BUNDLE.md](OKF_KNOWLEDGE_BUNDLE.md) | `okf@1.5` | Канон смысла (политики, ADR, метрики) | Не фазы delivery; не lint-пороги; не тела skills |

Версии — из шапок соответствующих файлов. При развёртывании они пишутся в проект
одной строкой (`stack: delivery@1.11, cqg@1.7, okf@absent`) в
`delivery/CONSTITUTION.md` и `delivery/active/STATUS.md`: без этого нельзя сказать,
какую ревизию канона репозиторий получил и что менялось с тех пор.

**Эта карта:** `stack-map@1.7` · 2026-07-27. Владеет двумя сквозными вещами:
приёмкой контура (**§6**) и самопроверкой канонов (**§7** + Приложение A).

---

## 2. Движение агента

### A. Первый заход в проект (развернуть стек)

Делай **строго по порядку**. Не начинай с ② или ③.

1. Прочитай этот файл целиком.
2. Разверни **① Delivery** по его §7 (дерево `delivery/`, hook в `AGENTS.md`).
3. Если человек просит полный стек — разверни **② CQG** по его §5 **все 10 шагов**
   (конфиг копируется дословно, не «по смыслу»; шаги 8–10 — CI, гейт мержа,
   защита ветки).
4. Затем **③ OKF** по его §0→§5 (у OKF свой preflight: сверка upstream SPEC).
5. Поставь **④ гейт мержа** по CQG §8.5: `merge_guard.sh` + pre-push + `needs:`
   (на любом тарифе); защиту ветки — если тариф даёт (§8.5.3).
6. В `delivery/CONSTITUTION.md` проставь указатели и версии: CQG/OKF/CI deployed.
7. Прогони приёмку — **§6** ниже. Пока чеклист не зелёный, контур не боевой.

Команда человеку для полного стека (одна, копируется целиком):

> «Разверни канон-стек по `AGENT_STACK.md` в этом проекте, строго по порядку:
> ① Delivery (`AGENT_DELIVERY_HARNESS.md` §7): дерево `delivery/`, `CONSTITUTION.md`
> под этот проект, `scripts/delivery_check.py` (Приложение B),
> `scripts/delivery_metrics.py` (Приложение C), hook A.5 в `AGENTS.md`.
> ② CQG (`CODE_QUALITY_GATES.md` §5, **все 10 шагов**): скрипты Приложения A,
> конфиги Приложения B — `.pre-commit-config.yaml` **копируй дословно**, не собирай
> «по смыслу», иначе гейт теряется молча; baseline'ы, `pre-commit install`,
> `scripts/lint/check_baseline_ratchet.sh` (§8.2), `check_gate_coverage.sh` (мета-гейт)
> и `.github/workflows/quality.yml` (§8.3). Сверься с блоком «Применимость» — если
> стек не Python+TS, адаптируй паттерны, сохранив механику ратчета, и пройди
> таблицу §3 построчно.
> ③ OKF (`OKF_KNOWLEDGE_BUNDLE.md`): сначала §0 preflight (сверить upstream SPEC),
> затем bundle `knowledge/`, `scripts/okf_validate.py` (Приложение B),
> `scripts/okf_sync_gate.py` (Приложение C) с заполненным `implementation:` хотя бы
> у одного concept'а, weekly-workflow `--check-stale`.
> ④ Гейт мержа по CQG §8.5: **обязательно** `scripts/merge_guard.sh` (§8.5.2),
> pre-push hook и `needs:` у downstream-джоб — это работает на любом тарифе.
> Защиту ветки (§8.5.3) предлагай только если тариф её даёт — тогда скажи, что
> нужно сделать руками в UI, и не выдавай `ci-oracles: deployed`, пока не включено:
> при гейте только в репозитории правильное значение — `tooling`.
> Запиши версии в `stack:` (constitution + STATUS), прогони `stack_selftest.py`
> (§7) и закончи приёмкой по `AGENT_STACK.md` §6: покажи мне чеклист с отметками
> и что осталось weak.»

Нужен только каркас процесса, без ②③ — скажи «разверни только Delivery по §7».

### A′. ⚠ Три пункта, которые агент НЕ закроет сам

Отмечено здесь специально: это не дефекты стека и не то, что «забыли доделать» —
это места, где развёртывание **упирается в реальность проекта**. Агент,
разворачивающий стек, обязан их назвать вслух, а не тихо обойти.

Проверено практикой: на первом реальном развёртывании пункт 3 был обойдён
молча — инвариант остался непокрытым, а приёмка показала «всё зелено».

| # | Пункт | Что происходит | Кто закрывает |
|---|---|---|---|
| **1** | **Раскладка путей** | Первый прогон гейтов почти наверняка **красный**: дефолты рассчитаны на `backend/features` + `frontend`, а у проекта своя структура (или вообще другой язык) | Агент — настройкой env по **CQG §6** (см. там «Первый прогон»), при другом стеке — адаптацией паттернов по блоку «Применимость» |
| **2** | **Гейт мержа** | Серверная защита ветки **платная** (GitHub: rulesets — Team+, приватный репо — Pro+). Поэтому база — **в репозитории**: мерж только через `merge_guard.sh`, тяжёлые проверки на `pre-push`, downstream через `needs:` (**CQG §8.5.1–8.5.2**) | Агент — кладёт `merge_guard.sh` и pre-push hook. Человек — **если тариф позволяет**, включает защиту ветки (§8.5.3) как усиление |
| **3** | **Где лежат каноны** | Если четыре `*.md` не в репозитории (лежат в отдельном каталоге и не коммитятся) — CI их не видит, `stack_selftest` в CI невозможен, инвариант остаётся непокрытым | Агент — выбирает вариант A/B/C из **§7.1** и **пишет выбор в STATUS**; молчаливое B = дыра, выглядящая как покрытие |

**Запрещённые «решения» пункта 1:** отключить гейт, поставить `STRICT=0` в конфиг,
переснять baseline вверх, чтобы стало зелено. Красный первый прогон означает
«пути не настроены» **или** «в коде правда есть нарушения» — различить это и
есть работа развёртывания.

Про пункт 2 в `STATUS.md` пиши честное состояние (Delivery §10.4):
`deployed` — есть серверный гейт; `tooling` — гейт в репозитории, тариф не даёт
серверного (**нормальный рабочий режим**, не поддавки); `weak` — CI нет вовсе.
Что на бесплатном тарифе закрыть нечем: **force-push и обход админом** — этот
остаток пишется в STATUS, а не замалчивается.

### B. Обычная работа (фича / баг) — стек уже есть

1. Открой `delivery/active/STATUS.md` — фаза и класс S/M/L.
2. Следуй фазам ①: specify → plan → tasks → implement → verify → converge → handoff  
   (короткий путь для S — см. Delivery §2.2; подфазы clarify/analyze — там же).
3. При письме кода держи ② (гейты / pre-commit) зелёными — и помни, что
   закрывает поставку **зелёный CI**, а не локальный прогон (Delivery §10.4).
4. Канон домена не выдумывай — читай `knowledge/` (③); при смене инварианта
   обнови concept + log.
5. **Done** только по DoD Delivery (oracles PASS), не по самооценке.

### C. Если чего-то ещё нет

| Нет в репо | Действие |
|---|---|
| Нет `delivery/` | Сначала ①, не пиши большую фичу «в лоб» |
| Нет CQG / pre-commit | Работает; STATUS: `shape-oracles: weak`; предложи развернуть ② |
| **Нет CI** | STATUS: `ci-oracles: weak`; на классе L нужен human waiver. Локальные гейты обходятся (`commit -n`), поэтому Verifier обязан приложить прогон в чистом клоне — Delivery §10.4, CQG §8 |
| Нет `knowledge/` | Работает; не выдумывай «как принято» — спроси человека или предложи ③ |

---

## 3. Порядок чтения в сессии (чеклист)

- [ ] `AGENT_STACK.md` (этот файл)
- [ ] `delivery/active/STATUS.md` (если delivery уже развёрнут)
- [ ] Нужный кусок ① / ② / ③ по задаче — не все три целиком каждый раз
- [ ] Для доменного вопроса: `knowledge/index.md` → links (если OKF есть)

**Канон vs payload.** У каждого из ①②③ вторая половина файла — **bootstrap
payload** (шаблоны и дословные исходники скриптов), помеченный баннером
`⬇ Ниже — BOOTSTRAP PAYLOAD`. В обычной работе он не нужен:

| Файл | Канон (читать по задаче) | Payload (только при развёртывании) |
|---|---|---|
| Delivery | §0–§11, ~700 строк | Приложения A–C, ~950 |
| CQG | §0–§8, ~710 строк | Приложения A–B, ~1330 |
| OKF | §0–§7, ~700 строк | Приложения A–C, ~590 |

Читай приложение целиком **только** когда разворачиваешь слой или правишь
конкретный шаблон/скрипт. Тянуть весь файл в контекст ради вопроса «а можно ли
так писать» — не надо.

---

## 4. Куда класть в репо

Скопируй в **корень проекта** рядом с тремя канонами (или сначала только эту
карту + ①). В `AGENTS.md` / Cursor rule достаточно блока:

```markdown
## Canon stack
Start at `AGENT_STACK.md`, then follow links:
Delivery → Code Quality Gates → OKF.
Active work: `delivery/active/STATUS.md` (field `stack:` = deployed canon versions).
Done is closed by a green CI run, never by a local pass (Delivery §10.4).
```

---

## 5. Куда смотреть по пробелам 2026

| Тема | Файл / путь |
|---|---|
| Метрики / cost / rework | [AGENT_DELIVERY_HARNESS.md](AGENT_DELIVERY_HARNESS.md) **§9** (+ A.10) |
| Stop-on-red, protect-main, hooks | Delivery **§10** (+ A.11) |
| CI как неподделываемый слой | Delivery **§10.4** (контракт) + [CODE_QUALITY_GATES.md](CODE_QUALITY_GATES.md) **§8** (workflow, `check_baseline_ratchet.sh`) |
| Версии стека в проекте | `stack:` в `delivery/active/STATUS.md` и `delivery/CONSTITUTION.md` (Delivery A.1–A.2); шапки каждого канона |
| Worktree / sandbox | Delivery **§5.1** |
| Eval / smoke suite | Delivery **§6**, `delivery/evals/smoke/` |
| Secrets в git, mechanical security | [CODE_QUALITY_GATES.md](CODE_QUALITY_GATES.md) **§2.7** |
| HITL prod / опасные действия | Delivery **§4.3**, **§10.3** |
| Skills / длинные промпты | `skills/README.md` + CQG `inline-prompt`; указатель Delivery **§11** |
| Гейт code↔canon, freshness | [OKF_KNOWLEDGE_BUNDLE.md](OKF_KNOWLEDGE_BUNDLE.md) **Приложение C** (`okf_sync_gate.py`), §7.2 |
| Circuit breakers механически | Delivery **§3.4** → `delivery_check.py --diff-base` |
| Builder ≠ Verifier механически | Delivery **§5.2** + branch protection CQG **§8.5** |
| Branch protection / required checks | CQG **§8.5** |

---

## 6. Приёмка боевого контура

Контур **боевой**, когда у каждого инварианта есть исполнитель, а не абзац.
Прогоняется после развёртывания и после любого изменения стека.

### ⚠ 6.0. Сначала полнота, потом зелёность

**Слепое пятно этой процедуры, вскрытое на первом реальном развёртывании.**
`pre-commit run --all-files` доказывает исправность хуков, **перечисленных** в
конфиге, и молчит о недостающих: невключённый гейт неотличим от проходящего.
Быстрый чек-лист ниже — тоже фиксированный список команд, поэтому забытый гейт
не попадает ни туда, ни сюда, и приёмка честно показывает «7 из 7 зелёных».

Поэтому **первым** шагом приёмки идёт вопрос «всё ли на месте»:

```bash
bash scripts/lint/check_gate_coverage.sh   # каждый гейт подключён к pre-commit/CI
python stack_selftest.py                   # payload канонов не сломан
python scripts/delivery_check.py           # артефакты фазы на месте
```

И только потом — «зелено ли то, что на месте». Если собирал
`.pre-commit-config.yaml` не копированием из CQG Приложения B, а «по смыслу» —
пройди таблицу CQG §3 построчно; именно этим способом гейт и теряется.

**Общее правило:** любой чек-лист проверяет то, что в нём написано. Нужен ещё
oracle на *состав* чек-листа — иначе он доказывает лишь собственную полноту
(Delivery §3.1a).

Пометки в колонке «Кто»: **auto** — прибито скриптом и работает на любом тарифе;
**tune** — требует настройки под проект (§2.A′ пункт 1); **human** — вне
репозитория (§2.A′ пункт 2). Ни одна строка чеклиста **не требует платного
тарифа**: там, где серверный гейт платный, база — `merge_guard.sh` и `needs:`
(CQG §8.5), а защита ветки идёт усилением.

| Инвариант | Кто исполняет | Проверка |
|---|---|---|
| Spec до широкого кода (M/L) | `delivery_check` (error) · auto | [ ] |
| Human OK на spec / plan | `delivery_check` (error) | [ ] |
| Форма кода (lint/types/слои) | pre-commit + `pre-commit run --all-files` в CI · **tune** (пути §6 CQG) | [ ] |
| Baseline тает, не растёт | `check_baseline_ratchet.sh` в CI · auto | [ ] |
| Нет секретов в git | detect-secrets/gitleaks (soft-режим запрещён) · auto | [ ] |
| Product oracles на M/L | `delivery_check` (error) + smoke-джоба | [ ] |
| Формат knowledge-bundle | `okf_validate.py` в CI | [ ] |
| Канон не разъехался с кодом | `okf_sync_gate.py` + `implementation:` у concept'ов | [ ] |
| Freshness канона | `okf_sync_gate.py --check-stale` (weekly) | [ ] |
| Circuit breakers (объём поставки) | `delivery_check --diff-base` в CI | [ ] |
| Метрики harness снимаются | `delivery_metrics.py` + гейт на блок в verify-report | [ ] |
| Builder ≠ Verifier | `builder:`/`Verifier:` + `merge_guard.sh` · auto · **human** для review, если тариф даёт | [ ] |
| **Красный не попадает в main** | `merge_guard.sh` (гейты на слитом состоянии) · auto · усиление: required checks, если тариф даёт | [ ] |
| **Красное не уезжает в прод** | `needs: [gates, delivery]` у deploy-джобы · auto (тариф не нужен) | [ ] |
| **Красное на main не остаётся тихим** | workflow `main-guard` открывает issue · auto | [ ] |
| Force-push в main / обход админом | ⚠ на бесплатном тарифе **нечем**; локально — hook `protect-main`. Остаток пишется в STATUS | [ ] |
| Diff-coverage ≥70% на изменённом | `check_diff_coverage.sh` в CI · **tune** (раннер/пакет §6 CQG) | [ ] |
| **Все гейты подключены, а не только исправны** | `check_gate_coverage.sh` (CQG §3) · auto | [ ] |
| Payload самих канонов не сломан | `stack_selftest.py` (§7) · auto — **см. §7.1, если каноны лежат вне репо** | [ ] |
| Приёмка и её провалы записаны | `delivery/STACK-ACCEPTANCE.md` (Delivery A.12) | [ ] |

Осталось **соглашением, а не гейтом** (сознательно — механически не проверяется):
worktree по умолчанию (§5.1), одна active-поставка (§2.3), `max_implement_retries`
и `max_session_minutes` (§3.4), «ошибка → усиление harness» (§5.4 — метрика
`harness_hardened` его лишь показывает, но не требует).

Быстрая самопроверка одной командой (из корня репо):

```bash
python scripts/delivery_check.py --diff-base origin/main   # фазы + breakers
pre-commit run --all-files                                 # форма кода
bash scripts/lint/check_baseline_ratchet.sh                # снимки только вниз
python scripts/okf_validate.py knowledge/                  # формат канона
python scripts/okf_sync_gate.py --base origin/main         # code <-> canon
bash delivery/evals/smoke/run.sh                           # product oracles
python stack_selftest.py                                   # payload канонов (§7)
BRANCH=feat/your-branch
DRY_RUN=1 bash scripts/merge_guard.sh "$BRANCH"            # гейт мержа (CQG §8.5)
```

Если какая-то строка падает «нет такого файла» — этот слой не развёрнут; отметь
соответствующий `*-oracles: weak` в `STATUS.md`, чтобы дыра была видна, а не забыта.

---

## 7. Самопроверка самого стека

Стек требует oracles от чужого кода — а его собственный payload (11 скриптов и
конфиги внутри markdown-фенсов) до этого не проверялся ничем. Скрипт ниже
извлекает **все** код-блоки из четырёх канонов и проверяет их: python через
`ast`, bash через `bash -n`, YAML — парсером (или tab-проверкой, если PyYAML нет).
Плюс сверяет версии в шапках канонов с таблицей §1 — расхождение ревизий ловится
механически.

Гоняй **при любой правке канонов** (и в CI репозитория, где стек живёт как
источник):

```bash
python stack_selftest.py            # каноны в текущем каталоге
python stack_selftest.py path/to/canons
```

### Приложение A — `stack_selftest.py`

```python
#!/usr/bin/env python3
"""Self-test for the canon stack: every fenced code block must parse.

Usage:
  python stack_selftest.py [dir]

Проверяет:
  * python-блоки  -> ast.parse
  * bash-блоки    -> bash -n
  * yaml-блоки    -> yaml.safe_load (или запрет табов, если PyYAML нет)
  * сбалансированность ``` в каждом файле
  * версии в шапках канонов == таблица §1 в AGENT_STACK.md

Exit 0 = всё чисто. Exit 1 = хоть один блок не парсится / версии разошлись.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

CANONS = (
    "AGENT_STACK.md",
    "AGENT_DELIVERY_HARNESS.md",
    "CODE_QUALITY_GATES.md",
    "OKF_KNOWLEDGE_BUNDLE.md",
)
CHECKED_LANGS = {"python", "bash", "sh", "yaml", "yml"}


def blocks(text: str) -> tuple[list[tuple[int, str, str]], int]:
    """[(line_no, lang, code)] + число незакрытых фенсов.

    Сканер построчный, а не regex: вложенный фенс в шаблоне рассинхронизировал бы
    регулярку молча, а несбалансированность мы хотим видеть как ошибку.
    """
    out: list[tuple[int, str, str]] = []
    lang: str | None = None
    start = 0
    buf: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.startswith("```"):
            if lang is not None:
                buf.append(line)
            continue
        if lang is None:                       # открытие
            lang, start, buf = line[3:].strip().lower(), i, []
        else:                                  # закрытие
            out.append((start, lang, "\n".join(buf)))
            lang = None
    return out, (1 if lang is not None else 0)


def check_yaml(code: str) -> str | None:
    try:
        import yaml  # type: ignore
    except ImportError:
        # Без PyYAML ловим самое частое: таб в отступе YAML запрещён спекой.
        for n, line in enumerate(code.splitlines(), 1):
            if line[:1] == "\t" or (line.strip() and "\t" in line[: len(line) - len(line.lstrip())]):
                return f"tab indentation at line {n} (YAML forbids tabs)"
        return None
    try:
        # safe_load_all, а не safe_load: блоки-шаблоны frontmatter обрамлены `---`,
        # то есть являются потоком из нескольких YAML-документов, и одиночный
        # safe_load ронял их с ComposerError (ложное срабатывание).
        list(yaml.safe_load_all(code))
    except Exception as exc:  # noqa: BLE001 -- любая ошибка парсера = провал блока
        return f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
    return None


def declared_versions(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    """(версии из шапок канонов, версии из таблицы §1 карты)."""
    heads: dict[str, str] = {}
    for name in CANONS[1:]:
        p = root / name
        if not p.is_file():
            continue
        m = re.search(r"\*\*Canon version:\*\*\s*`([a-z]+)@([\d.]+)`", p.read_text(encoding="utf-8"))
        if m:
            heads[m.group(1)] = m.group(2)
    table: dict[str, str] = {}
    smap = root / CANONS[0]
    if smap.is_file():
        for m in re.finditer(r"\|\s*`([a-z]+)@([\d.]+)`\s*\|", smap.read_text(encoding="utf-8")):
            table[m.group(1)] = m.group(2)
    return heads, table


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    failures: list[str] = []
    total = 0

    for name in CANONS:
        path = root / name
        if not path.is_file():
            failures.append(f"{name}: MISSING")
            continue
        text = path.read_text(encoding="utf-8")
        found, unbalanced = blocks(text)
        if unbalanced:
            failures.append(f"{name}: unbalanced ``` fence (unterminated block)")
        checked = 0
        for line_no, lang, code in found:
            if lang not in CHECKED_LANGS or not code.strip():
                continue
            checked += 1
            total += 1
            err: str | None = None
            if lang == "python":
                try:
                    ast.parse(code)
                except SyntaxError as exc:
                    err = f"SyntaxError: {exc.msg} (block line {exc.lineno})"
            elif lang in {"bash", "sh"}:
                proc = subprocess.run(
                    ["bash", "-n"], input=code, text=True, capture_output=True, check=False
                )
                if proc.returncode:
                    err = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "bash -n failed"
            else:
                err = check_yaml(code)
            if err:
                failures.append(f"{name}:{line_no} [{lang}] {err}")
        print(f"{name}: {checked} executable block(s) checked")

    heads, table = declared_versions(root)
    for layer, ver in heads.items():
        if layer in table and table[layer] != ver:
            failures.append(
                f"version skew: {layer}@{ver} in canon header vs {layer}@{table[layer]} "
                f"in {CANONS[0]} §1 table"
            )
    missing = sorted(set(table) - set(heads))
    if missing:
        print(f"note: no Canon version header for {', '.join(missing)}")

    print(f"\nstack_selftest: {total} block(s), {len(failures)} failure(s)")
    for f in failures:
        print(f"FAIL {f}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

Не заменяет функциональные прогоны гейтов (они бывают только в реальном проекте) —
ловит то, что дешевле всего сломать при правке markdown: сломанный синтаксис
в фенсе, оборванный блок, разъехавшиеся версии.

### 7.1. ⚠ Если каноны лежат ВНЕ репозитория

§4 по умолчанию исходит из того, что четыре `*.md` лежат в корне проекта и
коммитятся. Бывает иначе — человек держит их в отдельном каталоге (`~/Prepare/`)
и не коммитит в проект. Тогда **в CI их физически нет, и проверять нечего**: этот
инвариант остаётся непокрытым, и приёмка §6 об этом не узнает.

Так тоже можно, но это надо **назвать вслух** (§2.A′), а не оставить молча:

| Вариант | Что делать | Строка в STATUS |
|---|---|---|
| **A. Каноны в репо** (дефолт) | Коммитить в корень; `stack_selftest.py` — шаг CI | `stack-selftest: ci` |
| **B. Каноны вне репо** | Гонять `stack_selftest.py` **там, где они лежат**, вручную при каждой правке; в `delivery/STACK-ACCEPTANCE.md` записать путь и то, что CI их не видит | `stack-selftest: external (<путь>)` |
| **C. Vendored-копия** | Коммитить снимок канонов в `docs/canon/` + версии в `stack:`; CI проверяет копию | `stack-selftest: ci (vendored)` |

Выбор **B без записи в STATUS** — это то же самое, что неподключённый гейт:
инвариант выглядит покрытым, а его нет.

---

*Карта стека. Детали — только в связанных файлах выше.*
