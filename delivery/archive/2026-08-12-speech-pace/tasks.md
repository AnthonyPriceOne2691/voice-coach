# Tasks: speech-pace

Порядок — vertical slice. Каждая задача оставляет дерево зелёным.

- [ ] **T1. Политика темпа.** `backend/app/orchestrator/pace.py`:
      `PaceRequest`, `detect`, `apply`, константы шага/коридора.
      Тесты `backend/tests/test_pace_policy.py` — таблица распознавания
      (P1, P2), длинный ответ со словом «speed» (P4), clamp с флагом границы (P3).

- [ ] **T2. Шов TTS.** `TextToSpeech.synthesize(..., length_scale=None)`;
      `PiperTts` использует переданное значение, иначе своё;
      новый `backend/app/voice/tts_paced.py` (`PacedTts`);
      `FakeTts` записывает `length_scale` каждого вызова.
      Тесты: адаптер подставляет свой темп, `set_scale` действует со следующего
      вызова, явный аргумент перекрывает.

- [ ] **T3. Реплики подтверждения.** `data/prompts/templates/pace_slower.txt`,
      `pace_faster.txt`, `pace_slowest.txt`, `pace_fastest.txt`.
      Тест: ни одна из них не задевает `data/contracts/interview_forbidden.txt`
      (L24 — иначе на границе Генри онемеет).

- [ ] **T4. Мета-ход.** `ws_voice`: сессионный `PacedTts`, ветка в `_run_turn`,
      `_handle_pace_request`; последняя реплика агента из `flow.buffer`;
      мета-ход в транскрипт со `state=PACE_REQUEST`, `question_id=None`.
      Тесты в `test_ws_voice.py`: P1 (темп, состояние, отсутствие вызова LLM,
      дословный повтор), P2, P7 (review), P9 (пометка в транскрипте).

- [ ] **T5. Хранение.** `speech_length_scale` в `DEFAULTS`, дефолт из конфига
      параметром конструктора `SettingsRepository`; чтение при старте сессии.
      Тесты: P5 (значение переживает сессию и попадает в интро новой).

- [ ] **T6. Валидация REST.** 422 на значение вне коридора и на нечисловое.
      Тест в `test_rest_api.py`: P6.

- [ ] **T7. Мета-ходы мимо summary.** Фильтр в `_render_transcript`
      (`summary/service.py`). Тест: P9 — просьба не попадает в промпт R1.

- [ ] **T8. Канон.** doc 15 (ключ в JSON настроек), doc 17 (строка в таблице
      Settings), doc 12 (значение `state` для мета-хода), doc 04 (мета-ход не
      двигает состояние); концепты OKF `orchestrator-owns-structure.md` и
      `sentence-streaming.md` + `knowledge/log.md`.

- [ ] **T9. Гейты.** `./scripts/run_checks.sh`, фронт не тронут — но `npm test`
      прогнать, чтобы это утверждение было замером, а не предположением.

- [ ] **T10. Живой замер (P8).** Полный ход на `speech_length_scale=1.60`,
      время до первого аудио-чанка, порог 3.0 s (doc 20). Прогон реальным
      стеком; результат — в `verify-report.md`, блок «Исполнение рисковых путей».

- [ ] **T11. Handoff.** `verify-report.md`, `decisions.md`, метрики,
      `merge_guard.sh`, архив + строка в `delivery/archive/INDEX.md`.
