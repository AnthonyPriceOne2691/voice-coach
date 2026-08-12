# Verify report

**Date:** 2026-08-12
**Verifier:** agent:claude-code (прогоны) + human:anthony (приёмка ветки)
**asserts_reviewed_by:** n/a (все утверждения ведут к одобренным примерам)
**Commit:** ветка `fix/dev-proxy`

## Что чинилось

History и Useful Words не работали в единственном поддерживаемом запуске
(`./scripts/dev.sh`): Vite не проксировал `/sessions` и `/vocabulary`, запрос
уходил в SPA-fallback и возвращал HTML с кодом 200. Разбор —
`active/diagnosis.md`.

**Не работали никогда, и это замер:** `vite.config.ts` создан 2026-07-03
(`66792a2`) с правилом `/api`; `git log -p` по файлу показывает, что
`/sessions` и `/vocabulary` в нём не появлялись ни разу. `lib/api.ts`, который
их зовёт, добавлен 2026-07-05 (`d9dfb88`). 38 дней при зелёных сборке, тестах и
гейтах.

## Assertion digest (ревью ожиданий, не кода)

Вывод `scripts/lint/assert_digest.sh` дословно:

```
Новых/изменённых утверждений: 6, из них без ссылки на пример спеки: 0.

C5	expect(client.length).toBeGreaterThan(0); // C5 — регулярка не разучилась читать пути
C5	expect(client.filter((p) => !proxied.includes(p))).toEqual([]); // C5
C5	expect(client).toEqual(["/reports"]); // C5
C5	expect(client.filter((p) => !proxied.includes(p))).toEqual(["/reports"]); // C5
C4	await expect(request("/sessions/interviews")).rejects.toThrow(/не JSON.*прокси/i); // C4
C4	await expect(request("/sessions/interviews")).rejects.toThrow(/500/); // C4

asserts_without_example: 0
```

Первый прогон дайджеста дал `asserts_without_example: 6`: id стояли у
`describe`, а не у утверждений. Привязаны отдельным коммитом.

## Shape oracles

- [x] PASS — `pre-commit run --all-files`: 28 хуков, **0 провалов**
- [x] PASS — `tsc -b` + eslint + prettier (в составе pre-commit)
- [x] PASS — module size ≤ 500 LOC

## Behavior oracles

- [x] PASS — **C1** через dev-сервер `/sessions/interviews` и `/vocabulary`
      отдают `content-type: application/json`; до фикса — `text/html`
- [x] PASS — **C3** вкладка Useful Words показывает пустое состояние, не ошибку
- [x] PASS — **C4** два теста: HTML-ответ даёт ошибку с причиной («ответ не
      JSON … проверь server.proxy»), ответ 500 остаётся обычной ошибкой бэкенда
- [x] PASS — **C5** тест-сторож. На коде ДО фикса красный:
      `expected [ '/sessions', '/vocabulary' ] to deeply equal []`. Отдельный
      тест доказывает, что сторож не всегда-зелёный
- [x] PASS — **C6** `npm run build` зелёный, `vitest` — **18 тестов** (было 14)
- [~] **C2 ЧАСТИЧНО.** History грузится и показывает сессию, закрытую разрывом
      посередине хода: `Aug 12, 04:33 PM · 34 s · in_progress`. Буквальное
      «видно время окончания» нынешним UI **не проверяется**: `HistoryPage`
      рендерит `started_at` и `duration_sec`, `ended_at` не показывает нигде
      (`HistoryPage.tsx:103,153`). Хуже: `duration_sec` сервер считает и при
      пустом `ended_at` (замер до фикса: `duration_sec: 33` при
      `ended_at: null`), поэтому по списку History брошенную сессию от закрытой
      не отличить. Это наблюдаемость UI, а не прокси — в остатки, не в эту
      поставку (`decisions.md` D5)
- [x] PASS — backend: 93 теста / 93.03% — бэкенд не тронут ни строкой
- [x] PASS — `delivery/evals/smoke/run.sh`: S1–S7 ok

## Исполнение рисковых путей (§12.6)

`runtime_paths: frontend/vite.config.ts` — конфиг dev-сервера. Один путь, порог
не превышен. Отказ на нём не виден ни сборке, ни тестам: зелёными были ВСЕ
гейты, потому что ни один этот путь не исполнял. Прогоны исполнены
**at=2026-08-12**.

| Что исполнял | Чем | Что увидел | at |
|---|---|---|---|
| REST через dev-сервер, ДО фикса | `fetch` из страницы по CDP | `200`, тело `<!doctype html>` | 2026-08-12 |
| он же, ПОСЛЕ фикса | `curl -D -` и `fetch` из страницы | `content-type: application/json`, тело `{"items":…}` | 2026-08-12 |
| вкладка History в браузере | Chromium 151 по CDP, снимок `b-05-history.png` | сессия в списке; до фикса «Failed to load history» | 2026-08-12 |
| вкладка Useful Words | тот же стенд, снимок `b-06-words.png` | пустое состояние; до фикса «Failed to load» | 2026-08-12 |

⚠ **Первая проверка этого пути была неверной** и едва не закрыла тему:
`curl -o /dev/null -w '%{http_code}'` показал `200`, что выглядело как рабочий
прокси. SPA-fallback отвечает 200 на что угодно — смотреть надо тело или
content-type. Записано уроком.

## Ревью рисковых мест (§12.5)

0. **Что смотрел:** дифф целиком — `frontend/vite.config.ts`,
   `frontend/src/lib/api.ts` (`request<T>`), новые
   `frontend/src/lib/devProxy.ts` и `frontend/src/lib/api.test.ts`,
   `docs/15-api-websocket-spec.md`.

1. **`request<T>` теперь бросает на не-JSON.** Риск — сломать вызов, который
   легально получает не-JSON. Проверено: единственный такой случай —
   `204 No Content`, и он обработан раньше проверки; тела без содержимого идут
   через отдельный `requestNoContent`, который вообще не читает тело.
2. **Сторож разбирает исходники регуляркой.** Может дать ложное срабатывание
   при необычной записи пути. Смягчено: сверяются только префиксы (первый
   сегмент), и есть тест `expect(client.length).toBeGreaterThan(0)` — если
   регулярка перестанет находить пути вообще, сторож покраснеет, а не
   позеленеет молча.
3. **Убрано правило `/api`.** Если что-то звало его в обход `lib/api.ts` —
   сломается. Проверено `grep`: вхождений `/api` в `frontend/src` нет.
4. **Прокси — только dev.** Продовая сборка о нём не знает; `npm run build`
   зелёный, содержимое `dist` от правки не зависит.
5. **Производительность, безопасность, деньги — не затронуты:** правка
   маршрутизации локального dev-сервера, внешних вызовов нет.
6. **Бэкенд и протокол doc 15** не тронуты: пути REST не переименовывались,
   изменена только строка Base URLs, описывающая dev-прокси.
7. **Цепочка гейтов** не тронута; добавлен один тест внутри существующего
   `npm test`.

## Spec coverage gaps

- **C2 частично** — см. выше: UI не рендерит `ended_at`. Остаток наблюдаемости.
- Браузерные проверки (C1–C3) исполняются стендом из scratchpad сессии,
  которого нет в репозитории. В CI их нет и не будет — назван остаток.
- **Реляционного оракула в смысле §6.5 (`@given` / `fc.property`) нет, и
  предупреждение гейта законно.** Возражение по существу: главный тест этой
  поставки УЖЕ реляционный по форме — он сверяет два артефакта между собой
  (`префиксы api.ts ⊆ ключи server.proxy`) и не содержит ожидаемого значения,
  которое можно подогнать. Чего в нём нет — перебора входов раннером; чтобы он
  появился, нужен `fast-check`, то есть новая зависимость ради одного теста.
  Не ставлю, но и не делаю вид, что предупреждение закрыто.

## Verdict

- [x] **READY FOR HANDOFF**
- [ ] NEED CONVERGE
- [ ] BLOCKED

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 8 code (+8 process docs) / +106/-4 (net +102) |
| commits | 2 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — delivery/active/spec.md (новый оракул) |
| implement_retries | **1** — тест читал исходники через `node:fs` и уронил `npm run build` (`Cannot find module 'node:fs'`, @types/node в проекте нет). Переписан на `?raw` самого Vite; сам фикс прокси переделке не подвергался |
| verify_fails_before_green | заполняется после первого прогона CI на ветке |
| est_token_or_cost | n/a — не измерялось; локальный инструмент, внешних платных вызовов нет |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
