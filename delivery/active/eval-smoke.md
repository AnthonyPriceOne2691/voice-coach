# Eval smoke — shutdown-leaks

Derived from spec acceptance (E1–E5). Run during verify, 2026-10-25, на ветке
`fix/shutdown-leaks`, macOS, на пяти деревьях: поверх `main` `8d344d4` под нагрузкой
соседних сессий (load average 6–74), затем после слияний `5d7d7b7` (#48), `a97a621`
(#42), `84783b6` (#44) и `1fa99e5` (memory-guard) — в машине потише (2–8). Время
прогонов не показатель, детерминизм — показатель: вердикты оракулов на всех кругах
одинаковы.

## Оракулы поставки

- [x] **E1** разбор застрял внутри записи и не уложился в срок —
      `test_shutdown_cancellation.py::test_shutdown_waits_until_a_cancelled_summary_returns_its_connection`:
      до правки 5 из 5 красных (учёт: «выдано пулом и не возвращено» + «открыто и не
      закрыто»), после — зелёный, в логе ровно `shutdown: 1 summary task(s) cancelled
      by timeout`; мутации M1 (отмена без ожидания) и M2 (ожидание отмены со сроком) —
      красный 3 из 3, соседи зелёные
- [x] **E2** уборка ws-сессии застряла внутри итоговой записи —
      `test_shutdown_cancellation.py::test_shutdown_cancels_a_stuck_ws_cleanup_and_waits_for_it`:
      до правки 5 из 5 красных, после — зелёный, в логе ровно `shutdown: 1 ws
      cleanup(s) did not finish in time — cancelling`; мутации M3 (без отмены, как до
      правки), M4 (отмена без ожидания), M5 (ожидание отмены со сроком) — красный 3 из
      3; на деревьях с #42 к ним добавляется прохожий B5b от сборщика мусора (L89)
- [x] **Мутационный гейт** (#44) по двум изменённым файлам — 215 из 343 (62%) локально
      и 219 из 344 (63%) в CI при пороге 60%; в `aclose()` и `_drain` выживших нет (26
      убито, 4 timeout)
- [x] **E3** разбор, уложившийся в срок, дописан —
      `test_shutdown_summary.py::test_shutdown_waits_for_a_running_background_summary`
      зелёный без правки теста
- [x] **E4** зависшая модель не вешает гашение —
      `test_shutdown_summary.py::test_shutdown_gives_up_on_a_hung_summary_and_says_so`
      зелёный без правки теста: отмена теперь дожидается, и размотка из
      `HangingLlm.stream_chat` мгновенна
- [x] **E5** штатная уборка закрывает сессию —
      `test_ws_voice.py::test_disconnect_without_end_session_finishes_flow` и
      `test_ws_voice.py::test_disconnect_during_turn_finishes_session` зелёные без
      правки тестов

## Продуктовые оракулы (не должны шелохнуться)

- [x] `bash delivery/evals/smoke/run.sh` — см. verify-report, «Машинные гейты»
- [x] фронт не тронут — `git diff --stat origin/main -- frontend` пуст

## Отложено «по запускай»

- [ ] Живое гашение `./scripts/dev.sh` (Ctrl+C) после интервью с разбором: в логе
      backend `Application shutdown complete`, разбор виден в History, без `SAWarning`
      и `ResourceWarning` aiosqlite. Исполняет только штатный путь (задачи уложились в
      срок) — его покрывают E3 и E5; застрявшую запись живьём не воспроизвести.
      Нужен живой стек (ollama, whisper, Piper) — это сигнал наблюдения
      (`observe_signal`), а не условие закрытия.
