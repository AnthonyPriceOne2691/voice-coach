# Tasks: выбор микрофонного устройства

Порядок — снизу вверх по тракту: сначала хранение, потом доступ к железу, потом
экран, в конце канон. Каждый slice заканчивается зелёными тестами своей части.

- [x] **T1. kv-ключ `mic_device_id`** — `settings_repo.DEFAULTS`, валидация
      `str | null` в `routes_settings._validate` (иначе 422, длина ≤ 256).
      Тест: round-trip + 422 на числе/списке/true (M7).
- [x] **T2. `lib/mic.ts`** — `listMicrophones`, `labelsHidden`, `requestMicAccess`,
      `openMicrophone` (`exact` + фолбэк только на «устройства нет»).
      Тесты: M4 (константа `exact`), M5 (`OverconstrainedError` → фолбэк с
      флагом), M6 (`null` → `{ audio: true }`), `NotAllowedError` летит дальше.
- [x] **T3. `useVoiceSession.start()`** — читает настройку, открывает вход через
      `openMicrophone`, показывает сообщение при подмене входа.
      Тест: старт с сохранённым id и старт после его пропажи.
- [x] **T4. `hooks/useMicLevel.ts`** — уровень выбранного входа на время проверки;
      гашение треков при выключении, смене устройства, размонтировании (M10, M11).
- [x] **T5. `components/MicrophoneSetting.tsx`** — список, приглашение выдать
      доступ, `Test`, полоска. Тесты: M1, M2, M3, M10, M11 (`cleanup()` в
      `afterEach` — L50).
- [x] **T6. `SettingsPage.tsx` + `types/api.ts` + `styles/app.css`** — строка на
      экране, поле в типе, правила стиля (добавить, не переопределять — L45/L46).
- [x] **T7. Канон** — doc 15 (пятый ключ, `exact`, видимый фолбэк), doc 17
      (строка ✅), `knowledge/engineering/echo-protection.md` (правило про явный
      выбор входа; `implementation:` пополняется `lib/mic.ts`).
- [x] **T8. Verify** — `scripts/run_checks.sh`, `npm run build && npm test`,
      гейты контура, `eval-smoke.md`, живой прогон M9 в `verify-report.md`.
