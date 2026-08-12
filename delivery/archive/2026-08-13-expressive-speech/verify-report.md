# Verify report: expressive-speech

Дата прогонов: 2026-08-13. Verifier: human:anthony (builder — agent:claude-code).

## Оракулы примеров спеки

| id | Оракул | Результат |
|---|---|---|
| E1 | `test_tts_piper.py::test_prosody_reaches_synthesis_config` (+ красная сторона: `test_unset_prosody_falls_back_to_the_voice_passport`) | PASS |
| E2 | `test_prosody.py::test_silence_is_prepended_and_lasts_exactly_the_pause`, `test_ws_prosody.py::test_breath_between_sentences_but_not_before_the_first` | PASS |
| E3 | `test_prosody.py::test_format_survives_and_the_result_is_readable`, `test_the_pause_goes_before_the_sound_not_after` | PASS |
| E4 | `test_ws_prosody.py::test_intro_has_no_leading_pause_and_turn_end_has_no_trailing_one` | PASS |
| E5 | тот же тест + `test_pause_counter_resets_between_turns` | PASS |
| E6 | живой перезамер, см. ниже | PASS |
| E7 | человек, слушание образцов `LIVE_before.wav` / `LIVE_after.wav` | **PASS** (by=human:anthony, at=2026-08-13: «лучше») |

## Машинные гейты

| Гейт | Результат |
|---|---|
| `./scripts/run_checks.sh` | **PASS** — module size, ruff, ruff format, mypy strict, pytest |
| Backend pytest | **160 passed**, coverage **94.45%** (гейт 85; было 150 / 94.46%) |
| pre-commit (полный набор) | PASS |
| `jscpd` до и после (**L30**) | 0 клон-пар в обоих случаях |
| `okf_sync_gate` **после коммита** (**L35**) | drift на `model-split.md` закрыт подписанным waiver'ом |
| `delivery_check.py --diff-base origin/main` | 0 errors |
| Frontend `npm test` | фронт не тронут — замер, а не утверждение |

Circuit breakers: `files=11 net_loc=390 (+396/-6)` при лимитах 25/800 — с запасом.

## Ревью рисковых мест (§12.5)

1. **Счётчик `_spoken_chunks` и его сброс.** Пауза ставится по нему, а сброс
   происходит на `final=True` в `_send_audio`. Сломай сброс — и пауза уедет в
   НАЧАЛО следующей реплики, то есть станет задержкой перед первым словом
   Генри на каждом ходе после первого. Сторожит
   `test_pause_counter_resets_between_turns`: он проверяет ДВА хода подряд, а
   не один.

2. **`lead_in` перечитывает и пересобирает WAV.** Работа на каждый чанк кроме
   первого: чтение заголовка, конкатенация байтов, запись. Для реплики в
   несколько секунд это сотни килобайт `memcpy` — на фоне синтеза (46 ms) шум,
   и в путь до ПЕРВОГО звука не попадает вовсе, потому что первый чанк не
   дополняется. Замер E6 это подтверждает.

3. **Просодия привязана к конкретному голосу.** `noise_scale=0.667` выбран на
   слух для `en_US-hfc_male-medium`, чей паспорт вдвое ровнее. Для `ryan-high`
   (паспорт уже 0.667) значение просто совпадёт с паспортным, для другого
   голоса может звучать иначе. Записано комментарием в `config.py` рядом со
   значением, а не в отдельном документе, который не прочтут.

4. **`FakeTts` стал отдавать настоящий WAV.** Изменение затрагивает ВСЕ
   ws-тесты, а не только новые: раньше двойник возвращал `b"WAV:"+text`, и
   первый же код, читающий аудио, уронил шесть тестов на
   `file does not start with RIFF id`. Это не «тесты сломались» — это двойник
   перестал быть подстановочным ровно в тот момент, когда его впервые
   попросили быть аудио.

5. **«Деньги» и «производительность» — риска нет.** Маячок поднимают слово
   «цена» в комментариях и `wave`/`io` в `prosody.py`. Денег в проекте нет
   вовсе; производительность разобрана пунктом 2 и замерена E6.

## Исполнение рисковых путей (§12.6)

**Путь:** `backend/app/voice/tts_piper.py` — слышимость платформа подтверждает
звуком, а не кодом ошибки: тест увидит нужное число нулевых сэмплов и останется
зелёным при любом качестве звучания. Исполнен живым Piper'ом двумя способами,
at=2026-08-13.

1. **Прогнал** полный ход настоящим стеком (whisper → qwen → Piper с новой
   просодией), три раза на каждую ступень темпа. **Увидел:** синтез первого
   предложения 46 ms при 1.15 и 55 ms при 1.60; до первого звука 1302 ms в
   худшем прогоне при гейте 3000. Таблица ниже.
2. **Прогнал** живую реплику Генри целиком (модель формулировала сама) и собрал
   её дважды — со старыми и новыми параметрами. **Увидел:** WAV читается, длина
   выросла с 13.39 до 14.06 s ровно на паузы между предложениями; файлы
   `LIVE_before.wav` и `LIVE_after.wav` предъявлены человеку для E7.

## Исполнение E6 — живой перезамер latency

Чем исполнял: `WhisperCppStt` (whisper-cli, `ggml-small.en`) → `OllamaClient`
(`qwen2.5:14b-instruct`) → `PiperTts` **с новой просодией**. Три прогона на
ступень после прогрева, замер до первого аудио-чанка. at=2026-08-13.

| `length_scale` | STT | LLM до 1-го предложения | TTS 1-го предложения | Медиана | Худший |
|---|---|---|---|---|---|
| 1.15 (обычный) | ~700 ms | ~484 ms | **46 ms** | 1247 ms | **1302 ms** |
| 1.60 (самый медленный) | ~560 ms | ~497 ms | **55 ms** | 1111 ms | 1123 ms |

**Вердикт: PASS.** Гейт 3000 ms, худший прогон 1302 ms — 43% бюджета. Против
замера прошлой поставки (45 ms на первое предложение при 1.15) просодия стоила
**+1 ms**, ровно как предсказал спайк. Пауза в путь до первого звука не входит
по построению: первый чанк не дополняется.

## Что осталось человеку (E7)

Слышимость машинным оракулом не берётся. Собраны два образца **одной и той же**
живой реплики Генри (модель настоящая, текст один и тот же):

- `LIVE_before.wav` — 13.39 s, как звучало до поставки;
- `LIVE_after.wav` — 14.06 s, с интонацией, ритмом и дыханием.

Плюс пять образцов спайка (`A_baseline_now` … `E_ryan_high_full`), по которым
вариант и выбирался.

**Вердикт человека 2026-08-13: лучше, паузa темп не рвёт, дрожания нет.** E7
закрыт до мержа, а не отложен в наблюдение.

## Чего эта проверка НЕ покрывает

- **Пауза одинаковая для всех переходов.** Живая речь варьирует её по знаку
  препинания; здесь 350 ms всегда. Станет ли это заметно — покажет
  использование.
- **Реплика стала длиннее** на 0.35 s за каждый переход между предложениями
  (13.39 → 14.06 s на двух предложениях). Это плата за разборчивость.
- **Другие голоса не переслушивались** после смены значений: параметры выбраны
  под голос Генри.

## CI

Локальные гейты зелёные. Прогон CI на ветке — ссылкой в PR (**L1:** `CI`,
`quality` и `main-guard` — разные workflow).

## Verdict

**READY FOR HANDOFF** — шесть машинных примеров подтверждены оракулами, живой
перезамер latency пройден с запасом более чем вдвое, седьмой (слышимость)
подтверждён человеком на образцах до мержа.

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 11 code (+6 process docs) / +396/-6 (net +390) |
| commits | 1 |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 0 (handoff not declared yet) |
| harness_hardened | yes — backend/tests/test_prosody.py (новый оракул), backend/tests/test_ws_prosody.py (новый оракул), delivery/active/spec.md (новый оракул) |
| implement_retries | MANUAL — fills from session log |
| verify_fails_before_green | MANUAL — count red verify runs (CI run list) |
| est_token_or_cost | MANUAL / n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **27**, из них без ссылки на пример спеки:
**7**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
E2	assert wav_duration_s(original) == pytest.approx(1.0)
E2	assert wav_duration_s(padded) == pytest.approx(1.35, abs=0.001)
E3	assert after.getframerate() == before.getframerate()
E3	assert after.getsampwidth() == before.getsampwidth()
E3	assert after.getnchannels() == before.getnchannels()
E3	assert head == b"\x00" * len(head)
-	assert frames[:silence_len] == b"\x00" * silence_len
-	assert frames[silence_len:] == b"\x10\x10" * (RATE // 10)  # звук цел и в конце
-	assert lead_in(original, seconds) is original
E1	assert config.noise_scale == 0.667
E1	assert config.noise_w_scale == 1.0
E1	assert config.length_scale == 1.15
E1	assert voice.configs[0].noise_scale is None
E1	assert voice.configs[0].noise_w_scale is None
E2	assert isinstance(tts, FakeTts)
E2	assert spoken == ["Got it.", "Why separate queues?"]  # два предложения хода
E2	assert len(sent) == 2
E5	assert sent[0] == pytest.approx(raw[0], abs=0.001)  # E5: первому дыхание не нужно
E2	assert sent[1] == pytest.approx(raw[1] + PAUSE_S, abs=0.001)  # E2: второму — нужно
E4	assert isinstance(tts, FakeTts)
E4	assert started["type"] == "session_started"
E4	assert intro_chunks[0] == pytest.approx(fake_tts_duration_s(tts.synthesized[0]), abs=0.001)
E4	assert len(finals) == 1
-	assert isinstance(tts, FakeTts)
-	assert len(chunks) == 2
-	assert chunks[0] == pytest.approx(raw[0], abs=0.001)
-	assert chunks[1] == pytest.approx(raw[1] + PAUSE_S, abs=0.001)
```

Привязаны к примерам: **E1 E2 E3 E4 E5**. Остальные 7 — нет.

Читать нужно **только строки с `-` в первой колонке**: их ожидание
ничем не подписано. Подпись: `asserts_reviewed_by: human:… at=…`.

asserts_without_example: 7

asserts_reviewed_by: human:anthony at=2026-08-13 — прочитаны все 7 строк без
примера: три про устройство тишины (нулевые сэмплы ровно на длину паузы, звук
цел байт в байт, пауза ≤ 0 возвращает тот же объект без пересборки) и четыре
про чанки хода (ровно два, первый без паузы, второй с ней — проверено в двух
ходах подряд, что и сторожит сброс счётчика). Ожидания совпадают с решениями
D3 и D5 (`decisions.md`), принятыми до кода.
