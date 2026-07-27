# Engineering

Инварианты, нарушение которых ломает продукт тихо. Полный дизайн — `docs/00–20`.

* [Sentence streaming](sentence-streaming.md) - TTS по предложениям; буферизация проваливает latency-гейт
* [Model split (D-8)](model-split.md) - qwen2.5:14b в голосе, deepseek-r1 только offline
* [Orchestrator owns structure](orchestrator-owns-structure.md) - LLM даёт формулировки, не решения
* [Echo protection](echo-protection.md) - микрофон только после конца воспроизведения
