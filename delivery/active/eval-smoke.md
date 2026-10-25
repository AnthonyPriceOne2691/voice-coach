# Eval smoke — talk-notes-screen (D3a.2, 2 из 3, слой 2 из 2)

Run during verify, 2026-10-25. Живые модели и браузер не запускались: экран исполняют
компонентные тесты на jsdom (testing-library) с подменённым `fetch` и двойником
`Audio`; REST под ним — в `main` и проверен своей поставкой (talk-notes-rest).

## C10 — Language notes после разговора

- [x] каждая заметка — «You said: “…”» и «→ лучше — причина»; без причины нет и тире;
      ни одной оценки — `LanguageNotes.test.tsx` («каждая заметка — you said → better»)
- [x] без заметок — честное пустое состояние без кнопок и без похвалы
- [x] после конца разговора экран берёт заметки по `session_id` из `session_ended` —
      `TalkPage.test.tsx` («после разговора — его заметки»)

## C11 — Listen

- [x] играет WAV по адресу своей заметки (`/sessions/talks/t1/notes/1/audio`), `play`
      один раз; отказ звука виден — «Can't play right now»
- [x] заметки ушли с экрана — звук смолк (`pause` при размонтировании): фраза не
      доигрывает в микрофон новой сессии

## C12 — Add to Useful Words

- [x] `added` — «Added to Useful Words», кнопка больше не жмётся, запрос один и по
      адресу своей заметки; `exists` — «Already in Useful Words», не жмётся; 502 —
      «Couldn't add — try again», жмётся снова
- [x] пока ответа нет — «Adding…», кнопка выключена, второй клик второго запроса не
      шлёт: гонки двух Add на одну заметку экран не создаёт

## C13 — разговоры в History

- [x] секция Talks: длительность «· 12 min», «not finished» у брошенного, «2 language
      notes» / «No language notes» — `HistoryPage.test.tsx`
- [x] открытый разговор — заметки и транскрипт; «← Back to history» — снова список

## Постоянные smoke (`delivery/evals/smoke/run.sh`)

- [x] S1–S6 ok; S7 (health) пропущен — сервер не поднят

## Живое — по «запускай» human:anthony (не прогонялось)

- [ ] Listen голосом Piper в настоящем браузере: звучит лучший вариант в сохранённом
      темпе; при старте нового разговора сразу после Listen фраза смолкает до
      открытия микрофона (колонки, не наушники)
- [ ] снимок экрана Language notes после разговора и History с секциями Interviews и
      Talks: что сказано — тихо, как лучше — ярко; таблетка числа заметок (L17)
- [ ] Add to Useful Words на настоящей модели: русский перевод фразы, запись видна в
      Useful Words с категорией `fluency`; повтор — «Already in Useful Words» (L58)
