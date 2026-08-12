# Tasks: expressive-speech

- [ ] **T1. Интонация и ритм.** `Settings.piper_noise_scale`, `Settings.piper_noise_w`;
      `PiperTts` кладёт их в `SynthesisConfig`. Тест E1 — двойником `PiperVoice`.
- [ ] **T2. Дыхание.** `backend/app/voice/prosody.py::lead_in`. Тесты E2, E3:
      длительность выросла ровно на паузу, WAV читается, формат сохранён.
- [ ] **T3. Вставка.** Счётчик чанков в `_send_audio`, сброс на `final=True`.
      Тесты E2/E4/E5 на уровне WS: второй чанк длиннее, первый нет, в конце
      лишней тишины нет, у одиночных реплик паузы нет.
- [ ] **T4. Канон.** doc 03 (просодия и пауза в конвейере), doc 19 (замеры),
      concept `sentence-streaming.md` + `log.md`.
- [ ] **T5. Гейты.** `run_checks.sh`; jscpd до/после; diff-coverage с env;
      `okf_sync_gate` **после** коммита (L35); `npm test` — фронт не тронут.
- [ ] **T6. Живой перезамер (E6).** Полный ход настоящим стеком, время до
      первого чанка, порог 3.0 s. Результат — в verify-report.
- [ ] **T7. Handoff.** verify-report, decisions, метрики, `merge_guard.sh`,
      архив + строка в `INDEX.md`.
