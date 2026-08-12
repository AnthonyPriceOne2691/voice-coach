# Eval smoke — this shipment

Derived from spec acceptance (C1–C6). Run during verify.

## Оракулы поставки

- [x] **C1** `curl` через dev-сервер: `/sessions/interviews` и `/vocabulary`
      отдают `content-type: application/json` и тело `{"items":…}` —
      до фикса было 200 и `<!doctype html>`
- [x] **C3** браузер, вкладка Useful Words: «Nothing here yet — words are added
      automatically after each review» вместо «Failed to load»
- [x] **C4** тесты: HTML-ответ даёт ошибку с причиной; ответ 500 остаётся
      обычной ошибкой бэкенда
- [x] **C5** тест-сторож: на текущем коде до фикса красный и называет
      непокрытые префиксы (`['/sessions', '/vocabulary']`); отдельным тестом
      проверено, что сторож не всегда-зелёный
- [x] **C6** `npm run build` + `npx vitest run` — 18 тестов (было 14), сборка
      зелёная
- [~] **C2 частично** браузер, вкладка History: грузится и показывает сессию,
      закрытую разрывом посередине хода (`Aug 12, 04:33 PM · 34 s ·
      in_progress`). **Но буквальное «видно время окончания» нынешним UI не
      проверяется:** `HistoryPage` рендерит `started_at` и `duration_sec`, а
      `ended_at` не показывает нигде. И `duration_sec` считается сервером даже
      при пустом `ended_at` (замер до фикса: `duration_sec: 33` при
      `ended_at: null`), то есть по списку History отличить закрытую сессию от
      брошенной нельзя. Это НЕ дефект этой поставки и не её правка —
      наблюдаемость UI, вынесено в остатки

## Продуктовые оракулы (не должны шелохнуться)

- [x] `bash delivery/evals/smoke/run.sh` — S1–S7 ok
- [x] backend: 93 теста, покрытие 93.03% (бэкенд не тронут)
- [x] `pre-commit run --all-files` — 28 хуков, 0 провалов

## Живой прогон (ручной, вне CI)

Выполнен браузерным стендом: сессия создана прогоном `drive2.py` (закрытие
вкладки посередине хода), затем открыты вкладки History и Useful Words.
Снимки — `b-05-history.png`, `b-06-words.png` в scratchpad сессии.
