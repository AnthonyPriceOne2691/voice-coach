# Eval smoke — this shipment

Derived from spec acceptance (B1–B6). Run during verify.

## Оракулы поставки

- [x] **B1** разрыв посередине хода → из `ws_session` ничего не вылетает,
      `status = in_progress`, непустой `ended_at`, транскрипт `["agent", "user"]`
      (тест `test_disconnect_during_turn_finishes_session`)
- [x] **B2** тот же тест на коде ДО фикса → красный **3 из 3**, сообщение
      `RuntimeError('Cannot call "send" once a close message has been sent.')`
- [x] **B3** в логе нет `voice turn failed` — разрыв не считается отказом хода
- [x] **B4** живой клиент по-прежнему получает recoverable-ошибки
      (`test_stt_empty_recoverable`, `test_decode_failure_is_recoverable`)
- [x] **B5** разрыв в состоянии ожидания не сломан
      (`test_disconnect_without_end_session_finishes_flow`)
- [x] **B6, половина данных** браузер: закрытие вкладки в `Thinking…` →
      `ended_at` заполнен, **2 из 2**; в логе 0 необработанных исключений
- [ ] **B6, половина UI** — НЕ проверена: History не грузится из-за
      постороннего дефекта прокси Vite (`/sessions` не проксируется). Решение
      человека: отдельная поставка. Пробел назван в verify-report

## Продуктовые оракулы (не должны шелохнуться)

- [x] `bash delivery/evals/smoke/run.sh` — S1–S7 ok
- [x] `pytest` — 93 теста, покрытие 93.03% (гейт 85)
- [x] linux-контейнер, 5 прогонов сьюта — 0 висов, 0 падений
- [x] `npm run build` + фронтовые тесты — фронт не тронут, сборка зелёная

## Живой прогон (ручной, вне CI)

**Выполнен** — и именно он нашёл этот дефект. Стенд: Chromium 151 по CDP,
страница приложения, её VAD/MediaRecorder/ws, whisper.cpp, qwen2.5:14b-instruct,
Piper, SQLite; имитирован только микрофон (`getUserMedia` отдаёт поток из
`AudioContext`, потому что штатный флаг Chromium
`--use-file-for-fake-audio-capture` в этой сборке даёт цифровую тишину —
замер: `peak_rms 0`, `−180 dBFS`).

Стенд живёт в scratchpad сессии и **в репозиторий не попал** — это остаток:
следующий такой прогон придётся собирать заново.
