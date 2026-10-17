# Verify report: regenerate-mode-neutral

Дата прогонов: 2026-10-17. Builder: agent:claude-code. Verifier: human:anthony.

## Оракулы mini-spec

| id | Оракул | Результат |
|---|---|---|
| R1 | `test_turn_runner.py::test_regenerate_hint_carries_no_interview_era_rules` — контракт разбора, первое предложение на кириллице | **PASS** — до правки красный по правильной причине: `в подсказке перегенерации остался 'interview rules'` |
| R2 | `test_turn_runner.py::test_violation_on_first_sentence_regenerates` — контракт интервью | **PASS** — до правки красный: старый текст закреплял «violated interview rules»; теперь сверяется отсутствие всех пяти остатков |
| R3 | `test_turn_runner.py::test_double_failure_falls_back_to_seed` — обе попытки нарушают | **PASS** без изменений теста: лестница восстановления та же, озвучен только `seed` |

Различение проверено подстановкой кода до правки: `git stash` правки
`turn_runner.py` → `2 failed, 6 passed` (R1 и R2), правка на месте → `8 passed`.

## Машинные гейты

| Гейт | Результат |
|---|---|
| `UV_FROZEN=1 ./scripts/run_checks.sh` | **PASS** — 213 тестов бэкенда (было 212: +1 тест R1), coverage 95.23%, mypy strict, ruff, размер модулей |
| хуки на коммите `8da4a01` (ruff, mypy, inline-prompt, jscpd, complexity, layers, secrets, canon-vendor) | **PASS** |
| `delivery_check.py` | 2 ошибки — обе про просроченные окна наблюдения поставок 2026-10-01 (`live-transcript-setting`, `vad-silence-setting`); к этой поставке отношения не имеют и закрываются наблюдением человека. Своих ошибок 0 |

## Изменение поверхности модели (§14.1)

- `backend/app/voice/turn_runner.py` — текст `STRICT_REGENERATE`, подсказки, с которой
  модель переписывает ответ после нарушения контракта на первом предложении. Было:
  «violated interview rules … Max 3 sentences. One question OR a short acknowledgment.
  No coaching, praise, or scoring». Стало: «broke a rule of this session … Rewrite it in
  English only, keeping your role, the limits you were given and the original intent».
  Что меняется в поведении: на повторе модель больше не получает приказа выбросить
  подсказку и похвалу и уложиться в три предложения; в интервью это совпадает с
  контрактом 2.0 (тренер), в разборе — с его лимитом 5 предложений и работой «похвала и
  совет». Что не меняется: те же проверки енфорсера на повторном ответе. at=2026-10-17

## Ревью рисковых мест (§12.5)

Классификатор отнёс дифф к безопасности: правка живёт в лестнице восстановления
после нарушений контракта. Что может сломаться — с именами из диффа:

1. **Интервью на повторе ответит длиннее трёх предложений.** Подсказка больше не
   повторяет лимит. Держит машина: `G1-H1_max_sentences` = 3 и `G1-H2_max_chars` = 400
   проверяют повторный ответ так же, как первый, — лишнее обрезается, двойной провал
   уходит в `seed` (R3). Лимит есть и в `interviewer_system.txt`.
2. **Баллы на повторе.** Подсказка больше не говорит «no scoring». Держит
   `I1-H3_no_scoring` (`forbid_patterns` + `interview_forbidden.txt`) — исполняется на
   каждом предложении любой попытки, до озвучки.
3. **Ход интервью без вопроса.** Фразы «One question OR a short acknowledgment» больше
   нет. Держит `G1-H4_question_or_ack` в конце хода: вопроса нет — дописывается `seed`.
4. **Подсказка стала общей и для будущих режимов.** Это намеренно: в ней нет правил ни
   одного режима, кроме общего для всех контрактов «English only» (`I1-H1`, `I2-H1`,
   `S-H2`). Свой текст на режим из `data/prompts/` — долг, записан в `tasks.md` и в
   комментарии у константы.

Риск выше ровно один — модель на повторе станет многословнее, чем раньше. Он не
доходит до пользователя: все прежние ограничения исполняет енфорсер, а не подсказка.

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` с причиной в STATUS: меняется содержимое строки, а не тракт.
Живой прогон на настоящей модели не проводился — инференс только с разрешения
человека; поведение на модели — сигнал наблюдения (`observe_signal`).

## Независимый прогон на handoff (2026-10-17)

Сессия voice-interview-coach — не builder: поставку собрала сессия local-web-agent,
передала её 17.10 и больше в репозитории не работает. Прогон на ветке, перенесённой
на `main` `dac424a` (контур `delivery@2.01 · cqg@2.55`):

| Проверка | Результат |
|---|---|
| дифф против mini-spec | правка ровно в `STRICT_REGENERATE` и двух тестах; R1–R3 покрыты, лишнего нет |
| `pytest tests/test_turn_runner.py` | **8 passed** |
| различение: `turn_runner.py` из `main` подставлен на место правки | **2 failed** (R1 `test_regenerate_hint_carries_no_interview_era_rules`, R2 `test_violation_on_first_sentence_regenerates`), 6 passed; правка возвращена `git checkout HEAD --` |
| `UV_FROZEN=1 ./scripts/run_checks.sh` | **PASS** — 213 passed, coverage 95.23%, mypy strict, ruff, размер модулей |

## Verdict

**READY FOR HANDOFF** — R1–R3 зелёные, различение подтверждено подстановкой прежнего
текста дважды (builder и независимый прогон), машинные гейты зелёные по правилам
delivery@2.01 · cqg@2.55. Поведение на настоящей модели — сигнал наблюдения до
2026-11-07, не условие закрытия.

## Дайджест утверждений

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **8**, из них без ссылки на пример спеки: **0**.

```
R2	assert "broke a rule" in hint
R2	assert "ask impact" in hint
R2	assert leftover not in hint
L24	assert isinstance(completed, AgentCompleted)
L24	assert completed.violations[0]["recovery"] == "regenerate"
R1	assert leftover not in hint, f"в подсказке перегенерации остался {leftover!r}"
R1	assert "praise the answer and suggest a sharper opening" in hint  # намерение сохранено
R1	assert "English only" in hint  # общее правило всех трёх контрактов остаётся
```

Два утверждения дайджест привязал к L24 — ближайшей метке из докстроки теста. На деле
это проверки того же теста R1: «повтор действительно случился» — предусловие, без
которого сверка подсказки была бы пустой.

asserts_without_example: 0

asserts_reviewed_by: n/a (класс S — правило §3.1d уровня 3 для M/L; ожидания R1–R3 из mini-spec)

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 2 code (+3 process docs) / +58/-6 (net +52) |
| commits | 2 |
| time_to_accepted_spec | n/a (no spec.md in history — class S?) |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | no |
| implement_retries | n/a — журнал сессии builder (local-web-agent) этой сессии недоступен; в отчёте builder повторов реализации не записано |
| verify_fails_before_green | 0 — локальные прогоны зелёные с первого раза в обеих сессиях (builder 17.10 и независимый прогон на dac424a); CI ветки — в PR |
| est_token_or_cost | n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
