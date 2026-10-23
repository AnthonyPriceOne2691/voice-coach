# Verify report: talk-notes-rest (D3a.2 — 2 из 3, слой 1 из 2)

Дата прогонов: 2026-10-23. Builder: agent:claude-code (параллельная сессия, worktree
`.claude/worktrees/agent-a260dc0585f391a84`). Verifier: human:anthony.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| C13 (REST) | `test_talk_list_is_a_bounded_page_newest_first`, `test_talk_detail_has_notes_in_order_and_the_transcript` | **PASS** — новые первыми, страница 1…100 (вне — 422), длительность по `ended_at`, у брошенного `null`, число заметок, транскрипт |
| C10 (REST) | тот же тест детали | **PASS** — заметки по порядку разговора; без ключа — пусто; заметка вне контракта пропущена, ответ не падает |
| C11 (REST) | `test_listen_speaks_the_better_phrase_at_the_stored_pace` (3 случая) | **PASS** — `audio/wav` с кадрами, звучит `better`, темп вызова = сохранённый 1.45; «fast» и 9.0 — 1.15 |
| C12 | `test_add_to_useful_words_translates_once_and_never_duplicates`, `test_failed_translation_adds_nothing` (3), `test_add_brings_back_a_word_deleted_earlier`, `test_unknown_talk_or_note_is_404` | **PASS** — перевод по-русски одним вызовом qwen; повтор `exists` без модели; негодный перевод и молчащая модель — 502 без записи; удалённое возвращается; 404 на чужой разговор, номер вне списка и −1 |
| C10–C13 (экран) | поставка talk-notes-screen | собраны и зелёные на локальной ветке `feat/talk-notes-screen` (`f0fe001`, `1bf76f7`), проверяются там |

Все 11 тестов до правки были красными, и по правильной причине — маршрутов не было.
Тест на 404 до правки оказался зелёным: роутер и сам отвечает 404 на неизвестный
адрес. Чтобы он сторожил, в него добавлен положительный контроль «верный адрес
находится» (урок L101).

## Мутации (сторож обязан краснеть, L62)

| Мутация | Ожидание | Результат |
|---|---|---|
| MB1: `restore` не меняет статус | тест возврата удалённого красный | **красный** |
| MB2: отрицательный номер заметки допустим | тест 404 красный | **красный** |
| MB3: Listen игнорирует сохранённый темп | тест темпа красный | **красный** |
| MB4: S-H6 не судит перевод | тест 502 красный | **красный** |
| MB5: нет проверки наличия — повтор зовёт модель | тест повтора красный | **красный** |
| MB6: у страницы нет верхней границы | тест страницы красный | **красный** |
| MB7: заметка вне контракта уходит в ответ | тест детали красный | **красный** |

Пять мутаций экрана (MF1–MF5) прогнаны на собранной ветке до разреза — все красные;
их отчёт — в поставке talk-notes-screen.

## Машинные гейты

| Гейт | Результат |
|---|---|
| `UV_FROZEN=1 ./scripts/run_checks.sh` | **PASS** — 286 passed на слитом с `main` (там 275, поставка +11), coverage 95.68% (гейт 85), mypy strict, ruff, модули ≤ 500 строк |
| `STRICT=1 pre-commit run --all-files` | **PASS** — все хуки, jscpd 0 клон-пар обеих половин, сложность 0, слои OK, unbounded-list и cpu-in-async OK |
| `check_diff_coverage.sh` (`STRICT=1`) | **PASS** — `routes_talks.py` 100%, `talks.py` 94.4%, `vocabulary.py` 89.3% |
| `npx vitest run`, `npm run build` | **PASS** — фронт в поставке не тронут: 57 тестов, сборка |
| `okf_sync_gate.py --base origin/main`, `okf_validate.py` | **PASS** — концепты не задеты |
| `delivery_check.py --diff-base origin/main` | 0 ошибок; предохранитель — 8 файлов, net +595 (лимит 800) |

### Оставшиеся предупреждения

- **Примеры без ссылки: C1–C9, C14–C17** — это примеры соседних поставок той же спеки
  (talk-check и talk-tips); их тесты живут в своих ветках. Ссылаться на них отсюда
  значило бы объявить проверку, которой в этой поставке нет.
- **Реляционный оракул (§6.5)** — решение человека 2026-08-12: зависимость для
  тестов-свойств не добавляется.

### Покрытие `vocabulary.py:72-74` — артефакт замера, а не дыра

Отчёт показывает тело `restore` непокрытым, хотя мутация MB1 его роняет. Замер: с
`concurrency = greenlet,thread` строки 72-74 и соседние 113-117 (`soft_delete`)
покрыты, без него — нет. SQLAlchemy async исполняет работу сессии в greenlet, а coverage
без этой настройки теряет трассу после `await s.get(...)` в запросах через
`TestClient`. Это урок L100 ниже.

## Находка верификации: дайджест утверждений принимает любой «буква+цифры» за пример

`assert_digest.sh` приписывает утверждение первому токену вида `[A-Z][0-9]+` выше по
тесту. Комментарий «не R1 (D-8, L57)» сделал «примером» имя модели, докстринг «(L29)»
— номер урока: шесть утверждений числились привязанными к подписанным примерам, и
дайджест освобождал их от подписи. Комментарии переписаны (`c15c4ae`): теперь все 38
утверждений ведут к C10–C13. Сам инструмент не правился: это механика контура
(`scripts/lint/`), её место — полевой отчёт в канон, со сверкой токена со списком
примеров спеки.

## Изменение поверхности модели (§14.4)

- элемент: `backend/app/api/routes_talks.py` — новый. Он собирает запрос перевода
  фразы для `SummaryService.translate_term`: термин — `better` заметки, Usage —
  предложение Антона с исправленным фрагментом (`_example`). Промпт
  `translate_term_system.txt`, модель (`ollama_model_interview`, qwen2.5),
  температура, лимит токенов и `num_ctx` — прежние, их задаёт `translate_term`.
- почему: промпт перевода получает новый тип входа — фразы, а не одиночные термины.
- оракулы: S-H6 на ответе (`translation_problem`) — три случая (без кириллицы, CJK,
  молчащая модель) дают 502 без записи; мутация MB4 «S-H6 не судит» убита. Форма
  запроса — точное равенство последнего сообщения
  (`I went to the office and met my client` + Usage) и модель вызова (qwen, не R1).
- порча промпта: не делалась — промпт не менялся. Качество перевода фраз S-H6 не
  судит (L58), это живой прогон по «запускай».
- провайдер: живого прогона не было, Ollama не вызывалась.
- at=2026-10-23

## Ревью рисковых мест (§12.5)

1. **транзакция БД** (`commit` в `VocabularyRepository.restore`) — одна строка: чтение
   по ключу и запись `status`/`added_at` внутри одной `async with self._db.session()`,
   затем `s.commit()`; многострочной транзакции нет. Что реально может сломаться —
   гонка двух одновременных Add на одну заметку: `find_term`, `_translate` и `merge`
   идут разными сессиями, и оба запроса могут пройти `find_term`. Исход почти всегда —
   лишний вызов модели и `times_seen = 2`: второй `merge` найдёт строку первого
   через `_by_term`. Вставка двух строк возможна только при совпадении внутри
   `merge` между SELECT и COMMIT. Тогда `scalar_one_or_none()` в `_by_term` начнёт
   бросать на этом термине. Уникального индекса на `lower(term_en)` в схеме нет
   (doc 12, `create_all` без миграций). Защита — экран не шлёт второй запрос, пока
   идёт первый: кнопка «Adding…» не жмётся (talk-notes-screen). Человек один, риск
   назван, но не закрыт.
2. **производительность** (`json.loads`, `re.compile` в `routes_talks.py`) —
   `list_talks` разбирает `metadata_json` каждой строки через `_notes`; выборка
   ограничена `TALKS_PAGE_MAX = 100`, метаданные малы (фаза, темы, счётчики,
   заметки). Транскрипт в списке не разбирается — только в `get_talk` и
   `add_note_to_vocabulary`, по одной строке. `_SENTENCE_END` компилируется один раз
   при импорте. Гейт cpu-in-async не видит `json.loads` внутри синхронного `_notes`,
   и об этом сказано прямо: граница страницы — то, что держит цену.
3. **новый модуль** (`routes_talks`, `test_rest_talks`) — состояния нет, всё через
   репозитории контейнера; импорт `PACE_SETTING` из `routes_settings` вместо третьей
   копии константы. Что реально может сломаться — граница с параллельной talk-check:
   контракт `language_notes` проверен с двух сторон по отдельности (talk-check
   пишет, `_is_note` читает фикстуру по спеке), а сквозного «записала → прочитала»
   нет, пока обе не в `main`. Если talk-check переименует поле, `_notes` пропустит
   все заметки с записью в лог, а не упадёт — тихая пустота на экране. Кандидат в
   первую поставку после мержа обеих: тест на запись talk-check и чтение REST.

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` — объявленные пути (`ws_voice.py`, `useVoiceSession.ts`) не
задеты. Новые пути поставки — REST, его исполняют тесты:
`uv run pytest tests/test_rest_talks.py` — 11 тестов на `TestClient` с настоящей
SQLite, управляемой моделью и голосом-двойником, отдающим настоящий WAV; полный сьют —
286 passed. Живой голос и модель — по «запускай». at=2026-10-23

## Решения для человека

1. **Add to Useful Words возвращает слово, которое человек раньше удалил.** В doc 10
   есть правило «удалённое не добавлять снова». Оно написано для **автоматического**
   извлечения: экстрактор после каждого разбора сам предлагает слова, и без правила
   слово, удалённое человеком, возвращалось бы снова и снова против его воли. Явное
   нажатие «Add» — другой случай. Здесь просит сам человек и про конкретную фразу.
   Отказ значил бы, что однажды удалённую фразу нельзя вернуть никогда: кнопка
   ответила бы «уже в Useful Words», а в списке её нет. Возвращённая запись встаёт
   наверх (`added_at` — сейчас), перевод остаётся прежним.
2. **History — раздельные секции Interviews и Talks**, а не общий хронологический
   список (экран, поставка talk-notes-screen, уже собран). «Recent sessions»
   становится «Interviews», ниже — «Talks». Две постраничные выборки, слитые в одну,
   обрезали бы одну из них произвольно. И у строки интервью есть действия, которых у
   разговора нет (Review, Delete).
3. **Категория `fluency`** для фраз из разговора. Из пяти категорий doc 10
   (architecture, impact, process, fluency, technical) повседневной беглости
   соответствует только она. Фильтр по категории в Useful Words отделит фразы из
   разговоров от терминов интервью.

## Уроки

- **L99:** в этом репозитории тесты весят почти как код (492 строки к 552 у
  talk-notes), а доки добавляют ещё ~10%. Поэтому API и экран одной фичи в 800 строк
  вместе не помещаются. Оценка на плане (~950) уже превышала предел: резать надо на
  плане, а не после сборки (продолжение L77).
- **L100:** без `concurrency = greenlet,thread` coverage не видит строки после
  `await s.get(...)` в запросах через `TestClient`: `vocabulary.py:72-74` и
  `113-117` числятся непокрытыми, хотя мутация MB1 доказывает обратное, а с
  настройкой они покрыты (замер). Отчёт покрытия слоя хранилища занижен; судья тут —
  мутация. Кандидат в отдельную маленькую поставку: `[tool.coverage.run] concurrency`.
- **L101:** отрицательный тест на 404 был зелёным ещё до появления маршрута — роутер
  отвечает тем же 404. Сторож «не найдено» обязан нести положительный контроль
  «верный адрес находится», иначе он проверяет роутер, а не код.

## Verdict

**READY FOR HANDOFF** — REST-часть C10–C13 зелёная, семь мутаций сторожей убиты,
машинные гейты зелёные по правилам delivery@2.07 · cqg@2.74 (ветка догнала `main` после мержа контура #41). Экранная половина —
поставка talk-notes-screen. Живое — перевод фраз на qwen и Listen голосом Piper — по
«запускай».

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **38**, из них без ссылки на пример спеки: **0**.
Вопрос к каждому непривязанному один: **откуда взято ожидаемое значение — из спеки или
придумано под реализацию?**

```
C13	assert [i["id"] for i in items] == ["left", "legacy", "old"]  # C13: новые первыми
C13	assert by_id["old"]["duration_sec"] == 750 and by_id["old"]["notes_count"] == 1  # C13
C13	assert by_id["legacy"]["notes_count"] == 0  # C13: до talk-check заметок нет
C13	assert (left["ended_at"], left["duration_sec"], left["notes_count"]) == (None, None, 2)  # C13
C13	assert [i["id"] for i in page] == ["legacy"]
C13	assert rejected == [422, 422, 422]  # страница ограничена: выборка растёт с каждым днём
C10	assert detail["language_notes"] == [NOTE, STYLE]  # C10: экран не падает на чужой ошибке
C10	assert detail["notes_count"] == 2
C13	assert detail["transcript"] == TRANSCRIPT  # C13
C13	assert legacy["language_notes"] == [] and legacy["duration_sec"] is None
C13	assert missing == 404
C12	assert first.status_code == 200
C12	assert first.json() == {"status": "added", "term_en": BETTER, "translation_ru": RUSSIAN}  # C12
C12	assert again["status"] == "exists" and len(words) == 1  # C12: повтор не дублирует
C12	assert (word["term_en"], word["translation_ru"]) == (BETTER, RUSSIAN)  # C12
C12	assert word["times_seen"] == 1  # повторный клик — не «встретилось снова»
C12	assert word["example_en"] == f"Yesterday {BETTER}."
C12	assert word["context_note_en"] == f"You said: “{SAID}” — past tense"
C12	assert (word["type"], word["category"], word["session_id"]) == ("phrase", "fluency", "t1")
C12	assert llm.models == [container.settings.ollama_model_interview]
C12	assert llm.calls[0][-1]["content"] == f"{BETTER}\n\nUsage: Yesterday {BETTER}."
C12	assert response.status_code == 502  # C12
C12	assert "translation failed" in response.json()["detail"]
C12	assert words == []  # C12: ни записи с негодным переводом, ни пустой
C12	assert client.delete(f"/vocabulary/{word['id']}").status_code == 204
C12	assert back["status"] == "added"  # C12: экран не скажет «уже там» про невидимое
C12	assert [w["id"] for w in words] == [word["id"]]
C12	assert word["context_note_en"] == "You said: “It was a long day”"  # причины нет — нет и тире
C12	assert len(llm.calls) == 1  # возврат — без модели
C12	assert found == 200
C12	assert codes == [404] * 5
C11	assert isinstance(tts, FakeTts)
C11	assert response.status_code == 200
C11	assert response.headers["content-type"] == "audio/wav"
C11	assert audio.getnframes() > 0
C11	assert tts.synthesized == [BETTER]  # C11: звучит лучший вариант, а не сказанное
C11	assert tts.scales == [expected]  # C11
C11	assert container.settings.piper_length_scale == 1.15
```

✅ **Каждое утверждение ведёт к примеру спеки** (C10 C11 C12 C13), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь **не требуется**: она
уже стоит, заранее и на числах.

asserts_without_example: 0

asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 8 code (+5 process docs) / +604/-9 (net +595) |
| commits | 7 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — backend/tests/test_rest_talks.py (новый оракул) |
| implement_retries | 1 — замер собранной talk-notes пробил предохранитель (1,044 > 800 без доков); разрез по слоям без waiver, экран — следующей поставкой |
| verify_fails_before_green | 0 — CI на ветке зелёный с первого прогона; локальные гейты зелёные |
| est_token_or_cost | n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
