# Tasks

- [x] T1. Worktree `fix/ws-disconnect-mid-turn` от `main`
- [x] T2. **Воспроизвести**: браузерный стенд, закрытие вкладки в `Thinking…` —
      `ended_at = null`, 2 прогона из 2 (`active/diagnosis.md`)
- [x] T3. Диагноз: разрыв приходит внутрь `_run_turn`, широкий `except Exception`
      принимает его за отказ хода, `_error` в мёртвый сокет роняет `RuntimeError`,
      уборка не запускается. H1 (таймаут уборки) отвергнута замером
- [x] T4. **Репро-тест** `test_disconnect_during_turn_finishes_session`: разрыв,
      пока мок LLM держит ход. Прогнать на СТАРОМ коде — обязан быть красным (B2)
- [x] T5. `WebSocketDisconnect` пробрасывается из `_on_utterance_end`, а не
      попадает в широкий `except Exception` (B1, B3)
- [x] T6. ОТМЕНЕНА замером: правка в `_send` репро не закрывает (только она —
      1 failed), а стоит доигранного в пустоту хода. Снята, см. verify-report
- [x] T7. Прогон сьюта: локально + linux-контейнер (L5); ruff, ruff format,
      mypy strict, module size
- [x] T8. **Браузерный прогон после фикса** (B6, §12.6): `ended_at` заполнен,
      2 из 2. UI-половина не проверена — посторонний дефект прокси Vite,
      решение человека: отдельная поставка
- [x] T9. Приёмка: pre-commit целиком, smoke-оракулы, `verify-report.md` + блок
      метрик §9.2
- [ ] T10. PR, зелёные `quality` + workflow `CI` по имени (L1), мерж через
      `merge_guard`, архив + строка в `INDEX.md`
