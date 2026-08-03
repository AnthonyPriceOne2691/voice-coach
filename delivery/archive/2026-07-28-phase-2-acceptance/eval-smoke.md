# Eval smoke — this shipment

Derived from spec acceptance. Run during verify.
Живой прогон (whisper / qwen / piper) — ручной: он не в CI (constitution §11).

- [ ] Mode 1: старт интервью → Генри задаёт первый вопрос голосом; микрофон
      открывается только после конца воспроизведения (echo-защита)
- [ ] 3+ хода подряд без падений; каждый ход появляется в `data/sessions/` сразу
      (flush per turn, не в конце сессии)
- [ ] Mode 2 review отрабатывает; в тексте, уходящем в TTS, нет markdown-разметки
- [ ] Summary генерируется; `translation_ru` — чистый русский без артефакта
- [ ] Vocabulary Bank пополнился словами из сессии
- [ ] History показывает сессию с корректным числом ходов
- [ ] Warm full-turn latency на глаз не хуже ~3 s (регресс sentence-streaming виден сразу)
