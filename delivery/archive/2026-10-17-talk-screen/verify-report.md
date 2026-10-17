# Verify report: talk-screen (D3a.1, 3 из 3)

Дата прогонов: 2026-10-17. Builder: agent:claude-code (сессия voice-interview-coach).
Verifier: human:anthony.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| T1 | `TalkPage.test.tsx` (3), `useVoiceSession.test.tsx` — вид сессии выбирает стартовое сообщение (3) | **PASS** — до правки красные: на виде talk хук слал `start_review`, страницы не было |
| T10 | два живых замера по «запускай» human:anthony (`eval-smoke.md`) | **PASS по пути кода** — тёплые ходы 1.6–2.4 s, модель первого хода после правки прогрева 1.8 s; первый ход целиком под давлением памяти — выброс распознавания 29 s, открыт в наблюдении |
| — | прогрев сессии кладёт в кэш её префикс (`test_session_warmup_caches_its_own_prompt_prefix`, разговор и интервью) | **PASS** — до правки красный |

## Находка верификации: первый ход платил полный prefill

Замер 1 (прогрев как был): первый ход — **8,763 ms** до первого звука при гейте 3,000;
модель и синтез до первого предложения — 7,271 ms против ~830 на тёплых ходах. Прогрев
слал «hi» на один токен: веса грузились, а системный промпт с профилем (~1,700
токенов) в кэш не попадал. Doc 20 предсказывал эту цену с июля и помечал «не
замерено». Тот же путь у интервью. Починено: сессия, открытая репликой кода,
прогревает свои сообщения, пока звучит приветствие. Замер 2: модель первого хода —
**1,811 ms**.

## Мутации (сторож обязан краснеть)

| Мутация | Ожидание | Результат |
|---|---|---|
| MS1: хук на виде talk шлёт `start_interview` | T1 хука красный | **красный** |
| MS2: страница не передаёт подпись шапки | «Talk with Henry» красный | **красный** |
| MS3: прогрев снова «hi» | тест префикса красный | **красный** — оба случая, разговор и интервью |

## Машинные гейты

| Гейт | Результат |
|---|---|
| `UV_FROZEN=1 ./scripts/run_checks.sh` | **PASS** — 272 passed, coverage 95.6%, mypy strict, ruff |
| `npx vitest run`, `tsc`, `eslint` | **PASS** — 57 тестов (было 51); warning-ратчет прежний (1 — старый `useVoiceSession`) |
| `cd frontend && npm run build` | **PASS** — артефакт-оракул |
| `check_diff_coverage.sh` | **PASS**, exit 0 |
| `pre-commit run --all-files` | **PASS** — jscpd 0 клон-пар обеих половин |
| `okf_sync_gate.py` | **PASS** |
| `delivery_check.py --diff-base origin/main` | 0 ошибок; предохранитель — 16 файлов, ~290 строк |

### Оставшиеся предупреждения

- **Реляционный оракул (§6.5)** — решение человека 2026-08-12, зависимость для
  тестов-свойств не добавляется.

## Изменение поверхности модели (§14.1)

- `backend/app/voice/warmup.py`, `backend/app/api/ws_voice.py` — прогрев шлёт модели
  сообщения сессии (системный промпт и приветствие) с одним токеном генерации. Что
  модель видит на ходах — не меняется; меняется, что лежит в кэше к первому ходу.
  at=2026-10-17

## Ревью рисковых мест (§12.5)

1. **деньги** (`цена`) — слово из прозы доков и отчёта: «цена первого хода» —
   латентность, а не платёж. Денежного кода в диффе нет; риска нет.
2. **транзакция БД** (`commit`) — слова сообщений коммитов в отчёте; база не
   тронута — разговор пишется прежним `TalkRepository`. Риска нет.
3. **цепочка гейтов** (`merge_guard`) — упоминание в задачах; скрипты гейтов не
   тронуты.
4. **новый модуль** (`LiveSession`, `TalkPage`, `useLiveTranscriptSetting`) —
   `LiveSession` и `useLiveTranscriptSetting` вынесены из `InterviewPage` без
   изменения поведения: держат прежние тесты страницы интервью. `TalkPage` —
   страница без собственного состояния, кроме хука сессии. Что реально может
   сломаться — прогрев: `warm_up` теперь шлёт модели сообщения сессии; если сессия
   оборвётся раньше, задачу снимает тот же `_cancel_warmup` до записи статуса.

## Исполнение рисковых путей (§12.6)

`runtime_paths: frontend/src/hooks/useVoiceSession.ts` — хук тронут выбором
стартового сообщения; исполнен тестом хука на подставных WebSocket и анализаторе и
живым замером T10 на настоящем стеке (без браузера: whisper → qwen2.5 → Piper через
`TurnRunner`). at=2026-10-17

## Verdict

**READY FOR HANDOFF** — T1 зелёный, T10 зелёный по пути кода после найденной и
закрытой цены первого хода; выброс распознавания под давлением памяти записан в
наблюдение. Машинные гейты зелёные по правилам delivery@2.01 · cqg@2.57.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **11**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
T10	assert last_call[0]["role"] == "system"
T10	assert warmup[0]["role"] == "system"
T10	assert str(warmup[0]["content"]).startswith(system)
T10	assert warmup[-1]["role"] == "assistant"  # приветствие уже в истории
T1	expect(sent).toEqual(["hello", first]);
T1	expect(start).toHaveBeenCalledWith({ kind: "talk" });
T1	expect(screen.getByText("Talk with Henry")).toBeTruthy();
T1	expect(screen.queryByText("Mock interview with Henry")).toBeNull();
T1	expect(await screen.findByText(HENRY)).toBeTruthy();
T1	await waitFor(() => expect(screen.queryByText(HENRY)).toBeNull());
T1	expect(await screen.findByText(HENRY)).toBeTruthy();
```

✅ **Каждое утверждение ведёт к примеру спеки** (T1 T10), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 16 code (+10 process docs) / +359/-71 (net +288) |
| commits | 9 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 commit(s) after first phase: handoff |
| harness_hardened | yes — frontend/src/pages/TalkPage.test.tsx (новый оракул) |
| implement_retries | 1 — живой замер T10 нашёл цену первого хода (8,763 ms); прогрев починен в этой поставке и перемерен |
| verify_fails_before_green | 1 — первый замер T10 красный (первый ход); после правки — зелёный по пути кода |
| est_token_or_cost | n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
