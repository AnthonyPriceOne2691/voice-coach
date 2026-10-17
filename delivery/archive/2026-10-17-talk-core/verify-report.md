# Verify report: talk-core (D3a.1, 1 из 3)

Дата прогонов: 2026-10-17. Builder: agent:claude-code (сессия voice-interview-coach).
Verifier: human:anthony.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| T3 | `test_topic_change_picks_a_topic_not_heard_yet` (4 формулировки), `test_topics_never_run_out` | **PASS** |
| T4 | `test_words_without_the_shape_of_a_request_stay_talk`, `test_in_talk_only_the_shape_of_a_request_changes_the_pace` | **PASS** — до реализации красные |
| T5 | распознавание просьбы о темпе в разговоре | **PASS**; сквозной мета-ход через WS — talk-wiring |
| T6 | `test_requests_to_henry_get_a_line_and_the_question_back`, `test_talk_never_speaks_a_grade`, `test_talk_lets_praise_and_plain_talk_through` | **PASS** |
| T7 | отказ говорить по-русски, вопрос назад | **PASS** |
| T8 | `test_goodbye_ends_the_talk`, `test_after_the_time_limit_henry_says_goodbye` | **PASS**; сессия `completed` через WS — talk-wiring |
| — | банк ≥ 10 тем, реплики сценария проходят контракт | **PASS** |

**Красное до реализации:** 12 тестов темпа в разговоре падали ровно на новых
случаях (`detect` не знал `casual`); тесты оркестратора — на отсутствующем модуле.

## Мутации (сторож обязан краснеть)

| Мутация | Ожидание | Результат |
|---|---|---|
| M1: разговор зовёт таблицу темпа интервью | T4 красный | **красный** — все четыре отрицательных примера («It was a slow day», «Trains are faster…», …) |
| M2: прощание узнаётся по слову «bye/goodbye» где угодно | отрицательный пример красный | **красный** — «I said goodbye to my friend at the station» |
| M3: из `talk_forbidden.txt` убрано «b1 level» | T6 красный | **красный** — «Honestly, your English is a solid B1 level.» |

Файлы после каждой мутации возвращены и сверены `git status`.

## Машинные гейты

| Гейт | Результат |
|---|---|
| `UV_FROZEN=1 ./scripts/run_checks.sh` | **PASS** — 260 passed (было 218: +42), coverage 95.27%, mypy strict, ruff, размер модулей |
| `pre-commit run --all-files` | **PASS** — jscpd 0 клон-пар |
| `okf_sync_gate.py --base origin/main` | **PASS** — концепт `orchestrator-owns-structure` обновлён по существу |
| `delivery_check.py --diff-base origin/main` | 0 ошибок; предохранитель: 10 файлов, 639 строк чистого прироста при 800 |
| фронт | не тронут |

### Оставшиеся предупреждения

- **Реляционный оракул (§6.5).** Решение человека 2026-08-12 — не добавлять
  зависимость для тестов-свойств; не пересматривалось (`new_dependency: none`).
  Ближе всего к отношению — `test_every_scripted_line_survives_the_talk_contract`:
  он сверяет два артефакта (сценарий и контракт) на всём банке, а не одно значение.
- **T9, T10 без тестов** — по спеке они в следующих поставках: T9 — talk-wiring
  (окно истории), T10 — talk-screen (живой замер).

## Изменение поверхности модели (§14.1)

- `data/prompts/talk_system.txt` — персона разговора: друг-наставник, реакция на
  сказанное и один вопрос в ответ, без оценок и поправок. До подключения (talk-wiring)
  модель её не видит. at=2026-10-17
- `data/talk/talk.yaml` — реплики Генри и открывающие вопросы: звучат дословно, мимо
  модели и енфорсера; каждая проверена тестом на контракт.
- `backend/app/orchestrator/talk.py` — `CHAT_INTENT`: им модель правят при повторе
  после нарушения (`TurnRunner`).
- `data/contracts/talk.contract.yaml` — I3-H1..H3, G3-H1..H3.
- Интервью и разбор: поверхность не менялась; `pace.detect` по умолчанию прежний.

## Ревью рисковых мест (§12.5)

1. **производительность** (`re.compile`, `re.search`) — `_PATTERNS` разговора и
   `_CASUAL_PATTERNS` темпа компилируются один раз при импорте. `classify` гоняет их
   только по короткой реплике: длиннее `MAX_REQUEST_WORDS` (14 слов) — сразу беседа,
   без единой регулярки. Микросекунды на ход при бюджете 3 s до первого звука —
   риска нет.
2. **новый модуль** (`talk`) — `orchestrator/talk.py`. Состояния у
   `TalkOrchestrator` два поля — фаза и выбранные темы, создаётся он на сессию.
   Битый сценарий валит `load_script` с путём в сообщении на старте приложения, а
   не посреди разговора. Что реально может сломаться — ложное узнавание просьбы:
   реплика Антона пропала бы из беседы. Держат отрицательные примеры
   (`test_words_without_the_shape_of_a_request_stay_talk`) и мутация M2.

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` с причиной в STATUS: политика — чистые функции и данные;
голосовой путь не тронут, его подключает talk-wiring.

## Verdict

**READY FOR HANDOFF** — T3–T8 зелёные на уровне решения кода, сторожа проверены
мутациями, машинные гейты зелёные по правилам delivery@2.01 · cqg@2.57; поведение
приложения до подключения не меняется.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **31**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
I3	assert violation is not None and violation.rule_id == "I3-H2_no_grades"
T6	assert turn.feed(sentence) is None
T6	assert violation is not None and violation.check == "max_sentences"  # не длиннее 4
T6	assert talk.start_turn(TurnContext(state="CHAT")).feed("Привет!") is not None
T4	assert detect("It was a slow day.") is PaceRequest.SLOWER
T4	assert detect(utterance, casual=True) is expected
T1	assert plan.state is TalkState.INTRO
T1	assert plan.lines[0] == LINES["intro"]
T1	assert plan.lines[1] in [opener for openers in TOPICS.values() for opener in openers]
T3	assert plan.state is TalkState.TOPIC
T3	assert plan.lines[0] == LINES["topic_switch"]
T3	assert plan.lines[1] != opened
T3	assert plan.remember  # модель обязана знать, о чём теперь спросили
T3	assert all(a != b for a, b in itertools.pairwise(openers))
T6	assert plan.state is TalkState.REQUEST
T6	assert plan.lines == (LINES[line],)
T6	assert plan.repeat_question
T6	assert not plan.remember
T8	assert plan.state is TalkState.GOODBYE
T8	assert plan.lines == (LINES["goodbye"],)
T8	assert plan.finished and talk.finished
T2	assert plan.state is TalkState.CHAT
T2	assert plan.lines == ()
T2	assert plan.seed == LINES["fallback"]
T2	assert talk.on_user("It was fine.").state is TalkState.CHAT
T2	assert plan.state is TalkState.GOODBYE
T2	assert plan.lines == (LINES["time_up"],)
T1	assert set(LINES) <= set(script.lines)
T1	assert len(script.topics) >= 10
T1	assert all(
T6	assert rejected == []
```

✅ **Каждое утверждение ведёт к примеру спеки** (I3 T1 T2 T3 T4 T6 T8), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 10 code (+11 process docs) / +652/-4 (net +648) |
| commits | 6 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 commit(s) after first phase: handoff |
| harness_hardened | yes — backend/tests/test_talk_orchestrator.py (новый оракул) |
| implement_retries | 2 — собранный целиком сервер разговора упёрся в предохранитель (1,100 строк при 800), ветка пересобрана по слоям; дайджест нашёл 7 утверждений без id примера в докстринге — привязаны |
| verify_fails_before_green | 0 — гейты после пересборки зелёные с первого прогона; CI ветки — в PR |
| est_token_or_cost | n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
