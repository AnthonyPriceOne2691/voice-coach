# Active delivery status

- **slug:** liquid-glass-ui
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** L
- **kind:** feature
- **repro_test:** n/a (kind=feature)
- **diagnosis:** n/a reason=не багфикс; диагноз интерфейса снят снимками «до» и записан в spec
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-13) reason=направление утверждено МАКЕТОМ до кода (отрисован и показан), плюс три решения: как в макете, все три экрана + новый Settings, орб живёт по состоянию
- **human_ok_plan:** yes (by=human:anthony, at=2026-08-13) reason=четыре экрана одной поставкой (общий слой всё равно задевает всё; разрез дал бы три окна наблюдения и половинчатый интерфейс между ними); CSS без новых зависимостей; голосовой тракт не трогается; отдельно подтверждено расширение payload `state` тремя полями счётчика вопросов с правкой doc 15
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build` — правка фронта, собранное меняется (§6.5a)
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-ui (ветка feat/liquid-glass-ui)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=стекло и анимации делаются CSS; router, Tailwind и framer-motion отклонены в plan.md с причинами
- **runtime_paths:** frontend/src/styles/, delivery/evals/browser/
  <!-- §12.6: экран — путь, чей отказ виден пикселями, а не кодом ошибки.
       `npm test` зелён при полностью сломанной вёрстке. Значит нужен браузер
       и снимки (U1-U9), а также живой прогон сессии (U12). -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** U12 подтверждён в живой сессии — интервью запускается из
  нового интерфейса, орб отражает состояние, транскрипт читается как диалог,
  Settings меняет темп речи и значение переживает перезагрузку
- **observe_until:** 2026-08-27
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Интерфейс работает, но у него визуальный вес обратен важности: самое крупное на
экране — название приложения, пустая панель транскрипта занимает пол-экрана и
молчит, в History `Delete` того же веса, что главное действие, а экрана Settings
нет вовсе, хотя doc 17 его обещает и настройка темпа в REST уже есть.

Поставка перестраивает иерархию всех четырёх экранов и вводит визуальный язык
«жидкого стекла». Голосовой тракт не трогается вовсе.

Последний пункт плана после 2026-08-12.
