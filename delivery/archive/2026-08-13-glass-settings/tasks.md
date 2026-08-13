# Tasks: glass-settings

- [ ] **T1. API и типы.** `UserSettings` в `types/api.ts`; `api.getSettings` и
      `api.patchSettings`; правило `/settings` в `server.proxy` — вместе, чтобы
      сторож `api.test.ts` был зелёным (L44).
- [ ] **T2. Экран.** `pages/SettingsPage.tsx`: темп ползунком с числом и словом,
      длительность сегментами, порог тишины, live-транскрипт; сохранение на
      отпускании; показ 422 (S1–S4).
- [ ] **T3. Вкладка.** Четвёртый таб в `App.tsx`.
- [ ] **T4. Стили.** Секция настроек в `styles/app.css` (`.settings`,
      `.setting*`, `.segmented`, `input[type=range]`).
- [ ] **T5. Тесты.** `SettingsPage.test.tsx`: значение с сервера, один PATCH на
      отпускание, показ 422.
- [ ] **T6. Канон.** doc 17: экран Settings построен, состав настроек.
- [ ] **T7. Гейты и снимок.** Полный набор + снимок вкладки (S1, S7).
- [ ] **T8. Handoff.** verify-report, decisions, метрики, merge_guard, архив.
