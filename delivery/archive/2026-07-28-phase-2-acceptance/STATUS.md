# Active delivery status

> ⚠ **ПРИПАРКОВАНА 2026-08-03, не закрыта.** Поставка стояла в фазе `specify` с
> 2026-07-28 с незакрытым блокером. Заархивирована по правилу «одна active-поставка»
> (Delivery §7.2), чтобы пропустить вперёд bootstrap контура `cqg@1.7 → 1.61`:
> диагностировать висящий тест на контуре 1.61 дешевле, чем на 1.7 — там судит
> мутационный гейт и `filterwarnings=["error"]` ловит незакрытые ресурсы, из-за
> которых такие висы обычно и случаются.
>
> **Блокер НЕ решён и переезжает в спеку следующей поставки** (после bootstrap'а):
> `backend/tests/test_ws_voice.py` виснет на ubuntu-runner, убивается
> `pytest-timeout` на 60 c; трейс стоит на `selector.select` / `lock.acquire`.
>
> **Строка «Джобы CI, gates, main-guard зелёные; красная только quality/delivery»
> ниже — НЕВЕРНА** и не была обновлена: замер 2026-08-03 на том же SHA даёт
> обратное — `quality`, `gates`, `main-guard` зелёные, красная `CI`. Учёт разошёлся
> с прогонами и об этом ничто не сказало; урок записан в `archive/INDEX.md` как L1.


- **slug:** phase-2-acceptance
- **stack:** delivery@1.11, cqg@1.7, okf@1.5
- **class:** M
- **phase:** specify
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** no
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **ci-oracles:** tooling
  <!-- CI есть (.github/workflows/quality.yml); гейт мержа — в репозитории
       (scripts/merge_guard.sh + pre-push + needs:). Серверной защиты ветки нет:
       приватный репо на бесплатном тарифе (rulesets = Team+, protection = Pro+).
       Остаток: force-push в main и обход админом ничем не закрыты — см.
       delivery/STACK-ACCEPTANCE.md → «Остатки». -->
- **worktree:** none (пока specify; на implement — ../voice-coach-wt-phase-2-acceptance)
- **hooks:** claude (scripts/hooks/, подключение вручную — см. delivery/README.md)
- **blockers:** CI красный — `test_decode_failure_is_recoverable` виснет на
  ubuntu-runner (`TestClient.__exit__` не дожидается portal-треда). Дефект
  предшествует стеку и держал прогоны main по 6 ч с 2026-07-05; локально не
  воспроизводится. Полный диагноз и лид — в `spec.md`, «In scope», первый пункт.
  Джобы `CI`, `gates`, `main-guard` зелёные; красная только `quality / delivery`.
- **waivers:** none
- **circuit_breakers:** defaults from docs/canon/AGENT_DELIVERY_HARNESS.md §3.4

## Контекст

Phase 2 объявлена code-complete 2026-07-05: оркестраторы, sentence-gated Contract
Enforcer, Mode 2, SQLite, History/Words UI, R1-summary + Vocabulary Bank; live
e2e-smoke (interview→review→summary→bank) пройден. **Не закрыто:** ручной UI-прогон
и два наблюдения из CLAUDE.md — качество R1-summary (артефакт в `translation_ru`)
и markdown-списки в wrap-up review.

Эта поставка закрывает Phase 2 приёмкой, а не новым кодом. Черновик — `spec.md`;
ждёт human OK, до него фаза не двигается (§3.3).

## Развёртывание стека (не эта поставка)

Канон-стек развёрнут 2026-07-28 отдельным bootstrap-коммитом. Bootstrap — это про
репозиторий, а не про поставку, поэтому он записан в `delivery/STACK-ACCEPTANCE.md`
(A.12), а не здесь.
