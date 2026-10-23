# Tasks: talk-check-core

- [x] T1 — `LlmClient.stream_chat` получает `json_schema` (Ollama `format`); параметры
  вызова объявлены один раз (`ChatOptions` + `Unpack`); клиент, фейки, тест тела запроса.
- [x] T2 — `data/prompts/language_check.txt`; `PromptLibrary.language_check` подставляет реплику.
- [x] T3 — `orchestrator/tips.py`: разбор кандидата, решение кода, `contract_gate` (C1, C3–C7).
- [x] T4 — `voice/language_check.py`: история + просьба последней, вызов со схемой (C8).
- [x] T5 — eval C9: `delivery/evals/talk-check/cases.yaml` (37 случаев) и `run.py`
  (+ `--latency` для C8); живой прогон — по «запускай».
- [x] T6 — доки 13, 16, 20; концепты `orchestrator-owns-structure`, `model-split`;
  `delivery/rule_enforcers.md`; `knowledge/log.md`.
- [ ] T7 — живой eval C9 и замер C8 по «запускай»; verify-report.
