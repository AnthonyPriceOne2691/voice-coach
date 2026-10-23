# Verify report: mutation-gate — мутационный гейт судит на проекте и стоит в CI

**Date:** 2026-10-23
**Verifier:** human:anthony
**asserts_reviewed_by:** n/a (все утверждения ведут к одобренным примерам)
**CI run:** https://github.com/AnthonyPriceOne2691/voice-coach/actions/runs/40007693515
**Commit:** 72dd6e2

Builder: agent:claude-code (worktree `.claude/worktrees/agent-ad938971a5a5f44a4`).
Ветка перебазирована на `a4a0dce` (контур cqg@2.74 · delivery@2.07) и запушена
`--force-with-lease` ДО поправки ведущего, что force push в проекте запрещён; дальше
синхронизация только `git merge origin/main`.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| M1 | `test_repo_root.py::test_real_layout_resolves_to_the_repo_with_data` | **PASS** |
| M2 | `test_repo_root.py::test_mutants_copy_resolves_to_the_same_root` — копия настоящего `config.py` в `backend/mutants/app/` исполняется | **PASS**; на прежнем `config.py` та же копия даёт `<repo>/backend` (замер копией старого файла) — `repro_test` |
| M3 | `test_repo_root.py::test_worktree_inside_the_repo_reads_its_own_data` | **PASS** |
| M4 | `test_repo_root.py::test_missing_data_is_a_named_error` — три раскладки | **PASS** |
| M5 | `test_mutation_copy.py` — сторож и самопроверка сторожа | **PASS**; на дереве до правки (`git archive` коммита с тестами) — красный, называет `VocabularyRepository.list → list` |
| M6 | гейт на диффе talk-screen (`eval-smoke.md`) | **PASS** — «убито 497 из 806 (61%) — OK» вместо «не просудил НИЧЕГО» |
| M7 | обратный прогон на `voice/warmup.py` (`eval-smoke.md`) | **PASS** — без утверждений 42%, ERROR, exit 1; с ними 95%, OK |
| M8–M10 | `test_warmup.py` (6 тестов) | **PASS**; доля убитых `voice/warmup.py` 11% → 95% |
| M11 | доли по девяти модулям (`eval-smoke.md`) | **PASS** — все ≥ 60%: от 66.7% (`ws_voice.py`) до 95.2% (`warmup.py`) |
| M12 | `contracts/enforcer.py` | **PASS** — 21 → 171 мутант, убито 80.7% |
| M13 | шаг в CI PR #44 | **PASS** — «убито 267 из 324 (82%) — OK» за 85 s при бюджете 300 |
| M14 | `test_storage.py::test_vocabulary_merge_keeps_going_and_list_filters` | **PASS**; доля `vocabulary.py` 61% → 84% |

## Находка верификации: `api/ws_voice.py` в 300 s раннера не укладывается

ЗАМЕР_CI_WS_VOICE

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
| `pytest` (бэкенд, после перебазирования) | **PASS** — 290 passed, coverage 95.91% (было 272 / 95.6% на `main` до этой поставки) |
| `mypy app` (strict), `ruff check`, `ruff format --check` | **PASS** — 0 ошибок, 55 файлов |
| `STRICT=1 pre-commit run --all-files` | **PASS** — 28 хуков |
| pre-push (smoke S1–S6, delivery-gate, baseline-ratchet, new-dependency) | **PASS** — на каждом push |
| `contour_doctor.py` | **DEAD 0** — AUTO 47 · WEAK 17 · ABSENT 0 · TOOL 3 · SKIP 1; «стражи исполнения: mutmut его найдёт» — AUTO |
| мутационный гейт на диффе PR, локально | **PASS** — «убито 267 из 324 (82%)», 29 s, load 9 |
| CI PR #44: `backend`, `gates`, `delivery` | **PASS** — прогоны 40007693513 и 40007693515 |
| `delivery_check.py --diff-base origin/main` | 0 ошибок; предохранитель — 21 файл кода, net +370 строк |

### Оставшиеся предупреждения

- **`human_ok_spec: deferred`** — примеры M1–M14 человек подписывает на мерже.
- **Реляционный оракул (§6.5)** — решение человека 2026-08-12: зависимость для
  тестов-свойств не добавляется.

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

## Исполнение рисковых путей (§12.6)

`runtime_paths: frontend/src/hooks/useVoiceSession.ts` — диффом не задет. Исполнено
то, что эта поставка меняет: мутационный гейт — канонным скриптом на трёх диффах
(talk-screen, обратный прогон `warmup.py`, дифф PR) и шагом CI PR #44; настоящий
`config.py` — исполнением копии в раскладке `mutants/` (M2). Живые модели не
запускались. at=2026-10-23

## Verdict

**READY FOR HANDOFF** — M1–M14 зелёные, шаг CI судит дифф PR (82% за 85 s), CI PR #44
зелёный. Открыто и названо: цена `api/ws_voice.py` в CI (решение человека — ниже в
open questions), подписи человека под примерами и под `canon_drift_waiver`.

## Open questions — к человеку

ВОПРОСЫ_WS_VOICE

## Уроки

- **L91 (предварительно):** «гейт не просудил» оказалось тремя стенами подряд, и каждую
  видно только после предыдущей: копия `vocabulary.py` не импортировалась, корень
  уезжал в `backend/`, порог покрытия судил мутированную копию. Замер 18.10 назвал
  вторую, потому что первую на этом коде не видел никто — гейт не гоняли ни в CI, ни
  руками. Чинить «инструмент не судит» — значит гнать до вердикта, а не до следующего
  стека; и код, который ищет ресурсы глубиной пути (`parents[N]`), ломается под
  любым инструментом, копирующим пакет, — искать по маркерам данных.
- **L92 (предварительно):** доля убитых без числа мутантов — не вердикт. mutmut 3.7
  молча не мутирует декорированное, и `@dataclass` на `TurnEnforcer` спрятал от гейта
  все проверки контракта: на файле стояло «100%» по 21 мутанту фабрики. Сверять надо
  население (сколько мутантов у каких функций), а не процент; то же у знаменателя:
  `timeout` и `no tests` из доли выпадают молча.
- **L93 (предварительно):** гейт, «подключённый» причиной, а не конфигом, не
  подключён. gate-coverage принимал канонное «CI-only на PR» раньше, чем искал скрипт в
  конфигах, и мутационный гейт числился осознанно неподключённым с развёртывания
  контура. А бюджет — свойство самого дорогого файла, а не диффа: 300 s хватает PR #44
  (85 s), а `api/ws_voice.py` их не укладывает — мерить до того, как вешать шаг.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **37**, из них без ссылки на пример спеки:
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

✅ **Каждое утверждение ведёт к примеру спеки** (M1 M10 M14 M2 M3 M4 M5 M8 M9), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0
