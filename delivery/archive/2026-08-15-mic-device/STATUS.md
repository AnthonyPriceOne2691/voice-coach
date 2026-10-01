# Active delivery status

- **slug:** mic-device
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** feature
- **repro_test:** n/a (kind=feature)
- **diagnosis:** n/a reason=не багфикс; настройки нет, а не сломана
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-15) reason=спека утверждена целиком; отдельно решено ДОБАВИТЬ проверку уровня («Test» + существующий MicLevelMeter), потому что выбор входа вслепую не отвечает на вопрос «а он вообще слышит»
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** `cd frontend && npm run build`
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-mic (ветка feat/mic-device)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **runtime_paths:** frontend/src/hooks/useVoiceSession.ts
  <!-- §12.6: доступ к железу. jsdom не имеет ни устройств, ни разрешений, и
       единственное, что не проверяется ничем машинным, — звук с ФИЗИЧЕСКОГО
       входа в живой сессии.
       `SettingsPage.tsx` был объявлен вторым и СНЯТ по ходу поставки: сценарий
       стенда `run.sh mic` покрыл экран целиком в настоящем Chromium (имена,
       сохранение выбора, видимый отказ при пропаже входа, живая полоска), то
       есть отказ этого пути стал виден машине. Это тот же шаг, что снятие
       `vite.config.ts` в поставке glass-settings (L47): список рисковых путей
       пересматривается ПОСЛЕ каждого нового оракула, а не носится как шрам. -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** M9 на физическом железе — вход, выбранный на экране,
  действительно слышен в сессии; сохранённый `deviceId` не протух между запусками
- **observe_until:** 2026-10-31
  <!-- Перенесено 2026-10-01 с 2026-08-29 решением human:anthony: наблюдение не проведено вовремя, и просрочка с 30.09 блокировала pre-push и job delivery в CI (приёмка 01.10). Сигнал выше не проверен — проверить в использовании и записать observed.md до новой даты. -->
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Последняя строка таблицы Settings из doc 17, оставшаяся с крестиком. Микрофон
сейчас — всегда системный по умолчанию; при смене железа вход уезжает молча, а
порог VAD −50 dBFS откалиброван под конкретный тракт, поэтому «тихое» устройство
выглядит как сломавшийся агент, а не как выбор входа.
