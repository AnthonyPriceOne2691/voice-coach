# Eval smoke — talk-core (D3a.1, 1 из 3)

Derived from spec acceptance. Run during verify, 2026-10-17. Эта поставка кладёт
политику разговора; сессия и экран — следующие две.

## Оракулы поставки

- [x] **T3** смена темы — решение кода, тема новая — `test_topic_change_picks_a_topic_not_heard_yet`
      (четыре формулировки), `test_topics_never_run_out`
- [x] **T4** «It was a slow day», «Trains are faster than buses here» — беседа:
      `test_words_without_the_shape_of_a_request_stay_talk`,
      `test_in_talk_only_the_shape_of_a_request_changes_the_pace`
- [x] **T5** «Could you speak a bit slower?» — распознаётся как просьба о темпе
      (`test_in_talk_only_the_shape_of_a_request_changes_the_pace`); сквозной мета-ход
      через WS — talk-wiring
- [x] **T6** оценки нет: просьба — отказ кодом (`test_requests_to_henry_get_a_line_and_the_question_back`),
      балл от модели режется (`test_talk_never_speaks_a_grade`), похвала проходит
      (`test_talk_lets_praise_and_plain_talk_through`)
- [x] **T7** «Can we switch to Russian?» — отказ и вопрос назад
- [x] **T8** прощание — решение кода, оркестратор закончен (`test_goodbye_ends_the_talk`);
      сессия `completed` через WS — talk-wiring
- [x] банк ≥ 10 тем и все реплики сценария проходят контракт разговора —
      `test_the_real_script_has_every_line_and_a_bank_of_topics`,
      `test_every_scripted_line_survives_the_talk_contract`

## Что проверяют следующие поставки

- **T1** (сервер), **T2**, **T9**, сквозные T5 и T8 — talk-wiring: сессия `talk`
  через WS, поток с окном истории, таблица.
- **T1** (экран) и **T10** (живой замер первого звука ≤ 3 s) — talk-screen.
