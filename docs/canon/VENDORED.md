# Vendored canon snapshot

Снимок канон-стека, закоммиченный в репозиторий по варианту **C** из
`AGENT_STACK.md` §7.1 (`stack-selftest: ci (vendored)`).

| | |
|---|---|
| **Vendored at** | 2026-07-28 |
| **Upstream (рабочая копия человека)** | `Prepare/` в корне репо — **не коммитится** |
| **Версии** | `delivery@1.11` · `cqg@1.7` · `okf@1.5` · `stack-map@1.7` |

## Зачем копия

Каноны живут у человека в `Prepare/` и в git не попадают. Тогда CI их не видит,
`stack_selftest.py` в CI невозможен, и инвариант «payload канонов не сломан»
остаётся непокрытым (§7.1). Копия здесь закрывает ровно это: CI проверяет её.

## Что проверяется

`scripts/lint/check_canon_vendor.sh` (подключён к pre-commit и CI):

1. `SHA256SUMS` сходится с содержимым `docs/canon/*.md` — копию не правили на месте.
2. `scripts/stack_selftest.py docs/canon` — все фенсы парсятся, версии в шапках
   совпадают с таблицей §1 карты.
3. **Локально** (когда `Prepare/` существует) — побайтовый diff копии с upstream.
   В CI `Prepare/` физически нет, и этот шаг пропускается.

## ⚠ Известный остаток

Шаг 3 в CI непроверяем: upstream там отсутствует. То есть **дрейф
`Prepare/` → `docs/canon/` ловится только на машине человека**. Это цена варианта
C, записанная явно (`delivery/STACK-ACCEPTANCE.md` → «Остатки»), а не умолчанная.

## Как обновлять после правки канонов

```bash
cp Prepare/*.md docs/canon/
(cd docs/canon && shasum -a 256 *.md > SHA256SUMS)
python3 scripts/stack_selftest.py docs/canon
```

Версии в шапках изменились → обнови `stack:` в `delivery/CONSTITUTION.md` и
`delivery/active/STATUS.md`, иначе репозиторий врёт о том, какую ревизию канона он получил.
