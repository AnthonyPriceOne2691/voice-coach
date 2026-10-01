# Active delivery status

- **slug:** stand-selector-rot
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
  <!-- Версии main. Обновление до 1.79/2.20/1.17 живёт неслитым на ветке
       contour/update-2.15 — поставка на него не опирается. -->
- **class:** S
- **kind:** bugfix
- **repro_test:** `frontend/src/pages/InterviewPage.test.tsx` (сторож на крючок) + прогон `run.sh mid-turn`: до правки `start-button-not-found`, после — полный ход
- **diagnosis:** `delivery/active/diagnosis.md`
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** n/a (class S — mini-spec в tasks.md, §2.2)
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build`
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-stand (ветка fix/stand-selector)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **runtime_paths:** frontend/src/pages/InterviewPage.tsx
  <!-- §12.6: страница отказывает пикселями и разметкой, а не кодом ошибки.
       Крючок сторожит тест, но что кнопка на месте и стенд её нажимает —
       подтверждено живым прогоном браузера, а не сборкой. -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** `run.sh mid-turn` перед следующей демонстрацией доходит до
  `closed-mid-turn`, а не до `start-button-not-found`
- **observe_until:** 2026-10-31
  <!-- Перенесено 2026-10-01 с 2026-08-31 решением human:anthony: наблюдение не проведено вовремя, и просрочка с 30.09 блокировала pre-push и job delivery в CI (приёмка 01.10). Сигнал выше не проверен — проверить в использовании и записать observed.md до новой даты. -->
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Браузерный стенд — тот самый оракул, который нашёл три дефекта при зелёных
гейтах. С 2026-08-13 он **сам был сломан**: искал кнопку по подписи «Start Mock
Interview», а переработка интерфейса переименовала её в «Start interview». Прогон
честно краснел, но называл не ту причину — `mic-never-opened` — и тратил на это
5.5 минуты ожидания. Нашлось при подготовке к демонстрации.
