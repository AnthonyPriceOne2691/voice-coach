# Eval smoke — talk-wiring (D3a.1, 2 из 3)

Derived from spec acceptance. Run during verify, 2026-10-17. Эта поставка подключает
политику разговора (talk-core) к сессии; экран и живой замер — talk-screen.

## Оракулы поставки (WS на фейковых модели, STT и TTS; контракт, сценарий и база — настоящие)

- [x] **T1** (сервер) `start_talk` → `session_started {session_kind: talk}`, приветствие и
      тема из банка, `persona=friend_mentor`, поля вопроса в `state` — `null` —
      `test_start_talk_opens_with_a_greeting_and_a_topic_from_the_bank`
- [x] **T2** реплика уходит модели сырым текстом после системного промпта; транскрипт
      agent → user → agent — `test_talk_reaches_the_model_and_the_pace_stays`
- [x] **T3, T6, T7** тема, отказ оценивать, отказ от русского — кодом; модель о ходе не
      знает — `test_requests_are_answered_by_code_not_by_the_model`; отказ вне истории
      модели и на следующих ходах — `test_requests_stay_out_of_the_models_history`
- [x] **T4** «It was a slow day» через WS — ответ модели, темп прежний
- [x] **T5** «Could you speak a bit slower?» — мета-ход темпа с повтором последней реплики —
      `test_pace_request_in_talk_slows_down_and_repeats`
- [x] **T8** «Okay, I have to go. Bye, Henry!» — прощание, `session_ended`, сессия
      `completed` — `test_goodbye_ends_the_talk_as_completed`
- [x] **T9** 40 ходов: системный промпт первый, окно ≤ 40 сообщений, начало окна
      сдвигается ступенькой — `test_long_talk_sends_a_window_with_the_system_prompt_first`

## Что проверяет следующая поставка

- **T1** (экран) и **T10** (живой замер первого звука ≤ 3 s) — talk-screen.
