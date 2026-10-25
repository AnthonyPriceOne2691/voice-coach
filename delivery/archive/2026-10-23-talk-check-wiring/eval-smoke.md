# Eval / smoke: talk-check-wiring

| Пример | Оракул | Где | Статус |
|---|---|---|---|
| C2 | ошибка в реплике — заметка в базе с фрагментом из транскрипта | `test_ws_talk_check.py::test_error_is_noted_after_the_reply_with_the_recognized_fragment` | ✅ |
| C1, C4 | ничего не найдено — заметок нет, проверка посчитана | `test_ws_talk_check.py::test_clean_and_casual_speech_leave_no_note` | ✅ |
| C6 | кандидат про несказанное — заметки нет | `test_ws_talk_check.py::test_fix_of_words_that_were_not_said_is_dropped` | ✅ |
| C7 | та же ошибка дважды — одна заметка | `test_ws_talk_check.py::test_same_mistake_twice_gives_one_note` | ✅ |
| C8 | проверка ПОСЛЕ ответа, на том же префиксе; отмена репликой, концом и разрывом; просьбы не проверяются | `test_ws_talk_check.py` (5 тестов), `test_talk_checks.py` | ✅ |
| C9 | eval проверки речи | поставка talk-check-core, по «запускай» | — |

## Smoke

`delivery/evals/smoke/run.sh` — без изменений: проверка речи молчит (заметки только в
базу), путь звука прежний.
