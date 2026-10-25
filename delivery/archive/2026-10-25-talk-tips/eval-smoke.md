# Eval / smoke: talk-tips

| Пример | Оракул | Где | Статус |
|---|---|---|---|
| C14 | после ответа одна подсказка по шаблону: порядок чанков, две реплики Генри, `TIP` в транскрипте, `spoken: true`; модель её не видит; вопрос после отказа — Генри, а не подсказка | `test_ws_talk_tips.py::test_note_is_spoken_after_the_reply_and_never_reaches_the_model`, `test_talk_tips.py` (шаблон), `test_ws_sentinels.py::test_tip_built_from_the_users_words_stays_out_of_the_log` | ✅ |
| C15 | без заметки — только ответ | `test_ws_talk_tips.py::test_correction_by_the_model_is_cut_and_without_a_note_no_tip`, `test_talk_checks.py::test_no_check_means_no_tip` | ✅ |
| C16 | поправку модели режет енфорсер до озвучки; беседа об английском и причины проходят; шаблон подсказки ловит I3-H4; у каждого `forbid_patterns` свой список | `test_contract_talk_corrections.py`, `test_talk_tips.py::test_tip_template_is_plain_english_that_only_the_code_may_say`, WS-тест выше | ✅ |
| C17 | проверка, кончившаяся пока звучит ответ, — подсказка; не успела — подсказки нет, `listening` приходит; на сроке проверка не снимается, поздняя заметка — в списке; срок = конец звука + 1.5 s | `test_ws_talk_tips.py` (2 теста), `test_talk_checks.py::test_late_check_gives_no_tip_but_is_not_cancelled_and_lands_in_the_list`, `test_talk_tips.py::test_tip_waits_for_the_check_until_the_reply_ends_plus_grace`, `test_playback_ends_where_the_client_queue_ends` | ✅ |
| C9 | eval проверки речи | поставка talk-check-core (`delivery/evals/talk-check/`), по «запускай» | — |

## По «запускай» (живой стек, не прогонялось)

- Первый звук хода после подсказки ≤ 3 s (инвариант 3, класс L78/L80): подсказка в
  историю не попадает, префикс тот же — подтвердить замером на qwen2.5.
- C17 на живом стеке: доля заметок со `spoken: false` за 10-минутный разговор
  (проверка не успела к концу ответа + 1.5 s) и пауза перед `listening` на слух.
- Звучание подсказки голосом Генри: тире и двоеточие в шаблоне — естественно ли.

## Smoke

`delivery/evals/smoke/run.sh` — без изменений: путь звука прежний, у подсказки нет
своего сообщения протокола.
