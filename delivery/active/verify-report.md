# Verify report: talk-wiring (D3a.1, 2 из 3)

Дата прогонов: 2026-10-17. Builder: agent:claude-code (сессия voice-interview-coach).
Verifier: human:anthony.

## Оракулы спеки

| id | Оракул (WS на фейковых модели, STT и TTS) | Результат |
|---|---|---|
| T1 | `test_start_talk_opens_with_a_greeting_and_a_topic_from_the_bank` | **PASS** — `session_kind: talk`, приветствие и тема из банка, `persona=friend_mentor`, поля вопроса `null` |
| T2 | `test_talk_reaches_the_model_and_the_pace_stays[gym]` | **PASS** — модели уходит системный промпт и сырая реплика; транскрипт agent → user → agent |
| T3, T6, T7 | `test_requests_are_answered_by_code_not_by_the_model`, `test_requests_stay_out_of_the_models_history` | **PASS** — реплика из сценария, модель о ходе не знает и на следующих ходах |
| T4 | `test_talk_reaches_the_model_and_the_pace_stays[slow day]` | **PASS** — ответ модели, темп прежний |
| T5 | `test_pace_request_in_talk_slows_down_and_repeats` | **PASS** — мета-ход темпа, последняя реплика повторена |
| T8 | `test_goodbye_ends_the_talk_as_completed` | **PASS** — `session_ended`, сессия `completed` |
| T9 | `test_long_talk_sends_a_window_with_the_system_prompt_first` | **PASS** — системный промпт первый, окно ≤ 40, начало окна ступенькой |

**Красное до проводки:** WS-тесты падали на отсутствующих `start_talk`, `TalkFlow`,
`talk_sessions` (коммит тестов раньше коммита реализации).

## Мутации (сторож обязан краснеть)

| Мутация | Ожидание | Результат |
|---|---|---|
| MW1: окно скользит на каждом ходе (`window_start = size − WINDOW_MAX`) | T9 красный | **красный** — начало окна меняется чаще ступенек |
| MW2: разговор зовёт таблицу темпа интервью | T4 через WS красный | **красный** — «It was a slow day» стало сменой темпа |
| MW3: реплика кода всегда пишется в историю модели | отказ вне истории — красный | **красный** — `test_requests_stay_out_of_the_models_history` |

Файлы после каждой мутации возвращены и сверены `git status`.

## Машинные гейты

| Гейт | Результат |
|---|---|
| `UV_FROZEN=1 ./scripts/run_checks.sh` | **PASS** — 270 passed (было 260: +10), coverage 95.60%, mypy strict, ruff, размер модулей (`ws_voice.py` 494 из 500) |
| `check_diff_coverage.sh` (L32 — `run_checks` его не гоняет) | **PASS**, exit 0: изменённые файлы 83–100% |
| `pre-commit run --all-files` | **PASS** — jscpd 0 клон-пар |
| `okf_sync_gate.py --base origin/main` | **PASS** — концепты model-split и sentence-streaming обновлены по существу |
| `delivery_check.py --diff-base origin/main` | 0 ошибок; предохранитель — 15 файлов, ~470 строк при 800 |
| фронт | не тронут |

### Оставшиеся предупреждения

- **§3.1d «примеры появились в истории позже тестов»** — артефакт пересборки,
  а не порядок работы. Примеры T1–T10 подписаны человеком в спеке D3a.1 до кода и
  вошли в `main` раньше этих тестов — коммитом ядра `7beabae` (`delivery/active/spec.md`).
  Ветка проводки пересобрана после замера предохранителя: коммиты тестов перенесены
  с ветки, где спека стояла первой, а `spec.md` этой поставки — копия той же спеки,
  добавленная после переноса.
- **Реляционный оракул (§6.5)** — решение человека 2026-08-12: зависимость для
  тестов-свойств не добавляется. Ближе всего к отношению — T9: тест сверяет начало
  окна между ходами (свойство «префикс стабилен между ступеньками»), а не значение.
- **T10 без теста** — живой замер первого звука, поставка talk-screen.

## Изменение поверхности модели (§14.1)

- `backend/app/voice/talk_flow.py` — что модель видит в разговоре: системный промпт
  `talk_system.txt` и окно последних 21–40 сообщений; отказы, прощание и мета-ходы в
  историю не попадают. at=2026-10-17
- `backend/app/config.py` — `talk_temperature` 0.8, `talk_max_tokens` 200; модель та же
  (`ollama_model_interview`, D-8).
- `backend/app/api/ws_voice.py` — реплика беседы уходит модели сырым текстом, без
  обёртки состояния; повтор после нарушения — с намерением `CHAT_INTENT`.
- Интервью и разбор: что видит модель — не менялось (старт интервью через `_open` в
  прежнем порядке; тесты интервью не правились).

## Ревью рисковых мест (§12.5)

1. **транзакция БД** (`commit`) — `TalkRepository` коммитит каждую запись своей
   короткой сессией SQLAlchemy, как репозитории интервью и разбора: `create`,
   `checkpoint` на каждом ходе (flush-first, doc 12) и `finish`. Общего состояния и
   долгих транзакций нет; чекпойнт — одна строка по первичному ключу. Уборка
   сессии разговора идёт через тот же `aclose` → `finish` с `shield` и таймаутом
   (L5, L6): закрытие вкладки посреди хода не оставит соединение вне пула.
2. **производительность** — `window_start` считает начало окна арифметикой за O(1);
   `messages` копирует не больше 40 сообщений на ход. Главная цена — prefill: окно
   сдвигается ступенькой, поэтому KV-кэш теряется раз в 20 сообщений, а не на каждом
   ходе (doc 20).
3. **новый модуль** (`talk_flow`, `talks`, `warmup`) — `warmup` перенесён из
   `ws_voice.py` без изменений (best-effort, отказ в лог); `talks` — короткий
   репозиторий на миксине `SessionRecord`; `talk_flow` держит инвариант «реплика кода
   и отказ — вне истории модели» (MW3 его проверил).

## Исполнение рисковых путей (§12.6)

`runtime_paths: backend/app/api/ws_voice.py` — голосовой цикл разговора исполнен
WS-тестами на фейковых модели, STT и TTS: старт, беседа, мета-ход темпа, реплики кода,
прощание, окно. at=2026-10-17 Настоящий голос, микрофон и модель — браузерный стенд в поставке
talk-screen, только по «запускай» человека.

## Verdict

**READY FOR HANDOFF** — T1–T9 зелёные через WS-сессию, сторожа проверены мутациями,
машинные гейты зелёные по правилам delivery@2.01 · cqg@2.57.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **26**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
T1	assert row is not None
T1	assert result["started"]["payload"]["session_kind"] == "talk"
T1	assert result["opening"].startswith(SCRIPT.lines["intro"])
T1	assert any(result["opening"].endswith(opener) for opener in OPENERS)
T1	assert result["row"].persona == "friend_mentor"
T1	assert {s["session_kind"] for s in states} == {"talk"}
T1	assert {s["question_index"] for s in states} == {None}
T2	assert result["henry"] == "".join(REPLY).strip()
T2	assert last_call[-1] == {"role": "user", "content": said}  # сырая реплика, без обёртки
T2	assert PACE_TEMPLATES["pace_slower"] not in result["henry"]
T2	assert [t["role"] for t in turns] == ["agent", "user", "agent"]
T3	assert result["henry"].startswith(SCRIPT.lines[first_line])
T3	assert not _model_heard(result)
T3	assert result["henry"].endswith(opener) is question_back
T5	assert result["henry"] == f"{PACE_TEMPLATES['pace_slower']} {result['opening']}"
T5	assert not _model_heard(result)
T8	assert result["henry"] == SCRIPT.lines["goodbye"]
T8	assert ended and ended[0]["session_kind"] == "talk"
T8	assert result["row"].status == "completed"
T8	assert not _model_heard(result)
T9	assert messages[0] == {"role": "system", "content": "SYSTEM"}
T9	assert len(messages) - 1 <= WINDOW_MAX
T9	assert messages[-1]["content"] == "Nice, thing 39!"
T9	assert len(set(firsts)) <= 1 + (2 * 40 + 1) // WINDOW_STEP
T6	assert flow.messages == before
T6	assert [t["state"] for t in flow.buffer.to_json_list()[-2:]] == ["REQUEST", "REQUEST"]
```

✅ **Каждое утверждение ведёт к примеру спеки** (T1 T2 T3 T5 T6 T8 T9), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 15 code (+10 process docs) / +558/-84 (net +474) |
| commits | 9 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 commit(s) after first phase: handoff |
| harness_hardened | yes — backend/tests/test_ws_talk.py (новый оракул) |
| implement_retries | 2 — собранный целиком сервер упёрся в предохранитель, ветка пересобрана по слоям; дайджест нашёл одно утверждение без id примера — привязано к T1 |
| verify_fails_before_green | 0 — гейты после пересборки зелёные с первого прогона; CI ветки — в PR |
| est_token_or_cost | n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
