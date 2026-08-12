# Verify report

**Date:** 2026-08-12
**Verifier:** agent:claude-code (прогоны) + human:anthony (приёмка ветки)
**asserts_reviewed_by:** n/a (все утверждения ведут к одобренным примерам)
**Commit:** ветка `feat/henry-coach`

## Что делалось

Инверсия персоны Mode 1: Генри — добрый тренер-помощник, а не экзаменатор.
Помогать было запрещено **машиной**: `I1-H2_no_coaching` резал фразы до
озвучки. Контракт, список паттернов, промпт и канон переписаны; шесть чужих
тестов переведены на новую границу.

## Assertion digest (ревью ожиданий, не кода)

Вывод `scripts/lint/assert_digest.sh` дословно:

```
## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **16**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
G1	pytest.param("You should open with the metric, then the architecture.", id="G1-подсказка"),
G1	assert _speak(enforcer, sentence) is None, (  # G1, G2
G3	assert violation is not None, f"оценка прошла в интервью: {sentence!r}"  # G3, G4
G5	assert _speak(enforcer, "Расскажи про архитектуру.") is not None  # G5 — не английский
G5	assert turn.feed("One. ") is None
G5	assert turn.feed("Two. ") is None
G5	assert turn.feed("Three. ") is None
G5	assert turn.feed("Four. ") is not None  # G5 — четвёртое предложение
G5	assert "i'd score" in interview.spec.forbidden_patterns  # оценки остались
G5	assert "great answer" not in interview.spec.forbidden_patterns  # похвала разрешена 2026-08-12
G3	assert violation.matched == "i'd score"  # G3
G3	assert (
G3	assert completed.text == "Why queues?"  # G3 — фраза с баллом обрезана, префикс сохранён
G3	assert "score" not in " ".join(tts.synthesized)  # G3
I1	assert completed.violations[0]["constraint_id"] == "I1-H3_no_scoring"  # G3
G3	assert agent[0]["payload"]["text"] == "Why queues?"  # G3 — балл срезан до TTS
```

✅ **Каждое утверждение ведёт к примеру спеки** (G1 G3 G5 I1), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0
```

Первый прогон дал `asserts_without_example: 3`; заодно парсер принял строку
`I1-H3_no_scoring` внутри assert за id примера. Проставлены явные пометки.

## Shape oracles

- [x] PASS — `pre-commit run --all-files`: 28 хуков, 0 провалов
- [x] PASS — ruff / mypy strict / module size / canon vendor

## Behavior oracles

- [x] PASS — **G1** подсказка проходит («You should open with the metric…»)
- [x] PASS — **G2** похвала проходит («Great answer — you led with the trade-off.»)
- [x] PASS — **G3** баллы режутся («I'd score that a four.»)
- [x] PASS — **G4** итоговый разбор режется («Overall your performance today was solid.»)
- [x] PASS — **G5** нетронутые инварианты держатся: русский и 4-е предложение
- [x] PASS — **G6** живая модель помогает — дословно в `eval-smoke.md`
- [x] PASS — сьют **104 теста** (было 98), покрытие 93.01%
- [x] PASS — `delivery/evals/smoke/run.sh`

**Красная сторона:** на СТАРОМ контракте новый тест давал 4 провала из 6 —
три подсказки резались, итоговый разбор проходил.

## Исполнение рисковых путей (§12.6)

`runtime_paths: data/contracts/interview.contract.yaml` — контракт исполняется
перед озвучкой каждой фразы; ошибка в нём не видна ни сборке, ни типам.
Прогоны **at=2026-08-12**:

| Что исполнял | Чем | Что увидел | at |
|---|---|---|---|
| контракт на старом дереве | новый тест границы | 4 провала из 6 — граница сдвинута | 2026-08-12 |
| контракт после правки | он же | 6 из 6 | 2026-08-12 |
| поведение модели с новым промптом | живой запрос к qwen2.5:14b-instruct | подсказывает и переформулирует | 2026-08-12 |
| весь сьют | pytest | 104 passed, старые инварианты целы | 2026-08-12 |

## Ревью рисковых мест (§12.5)

0. **Что смотрел:** дифф целиком — контракт, список паттернов, системный
   промпт, docs 09 и 13, четыре тест-файла.

1. **Контракт стал слабее — это цель, но и риск.** Худший исход: в интервью
   просочится разбор. Закрыто G3/G4 и расширенным списком: добавлены
   «overall your», «final assessment», «the rubric», «you passed», которых
   раньше не было вовсе — до правки «Overall your performance…» проходило.
2. **Шесть тестов переписаны — риск потерять покрытие.** Ни один не удалён:
   каждый проверял механику (обрезание, схема события, откат на seed, живой
   ws-ход) на примере coaching и переведён на пример со счётом. Покрытие
   93.01% не изменилось.
3. **Персона в контракте сменилась** (senior_colleague → supportive_coach).
   Проверка `mode_persona` — prompt-level, рантайм её не исполняет; значение
   служит документацией и сверкой с промптом.
4. **Транзакция БД — риска нет, потому что** дифф её не касается: YAML, txt,
   промпт, markdown и тесты. Ни репозиториев, ни сессий в диффе нет.
5. **Интеграция (Ollama) — параметры вызова не тронуты.** Системный промпт
   вырос примерно на 60 токенов, бюджет doc 20 (system ≤ 400) держится.
   Живой вызов выполнен, ответ корректный.
6. **Безопасность и деньги** — локальные модели, внешних платных вызовов нет.
7. **Цепочка гейтов** не тронута; добавлен один тест-файл.

## Spec coverage gaps

- **Тон машиной не проверяется** — и не будет: doc 13 признаёт это для I1-S1.
  «Добрый» проверяется живой сессией и человеком, не тестом. Ограничение
  названо, а не закрыто.
- Три оставшиеся просьбы человека (темп речи, soft skills, выразительность)
  в эту поставку не входят — поставки 2–4.
- Реляционного оракула (`@given`) нет: предмет — списки паттернов.

## Verdict

- [x] **READY FOR HANDOFF**
- [ ] NEED CONVERGE
- [ ] BLOCKED

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 9 code (+6 process docs) / +245/-70 (net +175) |
| commits | 2 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — backend/tests/test_contract_coach_boundary.py (новый оракул), delivery/active/spec.md (новый оракул) |
| implement_retries | **2** — (1) первая версия теста границы была бесполезной: фразы случайно обходили запрещённые паттерны, тест зеленел ДО правки; (2) `prompt_level_only` не прошёл валидацию загрузчика — prompt-level правила здесь живут комментарием, как I1-S1 |
| verify_fails_before_green | заполняется после первого прогона CI |
| est_token_or_cost | n/a — локальные модели |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
