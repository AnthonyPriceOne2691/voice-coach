# Active delivery status

- **slug:** speech-pace
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** feature
- **repro_test:** n/a (kind=feature)
- **diagnosis:** n/a reason=не багфикс; дефект известен из спеки, гипотез не требовалось
- **phase:** handoff
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-12) reason=три продуктовых решения предъявлены ДО кода и подтверждены: подтверждение + дословный повтор без вызова LLM; темп переживает сессию (ключ в kv-настройках); шаг ±0.15 в коридоре 0.85–1.60
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=фронт не тронут (spec, Out of scope); бэкенд не собирается в артефакт, его оракул — pytest
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-wt-speech-pace (ветка feat/speech-pace)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** max_files_touched=32 max_loc_diff=850 reason=исходный перебор дают 9 тестовых файлов, 4 шаблона реплик и 4 дока при узком blast radius продукта (разбор двух вариантов с ценой — active/escalation.md); поднято с 30/800 до 32/850 после того, как ГЕЙТЫ потребовали ещё два файла: session_flow.py (консолидация дублей, снимок 1→0) и test_tts_piper.py (diff-coverage 48%→87%). Оба выросли из уже подписанных решений и улучшили код by=human:anthony
- **new_dependency:** none reason=темп — уже существующий параметр Piper (`SynthesisConfig.length_scale`), новых пакетов не требуется
- **runtime_paths:** backend/app/voice/tts_piper.py
  <!-- §12.6: слышимость темпа платформа подтверждает звуком, а не кодом ошибки.
       FakeTts запишет любое число и останется зелёным; значит нужен прогон
       живым Piper'ом с замером времени до первого чанка (P8, T10). -->
- **canon_drift_waiver:** knowledge/engineering/model-split.md reason=тронут summary/service.py — из промпта R1 отфильтрованы мета-ходы; разделение моделей (qwen в голосе, R1 offline) при этом не менялось ни в одну сторону by=human:anthony
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** P1, P4, P5 подтверждены в живой сессии — просьба замедлить
  слышимо меняет темп и не тратит вопрос, ответ со словом «speed» темп не трогает,
  значение переживает рестарт бэкенда
- **observe_until:** 2026-08-26
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Генри говорит с одним темпом на всё время жизни процесса, и просьба «speak
slower» сегодня не только не работает, но и **стоит пользователю вопроса**:
она уходит в оркестратор как ответ. Поставка делает просьбу о темпе мета-ходом:
темп меняется на лету и переживает сессию, состояние интервью не двигается,
подтверждение с дословным повтором звучит уже новым темпом и не зовёт LLM.

Пункт 1 плана после 2026-08-12.
