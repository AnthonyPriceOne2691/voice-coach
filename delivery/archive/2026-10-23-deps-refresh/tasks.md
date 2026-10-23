# Tasks: аудит уязвимых зависимостей — зелёный и в CI (deps-refresh)

- [x] W1. Сторож V2/V3 `test_manual_gates_run_in_ci.py` — до шага CI красный
- [x] W2. Шаг «Vulnerable dependencies» в `quality.yml` дословно из канона;
      запись `quality.yml` в `adapted.json`
- [x] W3. Frontend: vitest 5.0.5, vite 6.4.5, `npm audit fix`; сьют (57), сборка,
      eslint, prettier, tsc; dev-сервер на 5273 с прокси (V4, V5, V6)
- [x] W4. Backend: `uv.lock` — anyio 4.14.2, urllib3 2.8.0, certifi 2026.10.19,
      virtualenv 21.14.13; `run_checks.sh`, WS-тесты пятью прогонами (V7)
- [x] W5. Снимок аудита тает до нулей; гейт зелёный (V1); мутация V8
- [x] W6. Doc 07 (Node 22 LTS, vite `^6.4`); STACK-ACCEPTANCE — строка аудита ЗАКРЫТО
- [x] W7. `eval-smoke.md`, `verify-report.md`, метрики; PR, CI, лог шага аудита
