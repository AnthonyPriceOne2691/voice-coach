# Eval smoke — deps-refresh

Run during implement/verify, 2026-10-23. Живых моделей не запускалось: ни ollama, ни
whisper, ни Piper; бэкенд-сервер не поднимался (контейнер строит `PiperTts`).

## V1 — гейт аудита на дереве поставки

Вызов тот же, что в CI: `env LINT_PY_SRC=backend/app LINT_COV_PKG=app LINT_FE_DIR=frontend LINT_BE_DIR=backend bash scripts/lint/check_deps_audit.sh`.

| Где | Вывод | exit |
|---|---|---|
| `main` 73342b3, до | `✗ py_total: 20 (было 0)`, `✗ js_critical: 2 (было 1)`, `✗ js_high: 6 (было 3)`, `✗ js_total: 24 (было 14)`, `✗ критические/высокие уязвимости: critical=2 high=6` | 1 |
| ветка, после | «python-половина мерена по uv.lock», ни одной строки ✗ | 0 |

- [x] `--generate` после обновлений: `py_total=0 js_critical=0 js_high=0 js_total=0` — снимок
      растоплен (было 0/1/3/14), `check_baseline_ratchet.sh` — «OK (15 снимков сверено)»
- [x] независимо от гейта: `pip-audit -r <uv export> --no-deps --disable-pip` — «No known
      vulnerabilities found»; `npm audit` — «found 0 vulnerabilities»
- [x] ⚠ на зелёном пути гейт печатает «не найдено ни одного поддерживаемого манифеста …
      не проверены» и не печатает счётчики — проверка манифестов в нём смотрит только в
      корень, а половины — в `backend/` и `frontend/`. Вопрос человеку (D6).
- [x] ⚠ **js-половина не различает «нашёл ноль» и «не смог»**: при недоступном реестре
      (`npm_config_registry=http://127.0.0.1:9/`, `npm audit` — rc 1, ECONNREFUSED) вывод
      гейта побайтно тот же, что у честного зелёного, exit 0, строки «○ пропущено» нет.
      С vitest 2.1.9 в дереве (critical=2): онлайн — exit 1, без реестра — **exit 0**.
      Отсутствие «○ пропущено» доказывает только python-половину; js-половину локально
      доказывает прямой `npm audit` (0), в CI — строка `npm ci` той же джобы (V2).

## V2, V3 — шаг CI и сторож класса

- [x] `backend/tests/test_manual_gates_run_in_ci.py` до шага CI — 2 красных:
      «deps-audit: scripts/lint/check_deps_audit.sh не зовёт ни один шаг CI — гейт не
      исполняется нигде»; сторож не слеп — `deps-audit` виден ему как manual-only
- [x] после шага — 3 зелёных
- [x] мутация «шаг без `if: always()`» — оба теста красные: «шаг аудита без if: always()»
      и «шаг CI с scripts/lint/check_deps_audit.sh без if: always() — упавший шаг выше
      унесёт его молча»
- [x] CI PR #46, прогон `40008573567`, джоба `gates` — шаг «Vulnerable dependencies»
      зелёный, 2.8 с: «python-половина мерена по uv.lock — дерево продукта, как в проде»,
      строк «○ пропущено» нет, затем то же ложное «не найдено ни одного поддерживаемого
      манифеста». js-половина в логе гейта не видна (см. V1); её свидетель — шаг
      «Install frontend deps» той же джобы за 45 с до гейта: `npm ci` — «audited 404
      packages … found 0 vulnerabilities». Джобы `backend`, `delivery`, `gates` — pass

## V4 — сьют фронта на vitest 5

- [x] 57 тестов в 11 файлах — те же числа по файлам, что на vitest 2.1.9
      (mic 8, vad 7, api 4, format 5, messages 4, SummaryCard 3, useVoiceSession 8,
      InterviewPage 5, TalkPage 3, SettingsPage 4, MicrophoneSetting 6); тесты не правлены
- [x] мутация: без строки `// @vitest-environment jsdom` `SummaryCard.test.tsx` — 3 из 3
      красные, `ReferenceError: document is not defined` (умолчание — node)
- [x] `clearMocks` (умолчание vitest 5 — `true`): с `clearMocks: false` в конфиге — 57/57,
      с умолчанием — 57/57

## V5 — сборка, линтеры, типы

- [x] `npm run build` — `index-DEbu37-m.js` 174.98 kB, `index-uwZHTTsa.css` 12.80 kB: те же
      хэши, что на vite 6.4.3 — бандл побайтно прежний
- [x] `npm run lint` — 0 ошибок, 1 предупреждение (`useVoiceSession` 193 строки — ратчет 1)
- [x] `prettier --check src` — чисто; `tsc -b --force` и `tsc --noEmit -p tsconfig.json` — 0
- [x] TS-половины гейтов: jscpd 71 файл / 0 клон-пар, сложность 94 файла / 0 находок,
      слои — ts 31 модуль и python 82 файла

## V6 — dev-сервер на 5273 без бэкенда

`npx vite --port 5273 --strictPort` — «VITE v6.4.5 ready», слушает `[::1]:5273`.

| Запрос | Ответ | Что значит |
|---|---|---|
| `GET /` | 200 text/html, с `/@react-refresh` | приложение и плагин React |
| `GET /src/main.tsx` | 200 text/javascript | трансформ модулей |
| `GET /no-such-route` | 200 text/html | SPA-фолбэк для чужих путей |
| `GET /health`, `/sessions/interviews`, `/settings`, `/vocabulary` | 500 text/plain | прокси: в логе vite `http proxy error … ECONNREFUSED 127.0.0.1:8000` на каждый |
| WS-апгрейд `/ws/voice` | соединение закрыто | в логе `ws proxy error … ECONNREFUSED 127.0.0.1:8000` |

## V7 — бэкенд на новом `uv.lock`

- [x] `UV_FROZEN=1 ./scripts/run_checks.sh` — 278 passed (275 базы `a4a0dce` + 3 сторожа),
      coverage 95.64 %, mypy strict («no issues found in 55 source files»), ruff
- [x] WS- и shutdown-тесты (`test_ws_voice`, `test_ws_pace`, `test_ws_meta`,
      `test_ws_prosody`, `test_ws_talk`, `test_shutdown_summary`) — 5 × 38 passed, висов нет
- [x] `uv lock --check` после перебазирования на `a4a0dce` — lock согласован с новым
      `pyproject.toml`

## V8 — гейт красный на возвращённом critical при любом снимке

- [x] `npm install --save-dev vitest@2.1.9` + снимок `py_total=99 js_critical=99 js_high=99
      js_total=999` (ратчет сработать не может) — exit 1: «✗ критические/высокие
      уязвимости: critical=2 high=1 — снимком не легализуются». Откат: снимок и манифесты
      из git, `npm ci` — vitest 5.0.5, vite 6.4.5, 0 уязвимостей
