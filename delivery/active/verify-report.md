# Verify report: soft-skills

Дата прогонов: 2026-08-13. Verifier: human:anthony (builder — agent:claude-code).

## Оракулы примеров спеки

| id | Оракул | Результат |
|---|---|---|
| S1 | `test_question_bank.py::test_session_pool_is_half_behavioral_and_alternates` | PASS |
| S2 | тот же тест, ассерт `pairwise` — ни одной пары одного класса подряд, 4 разных seed'а | PASS |
| S3 | `test_interview_orchestrator.py::test_generic_behavioral_answer_gets_a_second_follow_up` | PASS |
| S4 | `test_interview_orchestrator.py::test_behavioral_story_with_an_ending_moves_on` | PASS |
| S5 | `test_interview_orchestrator.py::test_technical_rule_did_not_move` | PASS |
| S6 | `test_interview_orchestrator.py::test_behavioral_follow_up_asks_about_actions_not_trade_offs` | PASS |
| S7 | `test_interview_orchestrator.py::test_question_kind_travels_in_the_plan` + ассерт `question_kind` в `test_ws_voice.py` | PASS |
| S8 | `test_ws_voice.py` — `row.interview_mode == "technical_and_behavioral"` | PASS |
| S9 | живая сессия, см. ниже | PASS |

Сверх примеров спеки:

- `test_kind_comes_from_the_bank_file` — класс приходит из файла, у технического
  банка ключа нет вовсе (умолчание, а не забытое поле);
- `test_unknown_kind_is_a_loud_failure` — опечатка в классе роняет загрузку, а не
  превращается молча в `technical`;
- `test_pool_survives_a_short_behavioral_bank` — короткий банк не роняет сессию,
  чередование обрывается честно;
- `test_a_real_session_actually_asks_behavioral_questions` — **L22**: «банк
  загружен» и «вопрос задан» проверяются отдельно;
- `test_behavioral_seeds_are_speakable` — **L24/L25**: все восемь seed'ов и
  запасная реплика проходят енфорсер, красная сторона проверена.

## Машинные гейты

| Гейт | Результат |
|---|---|
| `./scripts/run_checks.sh` | **PASS** — module size, ruff, ruff format, mypy strict, pytest |
| Backend pytest | **150 passed**, coverage **94.46%** (гейт 85; было 137 / 94.25%) |
| pre-commit (полный набор) | PASS |
| `jscpd` до и после правки (**L30**) | 0 клон-пар до, 0 после — новая ветка политики дублей не завела |
| `diff-coverage` локально с `LINT_PY_SRC`/`LINT_COV_PKG` (**L32**) | PASS — минимум по изменённым файлам 86.7% (`session_flow.py`), цель 70 |
| `delivery_check.py --diff-base origin/main` | **0 errors**, 1 warning (принят, см. ниже) |
| `okf_sync_gate.py --base origin/main` | OK — concept обновлён в этом же коммите, waiver не потребовался |
| Frontend `npm run build` + `npm test` | PASS, 20 passed — фронт не тронут, и это **замер** |

Circuit breakers: `files=17 net_loc=446 (+497/-51)` при лимитах 25/800 — с запасом,
waiver не потребовался.

### Оставшиеся warning'и

`class M: ни одного реляционного оракула (§6.5)`. Решение прошлой поставки
(не добавлять hypothesis) не пересматривалось. Ближайшее к свойству здесь —
`test_session_pool_is_half_behavioral_and_alternates`, параметризованный четырьмя
seed'ами: он утверждает **отношение** (никаких двух одного класса подряд, счёт
3 и 3), а не конкретный пул, и потому не зависит от того, какие вопросы выпали.
Формы, которую ищет гейт, у него нет. Долг записан, а не спрятан.

`§3.1d: порядок не проверить — пример и тест приехали одним коммитом` (S1, S2,
S5–S8). Факт верен механически и не отражает того, что было: три продуктовых
решения (чередование вместо отдельного режима, своя ветка политики, три из шести)
предъявлены человеку и подтверждены **до первой строки кода** — они и есть
источник ожиданий в примерах. Разложить это по коммитам мешает встречное
требование §12.5 (≥2 цитаты из диффа считаются по `HEAD~1..HEAD`): спека
отдельным коммитом делает цитаты недостижимыми. Противоречие записано как **L30**
в `delivery/archive/INDEX.md` и здесь не «решается» подгонкой истории.

## Ревью рисковых мест (§12.5)

Дифф задел новый модуль данных и ветвление политики. Что может сломаться —
с именами из диффа:

1. **`_STRONG_ANSWER` промахивается классом.** Таблица индексируется
   `self._current_question().kind`, то есть классом **текущего** вопроса.
   Совпадает он с тем, на который отвечали, только потому, что `_may_follow_up`
   зовётся ДО `self._index += 1` — корректность держит порядок операций внутри
   `on_user_answer`. Переставь инкремент выше — ответ на behavioral-вопрос
   начнёт судиться техническим правилом; S3 и S4 покраснеют, потому что смотрят
   на класс через реальный проход политики, а не подставляют его.

2. **`_EPISODE` и `_OUTCOME` — словари, а не понимание.** Ложно-сильный ответ
   лишает пользователя второго допроса, ложно-слабый даёт лишний. Оба исхода
   безобидны у доброго тренера, поэтому словарь и выбран. Осознанно НЕ добавлен
   шаблон `\w+ed`: он ловил бы `speed`, `need`, `red` и систематически завышал
   бы силу ответа.

3. **`pick_session_pool` сменил сигнатуру.** Функция зовётся из `ws_voice` и из
   тестов; забытый вызов ловится mypy — и был пойман (`Missing positional
   argument "behavioral"`), а не рантаймом.

4. **`question_kind` добавлен в `Turn` и в оба плана.** `ReviewPlan` получил поле
   со значением `None`: у хода Mode 2 своего класса нет, поле есть ради общей
   записи в `SessionFlow`. Старые строки транскрипта поля не имеют, но читатели
   (`build_segments`, `_render_transcript`) его не спрашивают — старые сессии
   читаются как раньше.

5. **`interview_mode` сменил значение.** Колонка в `interview_sessions` — текст
   без ограничений; старые записи остаются с прежним значением и описывают
   другую сессию, что и правда. Значение доезжает до `GET /sessions` и до типа
   `frontend/src/types/api.ts`, но не рендерится ни одним компонентом —
   проверено grep'ом по `pages/` и `components/`.

6. **«Деньги» — риска нет, и вот почему.** Маячок подняло слово «цена» из
   разбора размена в комментариях (`_EPISODE`, `pick_session_pool`). Денег в
   проекте нет вообще: инструмент локальный, офлайновый, без платежей и внешних
   вызовов. Ни `question_bank.py`, ни `interview.py`, ни `behavioral.yaml` не
   касаются ничего финансового.

7. **«Производительность» — что подняло и чем это не опасно.** Маячок подняли
   `re.compile` и `re.search` в `interview.py` (`_EPISODE`, `_OUTCOME`). Оба
   шаблона компилируются **на импорте модуля**, ровно как существовавший
   `_DIGIT`, и выполняются **один раз за ход** внутри `_may_follow_up` — по
   реплике длиной в пару сотен слов, вне цикла и вне горячего пути синтеза.
   Нового прохода по данным поставка не вводит: `_STRONG_ANSWER` — словарь из
   двух функций, `pick_session_pool` делает две выборки вместо одной. Замер
   S9 это подтверждает: время ответа после прогрева 2.7–3.5 s, как и до
   поставки, а гейт latency меряется до первого предложения и от политики
   follow-up не зависит вовсе.

## Исполнение S9 — живая сессия

Чем исполнял: настоящий `qwen2.5:14b-instruct` через `OllamaClient`, настоящие
банки вопросов, настоящий `interview.contract.yaml` и `TurnRunner` со
sentence-gating. STT намеренно не задействован — эта поставка его не трогает, а
замена аудио на текст делает прогон повторяемым. at=2026-08-13.

**Пул сессии (seed 42):**

```
1. [technical ] project_overview
2. [behavioral] explaining_tech
3. [technical ] hitl_safety
4. [behavioral] disagreement
5. [technical ] llm_pipeline
6. [behavioral] async_remote
```

**Что реально прозвучало:**

| Ход | Состояние | Реплика Генри |
|---|---|---|
| 1 | FOLLOW_UP / project_overview / technical | «That's significant — can you tell me more about how the tool specifically saves those 120 hours per month?» |
| 2 | FOLLOW_UP / project_overview / technical | «That sounds like a smart decision — what were the key metrics or indicators that made you show those specific examples to your PM?» |
| 3 | CORE_QUEST / explaining_tech / **behavioral** | «That's great — let's make it concrete. Can you give an example of explaining a technical trade-off to someone who isn't technical, like a business stakeholder or team member?» |
| 4 | FOLLOW_UP / explaining_tech / **behavioral** | «I see — can you walk me through how you explained this separation of queues to a non-technical person?» |

**Вердикт: PASS.** Behavioral-вопрос задан и звучит естественно (ход 3), а
follow-up к нему (ход 4) спрашивает **про объяснение человеку**, а не про
trade-off и метрики — новая ветка инструкции доехала до формулировки, а не
осталась в коде. **Нарушений контракта: 0.**

Побочно виден S5 в живом виде: на ходе 2 пользователь рассказал историю
(«PM wanted to ship… in the end we shipped a week later»), но вопрос был
**техническим**, и Генри спросил про метрики — правило не «поехало» на весь код.

Время полного ответа после прогрева — 2.7–3.5 s (первый ход 14 s — холодный
старт модели). Latency-инвариант меряется до первого предложения и этой
поставкой не затронут: новых вызовов модели нет.

## Чего эта проверка НЕ покрывает

- **Уместность самих вопросов** машинного оракула не имеет. Восемь тем подобраны
  под профиль, но подтвердить, что они те самые, может только использование —
  это и есть `observe_signal`.
- **Порог в 40 слов** не пересматривался, хотя для behavioral-ответа он значит
  не то же, что для технического. Пока не мешает; если начнёт — константа одна.
- **Голосом сессия не проверялась.** STT не тронут, но связка «пользователь
  рассказывает историю вслух → whisper → политика» вживую не гонялась.

## CI

Локальные гейты зелёные полностью. Прогон CI на ветке — ссылкой в PR
(**L1:** `CI`, `quality` и `main-guard` — разные workflow, каждый называется
поимённо).

## Verdict

**READY FOR HANDOFF** — все девять примеров спеки подтверждены оракулами, живой
прогон показал behavioral-вопрос и его follow-up при нуле нарушений контракта,
гейты зелёные, breaker'ы не пробиты, waiver'ов нет.

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 17 code (+6 process docs) / +497/-51 (net +446) |
| commits | 1 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — backend/tests/test_question_bank.py (новый оракул), delivery/active/spec.md (новый оракул) |
| implement_retries | MANUAL — fills from session log |
| verify_fails_before_green | MANUAL — count red verify runs (CI run list) |
| est_token_or_cost | MANUAL / n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **36**, из них без ссылки на пример спеки:
**6**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
L24	assert len(bank) == 8
L24	assert turn.feed(question.seed) is None, f"{question.id} режется контрактом"
L24	assert turn.feed("What did you do next, and how did it turn out?") is None
L25	assert red.feed("Tell me about a time you failed. I'd rate that answer 3 out of 5.") is not None
S3	assert len(GENERIC_ANSWER.split()) >= 40, "иначе сработало бы правило длины, а не класса"
S3	assert plan.state == Phase.FOLLOW_UP
S3	assert plan.follow_up_count == 2
S4	assert len(STORY_ANSWER.split()) >= 40
S4	assert plan.state == Phase.CORE_QUEST
S4	assert plan.question_id == "b1"
S5	assert not any(ch.isdigit() for ch in STORY_ANSWER)
S5	assert plan.state == Phase.FOLLOW_UP
S6	assert plan.state == Phase.FOLLOW_UP
S6	assert "personally did" in lowered
S6	assert "turned out" in lowered
S6	assert "trade-off" not in lowered
S6	assert "measurable impact" not in lowered
S6	assert plan.seed == "What did you do next, and how did it turn out?"
S7	assert orch.intro_plan().question_kind == "behavioral"
S7	assert InterviewOrchestrator(make_pool(), clock=FakeClock()).intro_plan().question_kind == (
L22	assert "behavioral" in asked, asked
L22	assert "technical" in asked, asked
-	assert len(technical) == 8
-	assert len(behavioral) == 8
-	assert {q.kind for q in technical} == {QuestionKind.TECHNICAL}
-	assert {q.kind for q in behavioral} == {QuestionKind.BEHAVIORAL}
S1	assert len(pool) == 6
S1	assert len({q.id for q in pool}) == 6  # без повторов
S1	assert pool[0].id == "project_overview"  # marked first: true
S1	assert kinds.count(QuestionKind.TECHNICAL) == 3  # S1
S1	assert kinds.count(QuestionKind.BEHAVIORAL) == 3  # S1
S2	assert all(a is not b for a, b in pairwise(kinds)), kinds  # S2
-	assert [q.kind for q in pool][:3] == [
-	assert len(pool) == 4  # один behavioral исчерпан, чередование обрывается честно
S7	assert [t["question_kind"] for t in turns] == ["technical"] * 3
S8	assert row.interview_mode == "technical_and_behavioral"
```

Привязаны к примерам: **L22 L24 L25 S1 S2 S3 S4 S5 S6 S7 S8**. Остальные 6 — нет.

Читать нужно **только строки с `-` в первой колонке**: их ожидание
ничем не подписано. Подпись: `asserts_reviewed_by: human:… at=…`.

asserts_without_example: 6

asserts_reviewed_by: human:anthony at=2026-08-13 — прочитаны все 6 строк без
примера: четыре про содержимое банков (по 8 вопросов, класс из файла — у
технического ключа `kind:` нет вовсе) и две про короткий банк (чередование
обрывается честно, а не добивается техническими до шести). Ожидания совпадают
с решениями D7 и D9 (`decisions.md`), принятыми до кода.
