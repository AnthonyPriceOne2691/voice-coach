# Diagnosis: сессия не закрывается при разрыве посередине хода

## Симптом (дословно, машиной)

Закрытие вкладки в состоянии `Thinking…` оставляет строку сессии незакрытой
навсегда:

```json
{"id": "6ed9c1df-…", "status": "in_progress", "ended_at": null, "duration_sec": 33}
```

В логе бэкенда — необработанное исключение, а НЕ предупреждение уборки:

```
ERROR:    Exception in ASGI application
  …
  File "backend/app/api/ws_voice.py", line 245, in _on_utterance_end
    await self._error("INTERNAL", "turn failed — please repeat", recoverable=True)
  File "backend/app/api/ws_voice.py", line 401, in _error
  File "backend/app/api/ws_voice.py", line 374, in _send
  File "starlette/websockets.py", line 98, in send
    raise RuntimeError('Cannot call "send" once a close message has been sent.')
RuntimeError: Cannot call "send" once a close message has been sent.
```

Строки `session cleanup did not finish` в логе **нет** — то есть уборка не
подвисла, а не запускалась вовсе.

## Как воспроизведён

Настоящий браузер, стенд собран в этой же сессии:
Chromium 151 headless по CDP → страница приложения → её VAD, MediaRecorder,
ws (doc 15) → whisper.cpp → `qwen2.5:14b-instruct` → Piper → SQLite.

Имитирован **только источник звука**: штатный флаг Chromium
`--use-file-for-fake-audio-capture` в этой сборке отдаёт цифровую тишину —
замер отдельной пробой: трек `Fake Default Audio Input`, `readyState: live`,
`muted: false`, `AudioContext: running`, **`peak_rms 0`, `−180 dBFS`**. Поэтому
подменён `getUserMedia`: страница получает поток из `AudioContext` с ответом,
синтезированным Piper. Всё ниже микрофона настоящее — whisper распознал речь и
она легла в транскрипт (`role: user`).

| Момент закрытия вкладки | `ended_at` | Прогонов |
|---|---|---|
| `Speaking` (агент говорит) | заполнен | 1 из 1 |
| `Listening…` (микрофон открыт) | заполнен | 1 из 1 |
| **`Thinking…` (ход в обработке)** | **`null`** | **2 из 2** |

Драйвер стенда: `drive2.py` в scratchpad сессии; цикл воспроизведения ~90 с.

## Журнал гипотез

**H1 — «уборка не успевает за 5 с (`DISCONNECT_CLEANUP_TIMEOUT_S`), LLM держит
ход».** **ОТВЕРГНУТА замером:** при просрочке код пишет
`session cleanup did not finish in 5.0s`; этой строки в логе нет, а `ended_at`
остаётся `null` и через несколько минут после закрытия — то есть уборка не
запускалась, а не не успела.

**H2 — «разрыв посередине хода не доходит до `except WebSocketDisconnect`».**
**ПОДТВЕРЖДЕНА трассировкой:** разрыв приходит не в `receive_json`, а внутрь
`_run_turn` — на `_transcript("user", …)`, то есть на отправке уже распознанной
реплики.

## Корневая причина

Цепочка из трёх звеньев, и каждое по отдельности выглядит безобидно:

1. **`WebSocketDisconnect` — это `Exception`**, и его глотает широкий
   `except Exception` в `_on_utterance_end` (`ws_voice.py:243`). Разрыв
   классифицируется как «ход не удался» — отсюда и `logger.exception("voice turn
   failed")` в логе, хотя ход не падал.
2. **Обработчик пытается сообщить об этом клиенту**, которого уже нет:
   `_error(…)` → `_send` → starlette отвечает `RuntimeError: Cannot call "send"
   once a close message has been sent.` Тот же путь есть у веток `SttEmptyError`
   и `OllamaError` — они тоже зовут `_error` после возможного разрыва.
3. **`RuntimeError` не ловится** `except WebSocketDisconnect` в `ws_session`
   (`ws_voice.py:65`) и уходит в ASGI. Уборка (`handler.aclose()`) стоит именно
   в этом `except` — значит не выполняется ни `flush` статуса, ни `ended_at`.

Почему тесты зелёные: репро-тест прошлой поставки рвёт соединение **в состоянии
ожидания**, где разрыв приходит в `receive_json` — штатным путём. Ход в момент
разрыва не выполняется ни в одном тесте.

## Что это НЕ

- **Не регрессия поставки `ws-disconnect-hang`.** Замер:
  `git diff 6a6132e 70c6d15 -- backend/app/api/ws_voice.py` — 52 изменённые
  строки, ни одна не в `_on_utterance_end`, `_error`, `_send`.
- **Не потеря транскрипта.** Реплики пишутся по ходу и на диске остаются;
  теряются время окончания и корректный статус сессии.
