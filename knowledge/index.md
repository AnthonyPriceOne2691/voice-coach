---
okf_version: "0.2"
---

# Product

* [Overview](product/overview.md) - что это за инструмент, для кого и какие у него границы

# Engineering

* [Engineering index](engineering/) - инварианты voice-цикла, разделение моделей, контракты
* [Sentence streaming](engineering/sentence-streaming.md) - почему TTS идёт по предложениям
* [Model split (D-8)](engineering/model-split.md) - qwen в голосе, R1 только offline
* [Orchestrator owns structure](engineering/orchestrator-owns-structure.md) - LLM отвечает только за формулировки
* [Echo protection](engineering/echo-protection.md) - микрофон открывается после конца воспроизведения

# Ops

* [Ops index](ops/) - приватность данных, локальный запуск
* [Transcript durability](ops/transcript-durability.md) - транскрипт как невосполнимый артефакт
* [Talk memory](ops/talk-memory.md) - что может попасть в память Генри между разговорами (D3b)

# References

* [References](references/) - внешние спеки и указатели
* [Design docs map](references/design-docs.md) - соответствие docs/00–20 и concept'ов

# Legacy

* [Design docs `docs/`](../docs/) - канонический дизайн проекта (docs/00–20); OKF не заменяет их,
  а фиксирует инварианты, которые агент чаще всего нарушает. Миграция — ratchet'ом (§6).
