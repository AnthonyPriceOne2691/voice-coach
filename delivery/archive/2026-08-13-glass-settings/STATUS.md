# Active delivery status

- **slug:** glass-settings
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** feature
- **repro_test:** n/a (kind=feature)
- **diagnosis:** n/a reason=не багфикс; экран отсутствует, а не сломан
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-13) reason=экран Settings нарисован на макете поставки 1 и утверждён вместе с ним; состав настроек (темп, длительность, порог тишины, live-транскрипт) и решение НЕ выносить просодию в UI подтверждены отдельно
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build`
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-ui3 (ветка feat/glass-settings)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** max_loc_diff=1200 reason=723 строки из 1148 — сгенерированный package-lock.json трёх dev-зависимостей, поставленных по решению человека; рукописного кода ~440 строк, файлов 11 из 25. Lock-файл blast radius продукта не меняет — кандидат в список исключений §3.4 наравне с механикой контура by=human:anthony
- **new_dependency:** jsdom reason=компонентным тестам нужен DOM; до этой поставки во фронте были только логические тесты, и поведение разметки (один PATCH на отпускание, показ 422) проверить было нечем by=human:anthony
- **new_dependency:** @testing-library/react reason=рендер компонента и запросы к нему по роли; выбран как стандарт для React вместо enzyme и ручного ReactDOM by=human:anthony
- **new_dependency:** @testing-library/dom reason=peer-зависимость @testing-library/react, ставится явно, чтобы версия была видна в package.json by=human:anthony
- **runtime_paths:** frontend/src/styles/
  <!-- §12.6: экран отказывает пикселями, а не кодом ошибки — нужен браузер.
       `vite.config.ts` СНЯТ из списка сознательно: с 2026-08-12 забытое правило
       прокси ловится тестом-сторожем (`api.test.ts` сверяет префиксы `api.ts` с
       ключами `server.proxy`), то есть отказ этого пути ВИДЕН машине. Рисковым
       он был ровно до появления сторожа — в этом и был смысл его завести. -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** S1 и S6 подтверждены в использовании — темп выставляется
  мышью, значение переживает перезагрузку и слышно в следующей сессии
- **observe_until:** 2026-10-31
  <!-- Перенесено 2026-10-01 с 2026-08-27 решением human:anthony: наблюдение не проведено вовремя, и просрочка с 30.09 блокировала pre-push и job delivery в CI (приёмка 01.10). Сигнал выше не проверен — проверить в использовании и записать observed.md до новой даты. Наблюдение уже дало одно расхождение вне своего сигнала: ползунок порога тишины не доходил до VAD — поставка vad-silence-setting. -->
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Последняя из трёх поставок переработки интерфейса. Настройка темпа речи
существует, документирована, валидируется и меняется голосом — и при этом
невидима: посмотреть или выставить её можно было только `curl`. Экран Settings
закрывает это и заодно даёт длительность интервью, порог тишины и
live-транскрипт, лежавшие в базе без способа их изменить.
