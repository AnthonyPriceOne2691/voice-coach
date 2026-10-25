# Verify report: mutation-gate — мутационный гейт судит на проекте и стоит в CI

**Date:** 2026-10-23
**Verifier:** human:anthony
**asserts_reviewed_by:** n/a (все утверждения ведут к одобренным примерам)
**CI run:** https://github.com/AnthonyPriceOne2691/voice-coach/actions/runs/40017143636
**Commit:** e795a92

Builder: agent:claude-code (worktree `.claude/worktrees/agent-ad938971a5a5f44a4`).
Ветка перебазирована на `a4a0dce` (контур cqg@2.74 · delivery@2.07) и запушена
`--force-with-lease` ДО поправки ведущего, что force push в проекте запрещён; дальше
синхронизация только `git merge origin/main`.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| M1 | `test_repo_root.py::test_real_layout_resolves_to_the_repo_with_data` | **PASS** |
| M2 | `test_repo_root.py::test_mutants_copy_resolves_to_the_same_root` — копия настоящего `config.py` в `backend/mutants/app/` исполняется | **PASS**; на `parents[2]` тест красный — копия отвечает `<repo>/backend` (MG1) — `repro_test` |
| M3 | `test_repo_root.py::test_worktree_inside_the_repo_reads_its_own_data` | **PASS** |
| M4 | `test_repo_root.py::test_missing_data_is_a_named_error` — три раскладки | **PASS** |
| M5 | `test_mutation_copy.py` — сторож и самопроверка сторожа | **PASS**; на дереве до правки (`git archive` коммита с тестами) — красный, называет `VocabularyRepository.list → list` |
| M6 | гейт на диффе talk-screen (`eval-smoke.md`) | **PASS** — «убито 497 из 806 (61%) — OK» вместо «не просудил НИЧЕГО» |
| M7 | обратный прогон на `voice/warmup.py` (`eval-smoke.md`) | **PASS** — без утверждений 42%, ERROR, exit 1; с ними 95%, OK |
| M8–M10 | `test_warmup.py` (6 тестов) | **PASS**; доля убитых `voice/warmup.py` 11% → 95% |
| M11 | доли по девяти модулям (`eval-smoke.md`) | **PASS** — все ≥ 60%: от 66.7% (`ws_voice.py`) до 95.2% (`warmup.py`) |
| M12 | `contracts/enforcer.py` | **PASS** — 21 → 171 мутант, убито 80.7% |
| M13 | шаг в CI PR #44 | **PASS** — «убито 267 из 324 (82%) — OK» за 85 s при бюджете 300; после слияния `main` и M15 — то же за 86 s (прогон 40017143636, `e795a92`) |
| M14 | `test_storage.py::test_vocabulary_merge_keeps_going_and_list_filters` | **PASS**; доля `vocabulary.py` 61% → 84% |
| M15 | `test_repo_root.py::test_tests_take_the_repo_root_from_app_config` | **PASS**; до правки красный — `['test_language_check.py:10', 'test_tips_policy.py:27']` (пришли из main с talk-check-core) |

## Находка верификации: `api/ws_voice.py` в 300 s раннера не укладывается

Замер двумя временными draft-PR (#45 и #47): база — `feat/mutation-gate`, в диффе только
docstring `ws_voice.py`, бюджет поднят до 2400 s, чтобы получить полную цену. Оба PR
закрыты, ветки удалены.

| Где | Ядер | `timeout_multiplier` | Время шага | Вердикт |
|---|---|---|---|---|
| CI, #45 | 2 (`nproc`) | 15 (умолчание mutmut) | **1,854 s** (30 min 54 s) | убито 502 из 748 (67%) — OK |
| CI, #47 | 2 | 3 | **847 s** (14 min 07 s) | убито 496 из 741 (66%) — OK |
| локально, тихая машина (load 2–15) | 10 | 15 | ≈ 300 s | 496 из 744 (66.7%), timeout 57 |
| локально, тихая машина | 10 | 3 | 86 s | 490 из 738 (66.4%), timeout 63 |

Куда уходит время. Локально при умолчании рабочее время — 2,106 s, из них 1,488 s (71%)
съедают 57 повисших мутантов. WS-тест ждёт кадр, которого мутант не пошлёт, пока mutmut
не снимет процесс по таймауту (оценка тестов + 1) × 15. При × 3 рабочее время — 793 s,
повисшие — 316 s, выжившие те же 248.

Вывод. Бюджет канона в 300 s на деле определяется самым дорогим файлом, а не диффом.
Другие модули укладываются с запасом: PR #44, 324 мутанта, — 85 s. А PR, трогающий
`ws_voice.py`, на раннере с двумя ядрами получит «бюджет исчерпан — данные неполные,
гейт не судит», то есть красный шаг: и с умолчанием, и с × 3.

## Находка после слияния main: класс вернулся через три часа

Прогон quality на `bfb5b79` (40015859050) — шаг мутаций красный: «✗ мутационный гейт не просудил
НИЧЕГО», `ERROR tests/test_tips_policy.py - FileNotFoundError: …/backend/data/contracts/talk.contract.yaml`.
CI судит PR слитым с `main`, а `main` за это время принял talk-check-core (`384f8b2`): два новых
тестовых файла считали корень `Path(__file__).resolve().parents[2]` — под копией mutmut это
`backend/`. Правка тринадцати файлов закрыла случаи, а не класс. Закрыто сторожем на перечень
(M15: все `backend/tests/*.py`, `parents[N]` от `__file__` при N ≥ 2) и правкой двух файлов;
`main` слит обычным слиянием (`600e391`), а не перебазированием.

## Что ещё нашёл гейт (названо, не чинилось в этой поставке)

- **Слепое пятно декораторов.** mutmut 3.7 не мутирует декорированные классы и функции
  (кроме одиночных `@staticmethod`/`@classmethod`). Исправлено там, где это несущий
  модуль, — `TurnEnforcer`; вне M11 остаются маршруты FastAPI, свойства,
  `Turn`/`TranscriptBuffer` (143 строки функций).
- **Знаменатель гейта.** Канонный вердикт — `killed / (killed + survived)`; `timeout` и
  `no tests` не входят ни в одну часть. Функция диффа без покрывающего теста выпадает
  из доли молча, если рядом есть судимые. Направление — в отчёт канону.
- **gate-coverage прощал неподключённый гейт.** Канонная причина «CI-only на PR»
  проверяется РАНЬШЕ поиска скрипта в конфигах (`gate_coverage_roles.sh`, ветка
  `not_wired_reason`) и не проверяет, что скрипт есть в CI: мутационный гейт числился
  «не подключён осознанно» с развёртывания контура, не будучи подключённым нигде, и
  печатает ту же строку теперь, когда подключён. В отчёт канону.
- **TS-половина** на fullstack не судится: канон считает python, о фронте печатает
  предупреждение. Stryker в `frontend/` не установлен.
- **Выжившие в енфорсере, которые не эквивалентны** — граница G1-H2 (ровно 400
  символов), граница Q-ссылок Mode 2, `states` у `question_or_ack`, поля
  `sentence_index`/`matched` события нарушения — перечислены в `eval-smoke.md`
  кандидатами в тесты: модуль выше порога, догонять их здесь не стал.

## Мутации (сторож обязан краснеть)

| Мутация | Ожидание | Результат |
|---|---|---|
| MG1: вернуть `REPO_ROOT = Path(__file__).resolve().parents[2]` | M2 красный | **красный** — копия в `mutants/` отвечает `<repo>/backend` |
| MG2: снять `from __future__ import annotations` с `vocabulary.py` | M5 красный | **красный** — `['backend/app/storage/repositories/vocabulary.py: VocabularyRepository.list → list']` |
| MG3: вырезать все `assert` из `test_warmup.py` | гейт на `warmup.py` красный | **красный** — 42%, ERROR, exit 1 |
| MG4: `exc_info=True` → `False` в `warm_up` | M10 красный | **красный** — после правки теста (был выживший: `False is not None`) |

## Машинные гейты

| Гейт | Результат |
|---|---|
| `pytest` (бэкенд, после слияния `384f8b2`) | **PASS** — 318 passed, coverage 96.06% (было 272 / 95.6% на `main` до этой поставки) |
| `mypy app` (strict), `ruff check`, `ruff format --check` | **PASS** — 0 ошибок, 57 файлов |
| `STRICT=1 pre-commit run --all-files` | **PASS** — 28 хуков |
| pre-push (smoke S1–S6, delivery-gate, baseline-ratchet, new-dependency) | **PASS** — на каждом push |
| `contour_doctor.py` | **DEAD 0** — AUTO 47 · WEAK 17 · ABSENT 0 · TOOL 3 · SKIP 1; «стражи исполнения: mutmut его найдёт» — AUTO |
| мутационный гейт на диффе PR, локально | **PASS** — «убито 267 из 324 (82%)»: 29 s при load 9, после слияния `384f8b2` — 21 s при load 6 |
| CI PR #44: `backend`, `gates`, `delivery` | **PASS** — последние прогоны 40017143667 и 40017143636 (`e795a92`), до них 40007693513 и 40007693515; первый прогон quality (40002688227) был красным в джобе delivery: `stack:` в STATUS отставал от снимка — main ушёл на контур 2.74, пока PR был открыт |
| `delivery_check.py --diff-base origin/main` | 0 ошибок, 3 предупреждения (ниже); предохранитель — 23 файла кода, net +394 строки при лимитах 25 и 800 |

### Оставшиеся предупреждения

- ~~**`human_ok_spec: deferred`**~~ — снято: примеры M1–M15 подписаны человеком на мерже (human:anthony, 2026-10-25), как он решил 2026-10-23.
- **Реляционный оракул (§6.5)** — решение человека 2026-08-12: зависимость для
  тестов-свойств не добавляется.
- **§3.1d, порядок M15** — пример M15 и его сторож приехали одним коммитом (`c8cb25f`): класс
  нашёлся красным шагом CI после слияния `main`, сторож писался сразу на находку. Примеры
  M1–M14 закоммичены спекой раньше кода (`3d28b6d`).

## Изменение поверхности модели (§14.1)

- `backend/app/config.py` — изменён только поиск корня репозитория (`find_repo_root`,
  `RepoRootNotFoundError`, `ROOT_MARKERS`): `REPO_ROOT` в обычной раскладке тот же
  каталог (M1), пути `prompts_dir`, `contracts_dir`, `knowledge_dir`,
  `questions_dir`, `talk_dir` и модели, температуры, бюджеты токенов, `num_ctx` не
  тронуты. Что модель видит и с какими параметрами — не меняется. at=2026-10-23

## Ревью рисковых мест (§12.5)

1. **новый модуль** (`test_repo_root`, `test_mutation_copy`, `test_warmup`) — тесты, у
   продукта нового модуля нет. Что реально может сломаться — `find_repo_root`: если
   выше по дереву окажется чужой каталог с `data/prompts` и `data/contracts`, корнем
   станет он. Поиск идёт от файла вверх и берёт БЛИЖАЙШИЙ — для worktree внутри
   репозитория это сам worktree (M3); без данных — `RepoRootNotFoundError` на импорте,
   громко, а не тихо пустые пути (M4).
2. **енфорсер** (`TurnEnforcer`) — снят `@dataclass`, `__init__(spec, ctx)` повторяет
   поля; `ContractEnforcer.start_turn` создаёт его по ключевым словам, как раньше.
   Сравнения и `repr` dataclass'а нигде не использовались (поиск по `app/` и
   `tests/`); тесты контрактов и `turn_runner` без правок зелёные.
3. **конфиг mutmut** (`pytest_add_cli_args`) — `--no-cov` действует только в прогонах
   mutmut: обычный `pytest` по-прежнему краснеет ниже 85% (`ci.yml`, `run_checks.sh`).
4. **отложенные аннотации** в `vocabulary.py` — аннотации этого модуля становятся
   строками; во время исполнения их не читает никто (не pydantic, не FastAPI-маршрут),
   mypy их понимает.

5. **производительность** (`re.compile` у `DEPTH` в `test_repo_root.py`, `rglob`/`ast.parse` у сторожа `test_mutation_copy.py`) — риска нет, потому что это тесты-сторожа: регулярка компилируется один раз на модуль, проход идёт по ~40 файлам тестов и ~55 модулям пакета — миллисекунды; в коде продукта новых разборов в цикле и выборок без границы нет.

## Исполнение рисковых путей (§12.6)

`runtime_paths: frontend/src/hooks/useVoiceSession.ts` — диффом не задет. Исполнено
то, что эта поставка меняет: мутационный гейт — канонным скриптом на трёх диффах
(talk-screen, обратный прогон `warmup.py`, дифф PR) и шагом CI PR #44; настоящий
`config.py` — исполнением копии в раскладке `mutants/` (M2). Живые модели не
запускались. at=2026-10-23

## Verdict

**READY FOR HANDOFF** — M1–M15 зелёные, шаг CI судит дифф PR (82% за 85 s), CI PR #44
зелёный. Открытое закрыто человеком 2026-10-25: бюджет на `api/ws_voice.py` — вариант (а),
подписи под примерами и под `canon_drift_waiver` стоят (раздел «Решения человека 2026-10-25»).

## Решения человека 2026-10-25

- **Бюджет — вариант (а)** (human:anthony): `timeout_multiplier = 3.0` в `[tool.mutmut]`,
  `BUDGET_SEC: "900"` у шага мутаций, `timeout-minutes: 30` у джобы `gates`; обе адаптации
  объявлены в `scripts/lint/adapted.json`. Разрез `ws_voice.py` — при следующей его правке.
- **Подписи** (human:anthony): `human_ok_spec: yes` под M1–M15 и `canon_drift_waiver`
  (model-split, sentence-streaming) — `by=human:anthony at=2026-10-25`.
- Вопрос 3 (тесты на неэквивалентных выживших енфорсера) человек не решал — остаётся открытым.

## Open questions — к человеку (2026-10-23)

1. **Бюджет на `api/ws_voice.py` нужно решить до первого PR с этим файлом.** Варианты с ценой:
   - (а) в `[tool.mutmut]` поставить `timeout_multiplier = 3.0`, в шаге — `BUDGET_SEC: "900"`, у джобы
     `gates` — `timeout-minutes: 30`, и записать это в `adapted.json`. Цена: PR с `ws_voice.py`
     ждёт мутаций около 14 min, остальные PR не платят ничего — у них шаг 1–2 min. Вердикт на
     замере тот же (67% → 66%, выживших 246 → 245).
   - (б) только `timeout_multiplier = 3.0` при бюджете канона — **не хватит**: 847 s > 300.
   - (в) разрезать `ws_voice.py`. В нём 499 строк при потолке 500, так что следующая правка
     всё равно потребует разреза. Тогда PR судит только тронутую часть; хватит ли бюджета
     после разреза, надо мерить.
   - (г) ничего не делать: PR с `ws_voice.py` будет красным, пока решение не принято.
   Рекомендация агента — (а) сейчас и (в) при следующей правке `ws_voice.py`.
2. **Подписи human:anthony:** примеры M1–M15 (`human_ok_spec`) и `canon_drift_waiver`
   (model-split, sentence-streaming) — сейчас в нём стоит `by=agent:claude-code`.
3. **Неэквивалентные выжившие енфорсера** — граница G1-H2 (ровно 400 символов), Q-ссылки
   Mode 2, `states` у `question_or_ack`, поля события нарушения. Брать ли тесты на них
   отдельной поставкой?
4. **Force push.** Ветка перебазирована на `a4a0dce` и запушена `--force-with-lease` до
   того, как пришла поправка ведущего о запрете force push. Дальше синхронизация только
   слиянием `origin/main`.

## Уроки

- **L91:** «гейт не просудил» оказалось тремя стенами подряд, и каждую
  видно только после предыдущей: копия `vocabulary.py` не импортировалась, корень
  уезжал в `backend/`, порог покрытия судил мутированную копию. Замер 18.10 назвал
  вторую, потому что первую на этом коде не видел никто — гейт не гоняли ни в CI, ни
  руками. Чинить «инструмент не судит» — значит гнать до вердикта, а не до следующего
  стека; и код, который ищет ресурсы глубиной пути (`parents[N]`), ломается под
  любым инструментом, копирующим пакет, — искать по маркерам данных. Правка тринадцати файлов закрыла случаи, а не класс: через три часа talk-check-core принёс ещё два `parents[2]`, и шаг в CI снова «не просудил» — закрывает класс только сторож на перечень (M15, тот же урок, что L72).
- **L92:** доля убитых без числа мутантов — не вердикт. mutmut 3.7
  молча не мутирует декорированное, и `@dataclass` на `TurnEnforcer` спрятал от гейта
  все проверки контракта: на файле стояло «100%» по 21 мутанту фабрики. Сверять надо
  население (сколько мутантов у каких функций), а не процент; то же у знаменателя:
  `timeout` и `no tests` из доли выпадают молча.
- **L93:** гейт, «подключённый» причиной, а не конфигом, не
  подключён. gate-coverage принимал канонное «CI-only на PR» раньше, чем искал скрипт в
  конфигах, и мутационный гейт числился осознанно неподключённым с развёртывания
  контура. А бюджет — свойство самого дорогого файла, а не диффа: 300 s хватает PR #44
  (85 s), а `api/ws_voice.py` их не укладывает — мерить до того, как вешать шаг.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **38**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
M5	assert offenders == [], (
M5	assert _shadowed(ast.parse(source)) == ["Repo.list → list"]
M5	assert _postponed(ast.parse("from __future__ import annotations\n" + source))
M5	assert not _postponed(ast.parse(source))
M1	assert (REPO_ROOT / "data" / "prompts").is_dir()
M1	assert (REPO_ROOT / "data" / "contracts").is_dir()
M1	assert (REPO_ROOT / "backend" / "app" / "config.py").is_file()
M1	assert Settings.model_fields["contracts_dir"].default == REPO_ROOT / "data" / "contracts"
M2	assert repo.resolve() == plain.REPO_ROOT
M2	assert repo.resolve() == mutant.REPO_ROOT
M3	assert find_repo_root(config) == worktree.resolve()
M4	assert str(config) in message
M4	assert "data/prompts и data/contracts" in message
M15	assert offenders == [], (
M14	assert await repo.merge(batch, session_id="s2") == 2
M14	assert set(entries) == {"trade-off", "blast radius", "headroom"}
M14	assert entries["trade-off"].times_seen == 2
M14	assert (blast.type, blast.category) == ("phrase", "architecture")
M14	assert blast.context_note_en == "Use when scoping a risky change."
M14	assert blast.session_id == "s2"
M14	assert [e.term_en for e in await repo.list(category="architecture")] == ["blast radius"]
M14	assert [e.term_en for e in await repo.list(sort="alpha")] == [
M8	assert len(stt.wavs) == 1
M8	assert wav.getnchannels() == 1
M8	assert wav.getsampwidth() == 2
M8	assert wav.getframerate() == 16000
M8	assert wav.getnframes() == 16000
M8	assert set(wav.readframes(16000)) == {0}
M9	assert llm.calls == [{"messages": session, "model": MODEL, "temperature": 0.0, "max_tokens": 1}]
M9	assert llm.calls[0]["messages"] == [{"role": "user", "content": "hi"}]
M9	assert llm.pulled == 1
M10	assert len(llm.calls) == 1
M10	assert record.getMessage() == "STT warmup failed"
M10	assert record.exc_info is not None
M10	assert record.exc_info[0] is RuntimeError  # причина — сам отказ whisper
M10	assert record.getMessage() == "LLM warmup failed"
M10	assert record.exc_info is not None
M10	assert record.exc_info[0] is ConnectionError  # причина — сам отказ модели
```

✅ **Каждое утверждение ведёт к примеру спеки** (M1 M10 M14 M15 M2 M3 M4 M5 M8 M9), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 25 code (+9 process docs) / +451/-47 (net +404) |
| commits | 17 |
| time_to_accepted_spec | spec drafted, not yet accepted |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — .github/workflows/quality.yml, backend/tests/test_mutation_copy.py (новый оракул), backend/tests/test_repo_root.py (новый оракул), backend/tests/test_warmup.py (новый оракул) |
| implement_retries | 3 — гейт пробивался через три стены по одной (копия vocabulary.py → корень → порог покрытия), каждая видна только после предыдущей; плюс тест M10 доправлен после выжившего `exc_info=False` |
| verify_fails_before_green | 2 — (1) quality 40002688227 красный в джобе delivery: «STATUS says 2.06/2.69, snapshot has 2.07/2.74» — main ушёл на контур 2.74; после перебазирования и `stack:` — зелёный (40007693515); (2) quality 40015859050 красный в шаге мутаций: «не просудил» — новые тесты main считали корень `parents[2]`; закрыто сторожем M15 и правкой двух файлов |
| est_token_or_cost | n/a; раннер CI на замеры ws_voice.py — около 50 мин (#45 и #47) |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
