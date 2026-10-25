# Eval smoke — talk-notes-rest (D3a.2, 2 из 3, слой 1 из 2)

Run during verify, 2026-10-23. Живые модели не запускались: REST исполняют тесты на
`TestClient` с настоящей SQLite, управляемой моделью (`ScriptedLlm`, падающий двойник
`DownLlm`) и голосом-двойником, который отдаёт настоящий WAV (`FakeTts`).

## C13 — разговоры в History (REST-часть)

- [x] страница — новые первыми; `limit` 0 и 101, `offset` −1 — 422 —
      `test_talk_list_is_a_bounded_page_newest_first`
- [x] строка: длительность 750 s по `ended_at`, число заметок; у брошенного
      `ended_at` и `duration_sec` — `null`
- [x] деталь отдаёт транскрипт как записан —
      `test_talk_detail_has_notes_in_order_and_the_transcript`

## C10 — заметки разговора (REST-часть)

- [x] `language_notes` по порядку разговора; без ключа — пустой список; заметка вне
      контракта пропущена, ответ не падает — тот же тест детали

## C11 — Listen (REST-часть)

- [x] `audio/wav` с кадрами; синтезирован лучший вариант, а не сказанное; темп вызова —
      сохранённый 1.45; «fast» и 9.0 — темп по умолчанию 1.15 —
      `test_listen_speaks_the_better_phrase_at_the_stored_pace`

## C12 — Add to Useful Words

- [x] перевод по-русски одним вызовом голосовой модели, Usage — исправленная фраза
      Антона; повтор — `exists` без модели, `times_seen` 1 —
      `test_add_to_useful_words_translates_once_and_never_duplicates`
- [x] перевод без кириллицы, с CJK и молчащая модель — 502, банк пуст —
      `test_failed_translation_adds_nothing`
- [x] удалённое человеком возвращается без модели —
      `test_add_brings_back_a_word_deleted_earlier`
- [x] чужой разговор, номер вне списка и −1 — 404; верный адрес находится —
      `test_unknown_talk_or_note_is_404`

## Экранная половина C10–C13 — поставка talk-notes-screen

Компонентные тесты экрана собраны и зелёные на локальной ветке
`feat/talk-notes-screen` (`f0fe001`, `1bf76f7`) и проверяются в своей поставке.

## Живое — по «запускай» human:anthony (не прогонялось)

- [ ] перевод фраз на qwen2.5 — заметки реального разговора после talk-check: доля
      переводов, отвергнутых S-H6, и транслитерации глазами (L58)
- [ ] Listen голосом Piper в браузере — в поставке talk-notes-screen
