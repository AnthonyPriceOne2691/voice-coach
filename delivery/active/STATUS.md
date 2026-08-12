# Active delivery status

- **slug:** expressive-speech
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** feature
- **repro_test:** n/a (kind=feature)
- **diagnosis:** n/a reason=не багфикс; причины ровности измерены спайком до спеки, гипотез не требовалось
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-13) reason=вариант озвучен образцами и выбран на слух (D: интонация + ритм + паузы, тот же голос); отдельно подтверждено, что пауза ставится перед каждым чанком кроме первого (без задержки перед микрофоном) и что параметры живут в конфиге, а не в REST
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=фронт не тронут; оракул бэкенда — pytest
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-expressive (ветка feat/expressive-speech)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=noise_scale и noise_w_scale — существующие поля SynthesisConfig, тишина собирается модулем wave из stdlib
- **runtime_paths:** backend/app/voice/tts_piper.py
  <!-- §12.6: слышимость платформа подтверждает звуком, а не кодом ошибки.
       Тест увидит нужное число нулевых сэмплов и останется зелёным при любом
       качестве звучания — значит нужен живой прогон и уши (E6, E7). -->
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** E6 и E7 подтверждены в живой сессии — Генри слышимо живее
  прежнего, между предложениями есть дыхание, речь не звучит рвано, и ожидание
  до первого звука на слух не выросло
- **observe_until:** 2026-08-27
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Речь звучала «как компьютер» по двум измеренным причинам: голос Генри настроен
на `noise_scale: 0.333` — вдвое ниже стандартной вариативности интонации, а
между предложениями не было паузы вообще (`AudioQueue` ставит чанки встык).
Обе чинятся на бэкенде и стоят 1 ms на предложение.

Пункт 1 плана после 2026-08-13.
