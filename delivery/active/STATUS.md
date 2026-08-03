# Active delivery status

- **slug:** contour-bootstrap-1.61
- **stack:** delivery@1.48, cqg@1.61, okf@1.12
- **class:** M
- **kind:** bootstrap
- **repro_test:** n/a reason=не bugfix, кода продукта не трогает
- **diagnosis:** n/a reason=не bugfix
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** no
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **ci-oracles:** tooling
  <!-- CI есть (4 workflow), гейт мержа в репозитории. Серверной защиты ветки нет:
       приватный репо на бесплатном тарифе. Остаток — STACK-ACCEPTANCE.md. -->
- **worktree:** none (bootstrap трогает дерево контура целиком, §7.2 шаг 6)
- **hooks:** claude (scripts/hooks/)
- **blockers:** `deps-audit` красный: `critical=1 high=1` на фронте, оба лечатся
  апгрейдом `vitest` до 4.1.10 — **semver-major**. По приёмке эта строка
  закрывается «auto + human, когда фикс semver-major»: решение за человеком, waiver
  требует `by=human:`. Два варианта с ценой — `escalation.md` (§12.3). Оба пакета
  **dev-only**, в прод-бандл не попадают — проверено `npm run build`.
- **waivers:** none
- **new_dependency:** pip-audit reason=deps-audit без него не судит (гейт §3); альтернатива safety отвергнута — платная база by=human:anthony
- **new_dependency:** mutmut reason=единственный оракул «тесты утверждают» (§3.7); 2.x мёртв — нет --version, падает на py3.13+ by=human:anthony
- **new_dependency:** detect-secrets reason=secrets-гейт §2.7; хук уже был в конфиге, инструмент стоял мимо манифеста by=human:anthony
- **new_dependency:** import-linter reason=направление зависимостей §2.3; стоял мимо манифеста by=human:anthony
- **new_dependency:** pytest-timeout reason=уже стоял транзитивно, закреплён явно — вис теста режется на 60 c by=human:anthony
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** contour_doctor.py даёт DEAD=0 и SKIP=0 на этом репозитории
- **observe_until:** 2026-08-10
- **circuit_breakers:** exempt (kind: bootstrap, §3.4 — развёртывание трогает всё
  дерево контура и не режется на части)

## Что это

Обновление развёрнутого контура `cqg@1.7 · delivery@1.11 · okf@1.5` →
`cqg@1.61 · delivery@1.48 · okf@1.12`. Не рефреш: **ни один из 21 скрипта не
совпадал байт-в-байт**, восемь отсутствовали целиком (`complexity`, `deps-audit`,
`mutation`, `new-dependency`, `ci-status`, `gate_value`, `assert_digest`,
`contour_doctor`).

Почему сейчас и почему впереди `phase-2-acceptance`: та стояла с 2026-07-28 на
блокере (висящий `test_ws_voice.py`), и диагностировать вис на контуре 1.61 дешевле —
там судит мутационный гейт и `filterwarnings=["error"]` ловит незакрытые ресурсы,
типичную причину таких висов. Поставка припаркована по правилу «одна active»
(§7.2), блокер переезжает в спеку следующей.

## Замер ДО (contour_doctor.py на cqg@1.7)

`AUTO 14 · WEAK 3 · ABSENT 7 · TOOL 0 · SKIP 3 · DEAD 0`

Лжи не было, но `SKIP 3` — и это не слепота доктора: на 1.7 у `check_grep_gate.sh`
и `check_ast_gate.py` ещё нет `--list-rules`, поэтому перечислить их правила нечем.
**Два несущих гейта были непроверяемы в принципе.**

## Своё, что канон не поставляет — сохранить, а не снести

- `scripts/lint/check_canon_vendor.sh` — вариант C §7.1: следит за копией канонов
  в `docs/canon/`. Роль в карте ролей канона отсутствует; сохраняется как есть.
- `.github/workflows/canon-freshness.yml` — расписание на свежесть копии.
- `scripts/check_module_size.py` — своё, вне контура.

⚠ **Исправление собственной ошибки по ходу bootstrap'а.** Сначала я записал, что
`CANON_UPSTREAM=Prepare` — относительный путь, которого в репозитории нет, и потому
шаг 3 (сверка с upstream) не выполняется. **Это неверно:** каталог `Prepare/` в
репозитории ЕСТЬ, он под `.gitignore` (строка 30), и сверка работает. Что верно:
копия в `Prepare/` была на `cqg@1.7` и разъехалась бы с `docs/canon/` — обновлена
вместе с ней. То есть у варианта C **две** копии канонов, и обе надо двигать.
