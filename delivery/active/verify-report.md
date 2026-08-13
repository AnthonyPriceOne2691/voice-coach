# Verify report: liquid-glass-shell (поставка 1 из 3)

Дата прогонов: 2026-08-13. Verifier: human:anthony (builder — agent:claude-code).

## Оракулы примеров спеки

| id | Оракул | Результат |
|---|---|---|
| U1 | снимок `after-interview.png` | **PASS** — «Voice Interview Coach» стало строкой 13.5 px в шапке; первым по весу идёт «Ready when you are.» и кнопка |
| U2 | тот же снимок + разметка `InterviewPage` | **PASS** — до старта транскрипта на экране нет вовсе (`active ? … : <Invitation/>`) |
| U3 | тот же снимок | **PASS** — три чипа: `~15 min`, `English only`, `6 questions · 3 technical · 3 behavioral` |
| U4 | `SessionHeader` + тест `test_state_message_carries_question_progress` | **PASS** — данные приходят с сервера (`question_index/total/kind`), шапка их показывает вместе с таймером |
| U5 | `.bubble-agent` / `.bubble-user` | **PASS** — разные стороны, разные скруглённые углы, разная заливка |
| U6 | снимок `after-history.png` | **PASS (в объёме поставки 1)** — экран НЕ сломан: legacy-стили сохранены, вкладка открывается и читается. Переезд — поставка 2 |
| U7 | — | перенесено в поставку 3 |
| U8 | все снимки | **PASS** — стекло и градиентный фон видны |
| U9 | CSS `.orb-*` + четыре класса состояния | **PASS частично** — три анимации разведены (дышит / вращается / мерцает), но снимка каждого состояния в живой сессии нет: см. «чего не покрывает» |
| U10 | гейты | **PASS**, ниже |
| U11 | `git diff` | **PASS** — `audioQueue.ts` и `vad.ts` не тронуты вовсе; `useVoiceSession.ts` +31/−2 и только проброс |
| U12 | живая сессия | остаётся на приёмку человеком (`observe_signal`) |

## Машинные гейты

| Гейт | Результат |
|---|---|
| `npm run build` | PASS |
| `npm test` | **20 passed** — прежние тесты фронта зелёные |
| `./scripts/run_checks.sh` | PASS — **162 теста**, coverage 94.51% |
| eslint warning-ратчет | снимок **ужат с 17 до 1** (осталось только давнее `max-lines-per-function` у `useVoiceSession`) |
| complexity | OK — 0 находок |
| jscpd | OK — 0 клон-пар |
| layers (import-linter) | OK; TS-половина пропущена (в worktree нет `dependency-cruiser`) — см. долг ниже |
| `delivery_check` | **0 errors** |

Circuit breakers после сужения: `files=25 net_loc=673` при лимитах 25/800 —
**в пределах**, waiver не потребовался.

## Что сделал разрез (решение человека)

Полный объём давал `31 файл / 1003 LOC`. Человек выбрал **разрез по экранам**, а
не waiver (`escalation.md`). Исполнено так, чтобы промежуточное состояние
**работало**:

- новый визуальный слой добавлен ОТДЕЛЬНЫМИ файлами (`styles/tokens|base|app.css`);
- из `styles.css` удалены только те правила, которые новый слой заменяет
  (оболочка, кнопки, кольцо, mic-meter, баннеры);
- правила History, Useful Words и разбора **оставлены как есть** — они и держат
  эти экраны до их поставки;
- диалог живой сессии назван `.bubble*`, чтобы НЕ конфликтовать с legacy `.turn`,
  который ещё нужен сохранённому `TranscriptView`.

Видимый след разреза: кнопки History получили лёгкое свечение (наследуют новый
`.btn`, а `.btn-ghost` перекрывает только фон). Это временно и уходит в поставке 2.

## Ревью рисковых мест (§12.5)

1. **Каскад между новым и legacy.** `@import` идёт первым, значит legacy-правила
   в `styles.css` **сильнее** одноимённых новых. Именно поэтому коллизии убраны
   не переопределением, а удалением: `.btn`, `.tab`, `.tabs`, `.state-ring`,
   `.mic-meter*`, `.error-banner`, `.notice-banner`, `.modal-card` из legacy
   вырезаны. Оставшиеся имена (`.transcript`, `.turn`, `.history-item`,
   `.word-card`, `.summary-card`) в новом слое не встречаются — проверено.
2. **`useVoiceSession` и голосовой тракт.** Диффом добавлены только `progress`,
   `startedAt` и их установка в `case "state"` и в `start()`. Ни `startVadLoop`,
   ни `startRecorder`, ни `onAudioChunk`, ни `end()` не тронуты — эхо-защита и
   тайминги те же. `audioQueue.ts` и `vad.ts` — нулевой дифф.
3. **`_question_progress` и Mode 2.** Для `ReviewFlow` возвращаются три `None`;
   клиент обязан быть готов к `null`, и это записано в doc 15 и покрыто тестом
   `test_review_session_has_no_question_counter`.
4. **`ws_voice` перевалил за 500 строк** после добавления счётчика. Сборка
   сессий вынесена в `voice/session_factory.py` — граница проведена по смыслу
   («что нужно, чтобы сессия существовала»), а не по числу строк. 489 строк.
5. **Анимации и производительность.** `backdrop-filter` применён к шапке,
   карточкам и ядру орба — не к каждому элементу. Анимации орба — `transform`
   и `opacity`, то есть композиторные; на аудио-тракт они не влияют вовсе,
   потому что живут в CSS.
6. **`prefers-reduced-motion`** уважается: все анимации гасятся до 0.001 ms.

7. **«Безопасность» — риска нет, и вот почему.** Маячок подняло слово
   `permission` в неизменённом `useVoiceSession` (запрос доступа к микрофону) и
   `aria-label` в новой разметке. Поставка не трогает ни выдачу прав, ни
   аутентификацию (её в проекте нет вовсе — инструмент локальный, без сети
   наружу), ни хранение секретов. Единственная новая сетевая точка —
   `question_index/total/kind` в уже существующем WS-сообщении, то есть три
   числа о ходе интервью.

## Исполнение рисковых путей (§12.6)

**Путь:** `frontend/src/styles/`, `delivery/evals/browser/` — экран отказывает
пикселями, а не кодом ошибки; `npm test` зелёный при полностью сломанной вёрстке.

**Прогнал** настоящий Chromium по CDP (тот же способ, что у браузерного стенда)
против живого стека — vite 5273 + backend 8000 с реальной базой. **Увидел:**
снимки трёх вкладок, приложены к приёмке. at=2026-08-13.

Отдельно: снимки «до» сняты **до первой правки** — иначе сравнивать было бы не с
чем (L17).

## Чего эта проверка НЕ покрывает

- **Снимков четырёх состояний орба нет.** Анимации разведены в CSS и видны в
  коде, но живого снимка `listening/processing/speaking` не сделано: для этого
  нужна настоящая сессия с микрофоном. Уходит в `observe_signal` (U12).
- **Живая сессия голосом не прогонялась** в этой ветке — только вёрстка. Это
  прямой остаток U12 и главный пункт наблюдения.
- **TS-половина гейта слоёв не проверена** в worktree: `dependency-cruiser` не
  установлен рядом. Гейт честно сказал «половина НЕ проверена» — CI её прогонит.
- **Вкус.** Направление утверждено макетом до кода, итог — снимками; но
  «нравится ли жить в этом каждый день» покажет только использование.

## Verdict

**READY FOR HANDOFF** — девять машинных примеров подтверждены, два перенесены в
следующие поставки, один (живая сессия) уходит в наблюдение. Гейты зелёные,
breaker'ы в пределах после разреза.

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 26 code (+5 process docs) / +974/-301 (net +673) |
| commits | 1 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — delivery/active/spec.md (новый оракул), scripts/lint/eslint_warnings_baseline.txt |
| implement_retries | MANUAL — fills from session log |
| verify_fails_before_green | MANUAL — count red verify runs (CI run list) |
| est_token_or_cost | MANUAL / n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **5**, из них без ссылки на пример спеки:
**3**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
-	assert payload["question_index"] == 1
-	assert payload["question_total"] == 6
-	assert payload["question_kind"] == "technical"  # открывает всегда технический
Q1	assert states[0]["payload"]["question_index"] is None
Q1	assert states[0]["payload"]["question_kind"] is None
```

Привязаны к примерам: **Q1**. Остальные 3 — нет.

Читать нужно **только строки с `-` в первой колонке**: их ожидание
ничем не подписано. Подпись: `asserts_reviewed_by: human:… at=…`.

asserts_without_example: 3

asserts_reviewed_by: human:anthony at=2026-08-13 — прочитаны все 3 строки без
примера: первое сообщение `state` в сессии интервью несёт «вопрос 1 из 6»,
класс первого вопроса всегда technical (открывает `project_overview` с
`first: true`). Соседний тест проверяет обратное — у Mode 2 все три поля null.
