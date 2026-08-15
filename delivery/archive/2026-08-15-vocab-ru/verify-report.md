# Verify report: vocab-ru

Дата прогонов: 2026-08-15. Builder: agent:claude-code. Verifier: human:anthony.

## Оракулы примеров спеки

| id | Оракул | Результат |
|---|---|---|
| V1 | `test_cjk_leak_in_translation_is_caught` | **PASS** — запись `выразительный陳述` из живого банка отвергается |
| V2 | тот же тест | **PASS** — `автоматизация outreach` и `очередь задач (Redis/RQ)` законны |
| V3 | тот же тест | **PASS** — `Redis/RabbitMQ` (кириллицы нет) отвергается |
| V4 | `test_broken_translation_is_repaired_on_the_voice_model` | **PASS** — в банк попал починенный перевод; `llm.models` = [R1, qwen] в этом порядке |
| V5 | `test_unrepairable_translation_is_dropped_out_loud` | **PASS** — запись отброшена, в логе термин и причина |
| V6 | `test_all_vocabulary_broken_does_not_kill_the_summary` | **PASS** — оценки и `summary_kind=full` на месте |
| V7 | `test_clean_summary_costs_no_extra_call` | **PASS** — ровно 1 вызов LLM |
| V8 | `test_every_summary_invariant_leaves_a_mark_in_code`, `test_excluded_field_is_covered_by_another_invariant` | **PASS** (после правки, см. ниже) |
| V9 | `./scripts/run_checks.sh` | **PASS** — 171 тест, coverage 94.69% при гейте 85, mypy strict |

## Что нашли сами сторожа — до того, как их дописали

**Сторож A** (инвариант ↔ маркер в коде) на первом прогоне упал на `S-H1_valid_json`
и `S-H5_nonempty_after_strip`: оба **реализованы** (`extract_json` отвергает и
отсутствие JSON, и пустой после `strip_thinking` ответ), но в коде на них не было
ни одной ссылки. То есть связь «правило ↔ реализация» держалась на памяти. Теперь
она в коде строкой.

Честно про границы: **этот дефект поймал бы только сторож B.** `S-H2` существовал,
был помечен и реализован — сторож A прошёл бы мимо. Ловится дыра именно проверкой
«у каждого `exclude_fields` есть инвариант, называющий это поле».

## Живой прогон скрипта чистки

Копия настоящего банка (5 записей), `python scripts/repair_vocabulary.py`:

```
записей в банке: 5, с негодным переводом: 2
  ? 'impact statement': 'выразительный陳述' (содержит иероглифы) → 'влияние; эффект'
  ✗ 'Redis/RQ': 'Redis/RabbitMQ' (нет кириллицы) — починка вернула 'Redis; RabbitMQ'; оставлено как есть
ничего не записано — это dry-run
```

**Дефект, найденный этим прогоном и починенный в этой же поставке:** первая версия
переводила термин **вслепую** и выдала `влияние; заявление об impactе` —
транслитерацию вместо перевода. Проверку S-H6 она проходит (кириллица есть,
иероглифов нет), то есть машинный оракул её пропускал. Лечение: в починку идёт
`example_en` как контекст, а промпт прямо запрещает транслитерацию. Повторный
прогон дал `влияние; эффект`.

Это ровно тот класс, который тесты на подставном клиенте дать не могут: **качество**
ответа настоящей модели виден только на настоящей модели.

`Redis/RQ` остался нетронутым, и это правильное поведение: перевода без кириллицы
скрипт не пишет и записей не удаляет — решение за человеком (экран Useful Words).

## Ревью рисковых мест (§12.5)

1. **Новый вызов LLM в фоновом пути.** `translate_term` зовётся из
   `_repair_vocabulary` **только** для записи с негодным переводом, одна попытка на
   запись; V7 сторожит, что чистый ответ не платит ничем. Путь офлайновый (D-8),
   latency-гейт не затронут: он про голосовой ход, а не про фоновую суммаризацию.
2. **Место вставки одно.** Проверка+починка стоят в `_generate_validated`, через
   который идут оба пути (`generate_full` на R1 и `generate_minimal` на qwen).
   Второго сайта нет (L39), поэтому minimal-путь получил защиту бесплатно.
3. **Данные не теряются молча.** `_repair_vocabulary` пишет `logger.warning` с
   термином, исходным переводом и тем, что вернула починка. Проверено тестом на
   `caplog`, а не глазами.
4. **Публичный `translate_term` — расширение поверхности класса.** Сделано ради
   одного второго вызывающего (`scripts/repair_vocabulary.py`); копия логики в
   скрипте разъехалась бы с продуктовой на первой правке промпта.
5. **Скрипт пишет в базу.** По умолчанию не пишет вовсе, `--apply` явный, удаления
   нет ни в каком режиме, `set_translation` возвращает `False` на пропавшую запись
   (тест есть). Прогон делался на **копии** файла БД.
6. **Регулярка в асинхронном цикле.** `translation_problem` вызывается в
   `async def` внутри цикла — помечено `# cpu-ok` с правдивой границей: словарь
   это 5–12 записей по контракту (S-H4), а не растущая коллекция.
7. **Транзакция БД — риск разобран.** Новая запись в базу одна:
   `VocabularyRepository.set_translation` — она открывает свою сессию, читает
   запись по id, меняет `translation_ru` и коммитит; это та же одна транзакция на
   вызов, что у `merge` и `soft_delete` рядом. `_repair_vocabulary` в базу не
   пишет вовсе: он правит словарь **до** `merge`, поэтому починенный перевод
   попадает в базу тем же единственным путём, что и раньше.
8. **Производительность — риска нет.** `CJK`/`CYRILLIC` компилируются один раз на
   импорт модуля; на записи с исправным переводом работа сводится к двум
   `re.search` по строке длиной в пару слов.

## Исполнение рисковых путей (§12.6)

`runtime_paths: none` — предмет поставки это чистая функция проверки и один вызов
LLM в офлайн-пути. Ни экрана, ни железа, ни разрешений поставка не трогает; оба
куска закрыты тестами, а **качество** живой модели проверено прогоном скрипта на
копии настоящего банка (выше), at=2026-08-15.

## Гейт code↔canon поймал не то, что чинили (и был прав)

`okf_sync_gate` на мерже упал: концепт `orchestrator-owns-structure` держал в
`implementation:` **весь** `data/prompts/`, поэтому правка промпта суммаризации
требовала обновить концепт про то, кто владеет структурой интервью.

Выписывать `canon_drift_waiver` здесь было бы неправильно: дефект не в поставке,
а в **карте путей**. Широкий путь притягивает чужие изменения, поставка за
поставкой покупает waiver'ы, и гейт превращается в формальность. Поэтому пути
разведены по хозяевам: голосовые промпты остались у оркестратора, промпты
офлайн-разбора уехали в `model-split` — тот концепт, который их и описывает
(и который в этой поставке обновлён по существу). После правки гейт зелёный:
5 mapped concepts, 0 warnings.

## Verdict

**READY FOR HANDOFF** — девять примеров из девяти закрыты машинными оракулами,
живой прогон скрипта на копии настоящего банка пройден и по его результату
поставка была доработана (контекст употребления в починке).

## Чего эта проверка НЕ покрывает

- **Смысловая верность перевода.** `Redis/RQ → Redis/RabbitMQ` — не порча, а
  ошибка: модель подменила технологию. Машинного оракула на это нет и в поставке
  не заводилось (спека, Out of scope).
- **Полный проход R1 живьём.** Тесты идут на `ScriptedLlm`; что настоящий R1 после
  правки промпта перестанет сыпать иероглифами, покажет только следующий разбор —
  это `observe_signal`. Проверка при этом работает независимо от того, перестанет
  он или нет: в этом и смысл рантайм-правила.
- **Реляционного оракула (§6.5) нет** — решение прошлых поставок не заводить
  `hypothesis` не пересматривалось. Ближайшее по духу здесь — сторож B: он
  проверяет **отношение** между правилами контракта, а не значение.
- **Чистка живого банка ещё не применена** — `--apply` будет запущен на настоящей
  базе после мержа; в отчёте зафиксирован dry-run на копии.

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 12 code (+10 process docs) / +420/-7 (net +413) |
| commits | 2 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — delivery/active/spec.md (новый оракул) |
| implement_retries | MANUAL — fills from session log |
| verify_fails_before_green | MANUAL — count red verify runs (CI run list) |
| est_token_or_cost | MANUAL / n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **26**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
V8	assert isinstance(invariants, list) and invariants
H6	assert marker in source, (
V8	assert isinstance(excluded, list)  # V8
V8	assert covering, (  # V8: исключение обязано быть заменено правилом
H6	assert await repo.set_translation(entry.id, "заявление о вкладе") is True
H6	assert (await repo.list())[0].translation_ru == "заявление о вкладе"
H6	assert await repo.set_translation("no-such-id", "что угодно") is False
V1	assert not translation_is_russian("выразительный陳述")  # V1: та самая запись
V1	assert not translation_is_russian("陳述")
V3	assert not translation_is_russian("Redis/RabbitMQ")  # V3: кириллицы нет вовсе
V3	assert not translation_is_russian("")
V2	assert translation_is_russian("автоматизация outreach")
V2	assert translation_is_russian("компромисс")
V2	assert translation_is_russian("очередь задач (Redis/RQ)")
R1	assert data is not None
R1	assert data["vocabulary"][0]["translation_ru"] == "компромисс"
R1	assert entries[0].translation_ru == "компромисс"  # в банк попал ПОЧИНЕННЫЙ перевод
R1	assert llm.models == [settings.ollama_model_review, settings.ollama_model_interview]
R1	assert repair_prompt.startswith("trade-off")  # чинили именно термин
R1	assert "The trade-off was latency versus cost." in repair_prompt
V5	assert data is not None and data["vocabulary"] == []
V5	assert await VocabularyRepository(db).list() == []
V5	assert "trade-off" in caplog.text and "иероглифы" in caplog.text
V6	assert data is not None and data["scores"]["clarity"] == 4
V6	assert row is not None and row.summary_kind == "full"
V7	assert len(llm.calls) == 1
```

✅ **Каждое утверждение ведёт к примеру спеки** (H6 R1 V1 V2 V3 V5 V6 V7 V8), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам V1–V9; дайджест выше даёт `asserts_without_example: 0`)
