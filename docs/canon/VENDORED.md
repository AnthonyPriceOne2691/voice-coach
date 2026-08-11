# Vendored canon snapshot

Снимок канон-стека, закоммиченный в репозиторий по варианту **C** из
`AGENT_STACK.md` §7.1 (`stack-selftest: ci (vendored)`).

| | |
|---|---|
| **Vendored at** | 2026-08-11 |
| **Upstream (рабочая копия человека)** | `Prepare/` в корне репо — **не коммитится** |
| **Версии** | `delivery@1.68` · `cqg@2.01` · `okf@1.15` · `stack-map@1.47` |

## Зачем копия

Каноны живут у человека в `Prepare/` и в git не попадают. Тогда CI их не видит,
`stack_selftest.py` в CI невозможен, и инвариант «payload канонов не сломан»
остаётся непокрытым (§7.1). Копия здесь закрывает ровно это: CI проверяет её.

## Что проверяется

`scripts/lint/check_canon_vendor.sh` (подключён к pre-commit и CI):

1. `SHA256SUMS` сходится с содержимым снимка — копию не правили на месте.
   В манифесте не только `*.md`, но и обе части селфтеста.
2. `scripts/stack_selftest.py docs/canon` — все фенсы парсятся, версии в шапках
   совпадают с таблицей §1 карты.
   ⚠ Селфтест — **комплект из двух файлов**: `stack_selftest.py` импортирует
   `selftest_sizes.py` (планка 300 строк, CQG §9.1a п.5). Без второго файла он
   падает на импорте, то есть шаг 2 не выполняется вовсе. Оба лежат и в
   `scripts/`, и в снимке.
3. **Локально** (когда `Prepare/` существует) — побайтовый diff копии с upstream.
   В CI `Prepare/` физически нет, и этот шаг пропускается.

## ⚠ Известный остаток

Шаг 3 в CI непроверяем: upstream там отсутствует. То есть **дрейф
`Prepare/` → `docs/canon/` ловится только на машине человека**. Это цена варианта
C, записанная явно (`delivery/STACK-ACCEPTANCE.md` → «Остатки»), а не умолчанная.

## Как обновлять после правки канонов

```bash
cp Prepare/*.md Prepare/stack_selftest.py Prepare/selftest_sizes.py docs/canon/
cp Prepare/stack_selftest.py Prepare/selftest_sizes.py scripts/   # рабочая копия гейта
(cd docs/canon && shasum -a 256 AGENT_DELIVERY_HARNESS.md AGENT_STACK.md \
   CODE_QUALITY_GATES.md OKF_KNOWLEDGE_BUNDLE.md selftest_sizes.py stack_selftest.py \
   > SHA256SUMS)                                   # VENDORED.md — свой, не из upstream
python3 scripts/stack_selftest.py docs/canon
bash scripts/lint/check_canon_vendor.sh
```

**Обновление контура — это не то же, что развёртывание.** Копировать payload
поверх адаптированного запрещено: порядок и разбор природы расхождений — CQG
§5.5, объявления адаптаций — `scripts/lint/adapted.json`.

Версии в шапках изменились → обнови `stack:` в `delivery/CONSTITUTION.md` и
`delivery/active/STATUS.md`, иначе репозиторий врёт о том, какую ревизию канона он получил.
