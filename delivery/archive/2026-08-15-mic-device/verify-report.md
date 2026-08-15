# Verify report: mic-device

Дата прогонов: 2026-08-15. Builder: agent:claude-code. Verifier: human:anthony
(живой прогон на настоящем железе — за человеком, см. «Чего проверка НЕ покрывает»).

## Оракулы примеров спеки

| id | Оракул | Результат |
|---|---|---|
| M1 | `MicrophoneSetting.test.tsx::показывает входы по именам` | **PASS** — выходы отфильтрованы, сохранённый отмечен |
| M2 | `MicrophoneSetting.test.tsx::без разрешения предлагает его выдать` | **PASS** |
| M3 | `SettingsPage.test.tsx::выбор микрофона сохраняется одним PATCH` | **PASS** — тело ровно `{"mic_device_id":"yeti"}`, запрос один |
| M4 | `mic.test.ts` + `useVoiceSession.test.tsx` | **PASS** — constraint `{ exact }` и на уровне модуля, и на старте сессии |
| M5 | `mic.test.ts::пропажа устройства` + `useVoiceSession.test.tsx` | **PASS** — фолбэк с флагом, сессия жива, сообщение видно |
| M6 | `mic.test.ts::без выбора` | **PASS** — `{ audio: true }`, поведение до поставки |
| M7 | `test_rest_api.py::test_mic_device_setting_is_exposed_and_validated` | **PASS** — 422 на числе, `true`, списке, объекте и строке 257 символов; `null` законен |
| M8 | гейты | **PASS**, ниже |
| M9 | живой прогон | **ЧАСТИЧНО** — настоящий Chromium против живого стека пройден (ниже); смена на **физическом** железе за человеком |
| M10 | `MicrophoneSetting.test.tsx::Test открывает выбранный вход` | **PASS** — `exact`, полоска «hearing you», `Stop` гасит треки |
| M11 | `MicrophoneSetting.test.tsx::смена входа во время проверки` | **PASS** — старый поток погашен, новый открыт |
| M12 | `mic.test.ts::отказ в доступе НЕ подменяется фолбэком` | **PASS** — `NotAllowedError` летит наружу, второго вызова нет |

## Машинные гейты

| Гейт | Результат |
|---|---|
| `pre-commit run --all-files` (STRICT=1) | **PASS** — 28 хуков, ни одного пропуска по «нет файлов» в коде |
| `./scripts/run_checks.sh` | **PASS** — 163 теста, coverage 94.55% при гейте 85 |
| `npm run build` | **PASS** |
| `npm test` | **PASS** — **40** (было 23: +8 `mic.ts`, +6 компонентных, +2 на хук, +1 на страницу) |
| eslint | 0 errors, 1 warning при снимке 1 — ратчет не сдвинут |
| complexity / jscpd / layers | **PASS**, обе половины (python + ts) |
| `okf_sync_gate.py --base main` | **PASS** — 5 mapped concepts, 0 warnings |
| `okf_validate.py knowledge/` | **PASS** — 0 errors |
| `delivery_check.py --diff-base main` | 0 errors (после правки журналов) |

## Ревью рисковых мест (§12.5)

1. **Новых зависимостей нет** — ни npm, ни python; `package-lock.json` не тронут.
   Поставка обошлась тем, что уже стоит (L48 к ней не применяется).
2. **Тракт микрофона тронут в одном месте.** `start()` в
   `frontend/src/hooks/useVoiceSession.ts` — единственная точка открытия входа,
   и через неё идут оба флоу (interview и review). Прежняя строка
   `getUserMedia({ audio: true })` заменена на `openMicrophone`, всё остальное в
   хуке не изменено: `startRecorder`, `startVadLoop`, флаг `playing` и колбэк
   `AudioQueue` — те же (L39). Единственная другая правка там — `stopStream(r.stream)`
   вместо ручного обхода треков в `end()`, чтобы гашение жило в одном месте.
3. **Настройка не является условием старта.** `api.getSettings()` в `start()`
   обёрнут `catch → null`: недоступный бэкенд не мешает открыть микрофон, о нём
   скажет ближайший же WebSocket. Иначе поставка добавила бы новую причину, по
   которой сессия не начинается.
4. **`{ exact }` вместо `{ ideal }` — сознательная смена поведения при пропаже
   устройства.** До поставки такой ситуации не существовало вовсе (вход всегда
   был системный); теперь она есть, и закрыта видимым сообщением, а не тишиной.
5. **Разрешение запрашивается вне сессии.** `requestMicAccess` открывает поток
   ради имён и гасит его тем же вызовом; проверка уровня держит поток только
   между `Test` и `Stop`, гашение — в cleanup эффекта, то есть и при уходе с
   экрана.
6. **Производительность — риска нет.** Класс подняло `window.setInterval` в
   `useMicLevel`: таймер тикает раз в 50 ms и живёт только между `Test` и `Stop`
   (гасится в cleanup эффекта), шаг тот же, что у `startVadLoop` в сессии. В
   голосовом цикле нового таймера не появилось; `start()` получил один REST-вызов
   `api.getSettings()` — он идёт ДО `new AudioContext()` и WebSocket, то есть вне
   замеренного latency-гейта «до первого звука».
7. **База.** Пятый ключ (`mic_device_id`) в существующей kv-таблице;
   `SettingsRepository.update` и `get_all` не изменены по коду — транзакция как
   была одной, так и осталась. Правка там только в комментариях «четыре ключа»
   → «пять ключей» (включая пометки `cpu-ok`): иначе они врали бы в ту же
   сторону, что L11. Валидация вынесена в `_validate_mic` рядом с
   `_validate_pace`, общий `_validate` их только вызывает.

## Исполнение рисковых путей (§12.6)

**Путь:** `frontend/src/hooks/useVoiceSession.ts` — один. `SettingsPage.tsx`
объявлялся вторым и **снят по ходу поставки**: сценарий стенда `run.sh mic`
покрыл экран в настоящем Chromium целиком, то есть его отказ стал виден машине.
Ровно тот же шаг, что снятие `vite.config.ts` в прошлой поставке (L47) — список
пересматривается после появления оракула, а не носится по памяти.

**Прогнал настоящий Chromium** против живого стека (vite 5273 + backend 8000 на
коде ветки) — новый сценарий стенда `delivery/evals/browser/run.sh mic`.
Результат (три прогона подряд, стабильно **PASS**):

- сохранённый вход, которого нет, показан строкой «Saved microphone — not connected»;
- нажатие `Test` на нём даёт **видимое** сообщение о пропаже — то есть ветка
  `OverconstrainedError` сработала в настоящем браузере. **Это главное, чего
  тесты дать не могли:** весь фолбэк держится на имени ошибки, и подтвердить его
  можно только живым Chromium;
- `enumerateDevices` вернул три входа **с именами** (`Fake Default Audio Input`,
  `Fake Audio Input 1/2`) — разрешение и имена работают;
- выбор доехал до базы: `GET /settings` вернул выбранный `deviceId`;
- полоска уровня показала `-18 dBFS` и статус «hearing you» на выбранном входе.

Снимок экрана: `delivery/evals/browser/out/mic-settings.png`. at=2026-08-15.

**Найдено при написании стенда** (в продукте дефекта нет, дефект был в оракуле):
первый прогон дал 20 замеров «silent» подряд при работающей полоске. Причина —
совпадение периодов: фальшивый вход Chromium гудит ровно раз в секунду, а опрос
шёл с шагом 0.5 s и попадал в одну фазу. Отдельный замер показал живые значения
−10…−121 dBFS. Шаг сделан дробным (0.3 s), причина записана комментарием в
сценарии, чтобы «упростить обратно» было нельзя.

## Чего эта проверка НЕ покрывает

- **Физическое железо.** Что звук действительно идёт с выбранного микрофона
  (USB-гарнитура против встроенного), подтвердит только ухо человека. Это
  `observe_signal`.
- **Реляционного оракула (§6.5) нет.** Решение прошлых поставок — не заводить
  `hypothesis`/`fast-check` ради формы — не пересматривалось. Ближайшее к
  свойству здесь: `openMicrophone` проверен на **отношении** «что попросили ↔ что
  открылось» в четырёх ветках (есть устройство / пропало / нет выбора / нет
  доступа), но формы, которую ищет гейт, у него нет. Долг записан, а не спрятан.
- **Смена входа посреди сессии** не реализована сознательно (D5) и не проверялась.
- **Другие браузеры.** Стенд гоняет Chromium; Safari отдаёт устройства иначе
  (нулями до гранта) — код это учитывает (`labelsHidden` считает пустой список
  скрытым), но живьём не проверено.

## Verdict

**READY FOR HANDOFF** — одиннадцать примеров из двенадцати закрыты машинными
оракулами, двенадцатый (M9) наполовину: настоящий браузер пройден, физическое
железо остаётся человеку и вынесено в наблюдение.
## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **39**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
M3	assert client.get("/settings").json()["mic_device_id"] is None
M3	assert saved.status_code == 200
M3	assert client.get("/settings").json()["mic_device_id"] == "abc123"
M3	assert client.patch("/settings", json={"mic_device_id": None}).status_code == 200
M3	assert client.get("/settings").json()["mic_device_id"] is None
M3	assert client.patch("/settings", json={"mic_device_id": bad}).status_code == 422
M3	assert client.get("/settings").json()["mic_device_id"] == "abc123"  # не тронуто
M1	expect(select.value).toBe("yeti");
M1	expect(screen.getByRole("option", { name: "Blue Yeti" })).toBeTruthy();
M1	expect(screen.queryByRole("option", { name: "MacBook Air Speakers" })).toBeNull();
M2	await waitFor(() => expect(getUserMedia).toHaveBeenCalledWith({ audio: true }));
M3	expect(onPick).toHaveBeenCalledWith("yeti");
M3	expect(onPick).toHaveBeenLastCalledWith(null);
M5	expect(await screen.findByRole("option", { name: /not connected/ })).toBeTruthy();
M10	expect(getUserMedia).toHaveBeenCalledWith({ audio: { deviceId: { exact: "yeti" } } }),
M10	expect(await screen.findByText("hearing you")).toBeTruthy();
M10	await waitFor(() => expect(opened.track.stop).toHaveBeenCalled());
M11	await waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(1));
M11	await waitFor(() => expect(first.track.stop).toHaveBeenCalled());
M11	expect(getUserMedia).toHaveBeenLastCalledWith({ audio: { deviceId: { exact: "built-in" } } });
M4	expect(getUserMedia).toHaveBeenCalledWith({ audio: { deviceId: { exact: "saved-mic" } } });
M4	expect(result.current.error).toBeNull();
M5	await waitFor(() => expect(result.current.error).toMatch(/not available/));
M5	expect(result.current.active).toBe(true);
M1	expect(await listMicrophones()).toEqual([
M2	expect(labelsHidden([{ deviceId: "in-1", label: "" }])).toBe(true);
M2	expect(labelsHidden([])).toBe(true);
M2	expect(labelsHidden([{ deviceId: "in-1", label: "Yeti" }])).toBe(false);
M2	expect(stream.getTracks()[0].stop).toHaveBeenCalled();
M6	expect(getUserMedia).toHaveBeenCalledWith({ audio: true });
M6	expect(opened.fellBackToDefault).toBe(false);
M4	expect(getUserMedia).toHaveBeenCalledWith({ audio: { deviceId: { exact: "abc123" } } });
M5	expect(opened.fellBackToDefault).toBe(true);
M5	expect(getUserMedia).toHaveBeenLastCalledWith({ audio: true });
M5	expect((await openMicrophone("gone")).fellBackToDefault).toBe(true);
M12	await expect(openMicrophone("abc123")).rejects.toThrow("NotAllowedError");
M12	expect(getUserMedia).toHaveBeenCalledTimes(1);
M3	await waitFor(() => expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(1));
M3	expect(calls.at(-1)?.body).toBe(JSON.stringify({ mic_device_id: "yeti" }));
```

✅ **Каждое утверждение ведёт к примеру спеки** (M1 M10 M11 M12 M2 M3 M4 M5 M6), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам M1–M12; дайджест выше даёт `asserts_without_example: 0`)

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 16 code (+11 process docs) / +790/-9 (net +781) |
| commits | 2 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — delivery/active/spec.md (новый оракул), delivery/evals/browser/mic.py, delivery/evals/browser/run.sh |
| implement_retries | MANUAL — fills from session log |
| verify_fails_before_green | MANUAL — count red verify runs (CI run list) |
| est_token_or_cost | MANUAL / n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
