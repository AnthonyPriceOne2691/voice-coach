# Verify report: speech-pace

Дата прогонов: 2026-08-12. Verifier: human:anthony (builder — agent:claude-code).

## Оракулы примеров спеки

| id | Оракул | Результат |
|---|---|---|
| P1 | `test_ws_pace.py::test_slower_request_changes_tempo_and_costs_no_question` | PASS |
| P2 | `test_ws_pace.py::test_faster_request_speeds_henry_up` | PASS |
| P3 | `test_pace_policy.py::test_clamped_at_both_limits_and_the_limit_is_reported` | PASS |
| P4 | `test_ws_pace.py::test_answer_mentioning_speed_is_a_normal_turn` | PASS |
| P5 | `test_ws_pace.py::test_pace_survives_the_session`, `test_rest_api.py::test_speech_pace_setting_is_exposed_and_validated` | PASS |
| P6 | `test_rest_api.py::test_speech_pace_setting_is_exposed_and_validated` | PASS |
| P7 | `test_ws_pace.py::test_pace_request_works_in_review_mode` | PASS |
| P8 | живой прогон, см. ниже | PASS |
| P9 | `test_ws_pace.py` (P9-часть) + `test_summary.py::test_meta_turns_never_reach_the_summary_prompt` | PASS |

## Машинные гейты

| Гейт | Результат |
|---|---|
| `./scripts/run_checks.sh` | **PASS** — module size, ruff, ruff format, mypy strict, pytest |
| Backend pytest | **137 passed**, coverage **94.25%** (гейт 85; было 104 теста / 93.01%) |
| pre-commit (полный набор) | PASS — все 20+ хуков; `jscpd` сначала **краснел** и был честно закрыт консолидацией, см. ниже |
| `delivery_check.py --diff-base origin/main` | **0 errors**, 1 warning (см. ниже) — принят осознанно |
| `okf_sync_gate.py --base origin/main` | OK — единственный drift (`model-split.md`) закрыт подписанным waiver'ом |
| Frontend `npm run build` + `npm test` | PASS, **20 passed** — фронт не тронут, и это **замер**, а не утверждение |

### Оставшийся warning и почему он остался

`class M: ни одного реляционного оракула (§6.5)` — гейт ищет декоратор
hypothesis или свойство fast-check. Решение человека (2026-08-12): **не
добавлять** зависимость. Инвариант коридора при этом проверяется перебором
вручную — `test_pace_policy.py::test_repeated_requests_never_leave_the_corridor`
гоняет 10 просьб подряд в каждую сторону и утверждает границы, а
`test_clamped_at_both_limits_and_the_limit_is_reported` проверяет обе границы и
шаг, не доходящий до предела. Это инвариант по существу, но не в той форме,
которую видит гейт. Долг записан честно, а не спрятан.

### ⚠ Находка о самом гейте: он глушится упоминанием в прозе

Первая версия этого отчёта **процитировала** имя искомого декоратора, объясняя
warning, — и warning исчез. Причина: `delivery_evidence.py` ищет строку по
`haystack`, в который входят и документы поставки, поэтому **слово о свойстве
неотличимо от свойства**. Зелёное было получено прозой, а не тестом.

Это опаснее ложного срабатывания (§4.3b): ложное срабатывание видно и мешает,
а ложное молчание выглядит как выполненное требование. Здесь оно снято вручную
(цитата убрана, warning вернулся), но в контуре остаётся дефектом: гейт,
который можно погасить, написав о нём, не проверяет ничего. Кандидат в полевой
отчёт по канону.

## Исполнение рисковых путей (§12.6)

`runtime_paths: backend/app/voice/tts_piper.py` — слышимость темпа платформа
подтверждает звуком, а не кодом ошибки: `FakeTts` запишет любое число и
останется зелёным.

**Путь:** `backend/app/voice/tts_piper.py` — исполнен живым Piper'ом (не моком),
двумя способами ниже, at=2026-08-12.

### 1. P8 — латентность на самом медленном темпе

Чем исполнял: настоящий стек без моков — `WhisperCppStt` (whisper-cli,
`ggml-small.en`) → `OllamaClient` (`qwen2.5:14b-instruct`) → `PiperTts`
(`en_US-hfc_male-medium`). Реплика пользователя — ~9 s речи. Замер до **первого**
аудио-чанка, после прогрева. at=2026-08-12.

| `length_scale` | STT | LLM до 1-го предложения | TTS 1-го предложения | Всего (медиана) | Худший прогон |
|---|---|---|---|---|---|
| 1.15 (текущий) | ~600 ms | ~495 ms | **45 ms** | **1148 ms** | 1231 ms |
| 1.60 (самый медленный) | ~550 ms | ~495 ms | **69 ms** | **1105 ms** | **1151 ms** |

**Вердикт: PASS.** Гейт — 3000 ms; худший прогон на самом медленном темпе —
1151 ms, то есть **треть бюджета**. Цена самого медленного темпа измерена и
составляет **+24 ms** на синтезе первого предложения; на фоне STT+LLM (~1.1 s)
она теряется. Три прогона на ступень, не один.

### 2. Темп действительно слышен

Одно и то же предложение («What trade-off did you consider when you chose SQLite
over Postgres?») на каждой ступени коридора, живой Piper:

| scale | Длительность | Относительно самого быстрого |
|---|---|---|
| 0.85 | 3.55 s | 1.00× |
| 1.00 | 4.08 s | 1.15× |
| 1.15 | 4.56 s | 1.28× |
| 1.30 | 4.75 s | 1.34× |
| 1.45 | 5.28 s | 1.49× |
| 1.60 | 5.43 s | 1.53× |

**Вердикт: PASS.** Коридор растягивает фразу в полтора раза, и **каждая** ступень
отличается от соседней на 0.2–0.5 s при длине фразы ~4 s — то есть шаг заметен
на слух, а не только в числе. Записанные образцы каждой ступени лежат рядом с
прогоном (scratchpad сессии), их можно послушать подряд.

## Незапланированное: консолидация двух флоу

Гейт `jscpd` покраснел на коммите и оказался прав по существу: `InterviewFlow` и
`ReviewFlow` дублировали **36 строк одним куском** ещё до этой поставки (замерено
прогоном jscpd на `origin/main` — одна клон-пара), а `on_meta` встал ровно в
середину и разрезал её на две.

Выбрано **починить**, а не переснять снимок (решение человека): общая часть —
`on_agent`, `on_meta`, `messages`, `finished`, `finish`, запись реплик — переехала
в `backend/app/voice/session_flow.py`; в наследниках остались оркестратор, обёртка
пользовательской реплики и состав метаданных, то есть ровно то, чем режимы
различаются. Снимок пересобран **вниз, с 1 до 0**.

Страховка — характеризационная: 134 теста, включая ws-контрактные по обоим
режимам, зелёные ДО и ПОСЛЕ переноса, без единой правки теста. Coverage вырос с
93.34% до 93.61%.

## Что нашёл CI, чего не нашли локальные гейты

`quality/gates/Diff coverage` покраснел на `tts_piper.py`: **48.4%** при цели 70.
Локально этот гейт молчал — он запускается с `LINT_PY_SRC=backend/app`, а без
переменной честно печатает «не смотрел никуда» (и это правильное поведение, не
дефект).

Замечание оказалось по существу: изменённые строки `tts_piper.py` — ровно те, где
число превращается в звук, и `FakeTts` доказать их не может **в принципе**.
Добавлен `test_tts_piper.py`: подставлен двойник `PiperVoice`, проверяется, что
уходит в `SynthesisConfig` при настроенном темпе и при разовом переопределении.
Стало **87.1%**, всего тестов 137, coverage 94.25%.

То есть цепочка «FakeTts → PacedTts → PiperTts → SynthesisConfig» теперь закрыта
оракулом на каждом стыке, а не только на первом.

## Ревью рисковых мест (§12.5)

Дифф задел новый модуль и путь производительности. Что именно может сломаться —
с именами из диффа, а не «посмотрел и всё нормально»:

1. **`pace.detect` съедает содержательный ответ.** Самое дорогое из возможного:
   реплика пользователя не попадает ни в оркестратор, ни в LLM-историю, и в
   транскрипте от неё остаётся мета-ход. Восстановить нечего — это ровно тот
   «невосполнимый артефакт», о котором concept `transcript-durability`. Держится
   на `MAX_REQUEST_WORDS = 12` и на порядке шаблонов в `_PATTERNS`. Порядок —
   реальная ловушка: «too slow» содержит «slow», и общий шаблон замедления,
   стоящий выше, выдал бы ПРОТИВОПОЛОЖНОЕ действие; поэтому составные
   формулировки идут первыми, а на это есть отдельный тест
   (`test_too_slow_asks_to_speed_up_not_to_slow_down`). Слабое место остаётся:
   короткая настоящая реплика вида «slow start, then it scaled» (5 слов) будет
   принята за просьбу. Это осознанный размен, записанный в спеке.

2. **`_handle_pace_request` живёт в `_run_turn` и наследует его обработку
   ошибок.** Ветка стоит ПОСЛЕ `transcribe_utterance` и ВНУТРИ существующего
   `try`, у которого `except WebSocketDisconnect: raise` идёт до широкого
   `except Exception` (L8). Значит разрыв посередине мета-хода закрывает сессию
   штатно, а не объявляет её упавшей. Новых задач (`create_task`) мета-ход не
   заводит, поэтому источника висов класса L5–L7 не добавляет — это проверено
   не рассуждением, а тем, что оба ws-теста дослушивают `session_ended`, и в
   логе прогона нет `no active connection`.

3. **`PacedTts` — изменяемое состояние на сессию.** `set_scale` вызывается ДО
   синтеза, и на этом держится половина P1: переставь две строки местами —
   подтверждение прозвучит СТАРЫМ темпом, а тесты, проверяющие только итоговое
   значение настройки, останутся зелёными. Поэтому оракул смотрит на список
   `FakeTts.scales` (значение КАЖДОГО вызова), а не на `tts.scale` в конце.

4. **«Деньги» — риска нет, и вот почему.** Маячок подняли слова `счётчик`
   (в `test_ws_pace.py`: «счётчик follow-up прежний») и «цена» из разбора
   размена в `pace.py`. Денег в этом проекте нет вообще: он локальный, офлайновый,
   без платежей и без внешних вызовов. Ни `settings_repo.py`, ни
   `routes_settings.py`, ни `tts_paced.py` не касаются ничего финансового —
   `speech_length_scale` это число от 0.85 до 1.60.

5. **Производительность.** Единственный новый расход на обычном ходе — `re.search`
   по восьми шаблонам на одну реплику, то есть шум. Расход, который виден, —
   синтез на медленном темпе: измерен, +24 ms к первому предложению (таблица
   выше). Гейт 3.0 s остаётся с запасом втрое.

6. **`SettingsRepository` получил параметр `defaults`.** Изменение затрагивает
   всех потребителей репозитория, но поведение по умолчанию прежнее: словарь
   мержится поверх модульного `DEFAULTS`. Риск — расхождение литерала `1.15` с
   `Settings.piper_length_scale`; закрыт тестом
   `test_settings_defaults_agree_with_the_config`, потому что расхождение
   ничего не ломает громко (Генри просто заговорит не с той ступени).

### Ещё две находки о гейтах контура

Обе — из этого же прогона, обе про то, что механика меряет не то, что называет:

1. **`RISK_CLASSES["деньги"]` совпадает по фрагменту.** Корень `счёт\w*` ловит
   `счётчик`, то есть обычное слово «counter». В `delivery_risk.py` рядом стоит
   комментарий «Русские корни — только однозначные» и рассказ, как по этой же
   причине убрали `доступ` (совпадал внутри `недоступен`). `счёт` — ровно тот же
   случай, только не пойманный: он же внутри `счётчик`, `расчёт`, `учётный`.

2. **`diff_identifiers` берёт `HEAD~1..HEAD`** (`delivery_diff.py:85`), то есть
   ПОСЛЕДНИЙ коммит, а не дифф поставки. У поставки из двух коммитов (код, потом
   артефакты) порог «≥2 цитаты из диффа» становится невыполнимым арифметически:
   в последнем коммите кода нет. Это буквально **L4** из
   `2026-08-11-contour-2.01`, повторившийся в другом скрипте — там ловили
   `--diff-base @{u}`, здесь то же самое зашито константой. Обойдено схлопыванием
   поставки в один коммит, но это лечение симптома.

3. **Схлопывание в один коммит гасит проверку §3.1d.** До схлопывания гейт
   честно предупреждал: «пример и тест приехали одним коммитом, порядок не
   проверить». После — молчит, хотя порядок стал виден ХУЖЕ, а не лучше. То
   есть требование ≥2 цитат (пункт 2) и требование раздельных коммитов (§3.1d)
   тянут в противоположные стороны, и удовлетворить оба одновременно нельзя.
   Здесь порядок подтверждён вне механики: человек утвердил три решения спеки
   до первой строки кода (`decisions.md` D2–D4, `STATUS.human_ok_spec`).

Вместе с находкой о §6.5 выше — четыре кандидата в полевой отчёт по канону.

## Чего эта проверка НЕ покрывает

- **Живой сессии в браузере не было.** Мета-ход проверен на уровне WS-контракта
  (`TestClient`) и живого стека по стадиям, но не в реальном разговоре голосом.
  Урок L10 говорит прямо: ручной прогон находит то, чего не видит сьют. Это и
  есть содержание `observe_signal` — P1, P4, P5 подтверждаются в первой же
  настоящей сессии.
- **Ослышки STT не измерены.** `whisper small.en` может услышать «slower» как
  «lower»; насколько часто — неизвестно, и поставка этого не обещает.
- **Порог в 12 слов не откалиброван на настоящей речи**, только на примерах
  спеки. Если живые просьбы окажутся длиннее — это правка одной константы.

## CI

Локальные гейты зелёные полностью. Прогон CI на ветке — ссылкой на PR при
handoff (L1: `CI` и `quality` — разные workflow, каждый называется поимённо).

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 29 code (+9 process docs) / +796/-52 (net +744) |
| commits | 2 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — backend/tests/test_pace_policy.py (новый оракул), backend/tests/test_tts_paced.py (новый оракул), backend/tests/test_ws_pace.py (новый оракул), delivery/active/spec.md (новый оракул) |
| implement_retries | MANUAL — fills from session log |
| verify_fails_before_green | MANUAL — count red verify runs (CI run list) |
| est_token_or_cost | MANUAL / n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.

## Verdict

**READY FOR HANDOFF** — все девять примеров спеки подтверждены оракулами,
локальные гейты зелёные, рисковый путь исполнен живым стеком с датой, оба
waiver'а подписаны человеком. Остаётся один принятый warning (§6.5) и
наблюдение до 2026-08-26.
## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **65**, из них без ссылки на пример спеки:
**11**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
L20	assert started["type"] == "session_started"
-	assert detect(utterance) is expected
-	assert detect("That's too slow.") is PaceRequest.FASTER
-	assert detect(utterance) is None
P1	assert detect(f"speak slower {words}") is None
P1	assert (new_scale, at_limit) == (1.30, False)  # P1
P2	assert (new_scale, at_limit) == (1.00, False)  # P2
P3	assert apply(PACE_SLOWEST, PaceRequest.SLOWER) == (PACE_SLOWEST, True)
P3	assert apply(PACE_FASTEST, PaceRequest.FASTER) == (PACE_FASTEST, True)
P3	assert apply(PACE_SLOWEST - 0.15, PaceRequest.SLOWER) == (PACE_SLOWEST, False)
-	assert scale == PACE_SLOWEST
-	assert scale == PACE_FASTEST
-	assert in_range(1.15) and in_range(PACE_FASTEST) and in_range(PACE_SLOWEST)
-	assert not in_range(2.5)
-	assert not in_range(0.5)
L24	assert line, f"{name} пуст"
L24	assert turn.feed(line) is None, f"{name} режется контрактом: {line!r}"
L25	assert red.feed("Sure, slowing down. I'd rate that answer four out of 5.") is not None
P5	assert client.get("/settings").json()["speech_length_scale"] == 1.15
P5	assert client.patch("/settings", json={"speech_length_scale": 1.45}).status_code == 200
P5	assert client.get("/settings").json()["speech_length_scale"] == 1.45
P6	assert client.patch("/settings", json={"speech_length_scale": bad}).status_code == 422
P6	assert client.get("/settings").json()["speech_length_scale"] == 1.45  # не тронуто
L11	assert DEFAULTS["speech_length_scale"] == Settings().piper_length_scale
L11	assert in_range(DEFAULTS["speech_length_scale"])
Q1	assert "I built a CRM." in sent  # содержательное на месте
Q1	assert "Slower, please." not in sent
Q1	assert "Sure, slowing down." not in sent
-	assert inner.scales == [1.15]
P1	assert inner.scales == [1.15, 1.30]
P1	assert tts.scale == 1.30
-	assert inner.scales == [1.0]
-	assert tts.scale == 1.15  # разовый аргумент не меняет темп сессии
P1	assert isinstance(tts, FakeTts)
P1	assert tts.scales == [DEFAULT_SCALE]  # интро — прежним темпом
P1	assert _agent_lines(turn) == [f"Sure, slowing down. Here it is again. {INTRO}"]
P1	assert tts.scales == [DEFAULT_SCALE, 1.30, 1.30]
P1	assert "slower" not in spoken_to_llm
P1	assert "Here it is again" not in spoken_to_llm
P1	assert row is not None
P1	assert metadata["phase"] == "INTRO"
P1	assert metadata["questions_asked"] == 1
P1	assert metadata["follow_ups"] == 0
P9	assert [t["state"] for t in turns[-2:]] == [META_STATE, META_STATE]
P9	assert [t["question_id"] for t in turns[-2:]] == [None, None]
P9	assert [t["role"] for t in turns[-2:]] == ["user", "agent"]
P2	assert isinstance(tts, FakeTts)
P2	assert _agent_lines(turn) == [f"Sure, speeding up. Here it is again. {INTRO}"]
P2	assert tts.scales[-2:] == [1.00, 1.00]
P4	assert isinstance(tts, FakeTts)
P4	assert _agent_lines(turn) == ["Got it. Why the batching layer?"]  # ответила модель
P4	assert set(tts.scales) == {DEFAULT_SCALE}  # темп не тронут
P4	assert answer in json.dumps(llm.calls)  # ответ дошёл до модели
P4	assert row is not None
P4	assert json.loads(row.metadata_json)["phase"] != "INTRO"  # состояние продвинулось
P4	assert all(t["state"] != META_STATE for t in json.loads(row.transcript_json))
P5	assert isinstance(tts, FakeTts)
P5	assert client.get("/settings").json()["speech_length_scale"] == 1.30
P5	assert tts.scales[0] == 1.30
Q1	assert isinstance(tts, FakeTts)
Q1	assert _agent_lines(turn) == [f"Sure, slowing down. Here it is again. {agent_intro}"]
Q1	assert tts.scales[-2:] == [1.30, 1.30]
Q1	assert row is not None
Q1	assert json.loads(row.metadata_json)["questions_reviewed"] == 0
Q1	assert [t["state"] for t in turns[-2:]] == [META_STATE, META_STATE]
```

Привязаны к примерам: **L11 L20 L24 L25 P1 P2 P3 P4 P5 P6 P9 Q1**. Остальные 11 — нет.

Читать нужно **только строки с `-` в первой колонке**: их ожидание
ничем не подписано. Подпись: `asserts_reviewed_by: human:… at=…`.

asserts_without_example: 11

asserts_reviewed_by: human:anthony at=2026-08-12 — прочитаны все 11 строк без
примера: восемь проверяют таблицу распознавания и порог «короче 12 слов», три —
границы коридора 0.85–1.60 с шагом 0.15 и поведение адаптера темпа. Ожидания
совпадают с решениями D4 и D5 (`decisions.md`), принятыми ДО кода.
