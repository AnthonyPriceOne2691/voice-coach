# Design Documents Index

Планирование проекта ведётся через design docs в этой папке. Код пишется только после закрытия Phase 0 benchmark (см. [06-mvp-phases.md](06-mvp-phases.md)).

## Document map

| Doc | Status | Description |
|-----|--------|-------------|
| [00-project-overview.md](00-project-overview.md) | ✅ v0.1 | Контекст, цели, принятые решения |
| [01-requirements.md](01-requirements.md) | ✅ v0.2 | FR/NFR; OQ закрыты, D-8 open |
| [02-architecture.md](02-architecture.md) | ✅ v0.1 | Компоненты, потоки, repo layout |
| [03-voice-pipeline.md](03-voice-pipeline.md) | ✅ v0.3 | STT/LLM/TTS, latency (perceived), memory budget |
| [04-interview-orchestrator.md](04-interview-orchestrator.md) | ✅ v0.1 | State machine, question bank |
| [05-knowledge-base.md](05-knowledge-base.md) | ✅ v0.1 | CV/case injection, rubric, debrief |
| [06-mvp-phases.md](06-mvp-phases.md) | ✅ v0.3 | Phases 0–3; **Phase 0 ✅**; Phase 1 re-benchmark gate |
| [07-tech-stack.md](07-tech-stack.md) | ✅ v0.7 | Stack + LLM settings (канон — doc 16) |
| [14-llm-model-split.md](14-llm-model-split.md) | ⚠️ v0.2 | Model split; **D-8 open** (Mode 2 voice) |
| [08-post-session-debrief.md](08-post-session-debrief.md) | ✅ v0.1 | **Обязательная** обратная связь после каждой сессии |
| [09-agent-persona-and-tone.md](09-agent-persona-and-tone.md) | ✅ v0.1 | Supportive senior colleague — мягкий тон, mentor mode |
| [10-vocabulary-bank.md](10-vocabulary-bank.md) | ✅ v0.1 | Вкладка полезных слов, авто + перевод RU |
| [11-two-modes-review-dialogue.md](11-two-modes-review-dialogue.md) | ✅ v0.1 | Mode 1 Interview + Mode 2 Review Together |
| [12-session-storage.md](12-session-storage.md) | ✅ v0.2 | Хранение (канон схемы); turn + question_id |
| [13-behavioral-contracts.md](13-behavioral-contracts.md) | ✅ v0.2 | ABC-lite: sentence-gated enforcer, contract YAMLs в `data/contracts/` |
| [15-api-websocket-spec.md](15-api-websocket-spec.md) | ✅ v0.2 | REST + WebSocket contracts |
| [16-prompts-library.md](16-prompts-library.md) | ✅ v0.2 | Prompt files + **канон LLM params** |
| [17-ui-screens.md](17-ui-screens.md) | ✅ v0.1 | Screens, flows, components |
| [18-engineering-standards.md](18-engineering-standards.md) | ✅ v0.1 | **500 LOC**, SOLID, DRY, test coverage gates |
| [19-phase0-benchmark-results.md](19-phase0-benchmark-results.md) | ✅ v0.2 | **Phase 0 benchmark** — latency, decisions, raw log, **limitations** |
| [20-context-token-budget.md](20-context-token-budget.md) | ✅ v0.1 | **Token/context budget**, R1 thinking rule, Phase 1 re-benchmark gate |

## Project status

| Phase | Status |
|-------|--------|
| Phase 0 Benchmark | ✅ **Complete** (2026-06-26) |
| Phase 1 Voice loop | ✅ **Complete** (2026-07-03) — live-проверено с микрофоном |
| Phase 2 Full MVP | 🔲 **Next**: оркестраторы, Contract Enforcer, Mode 2, SQLite, History, Vocabulary Bank |
| Phase 3 Enhancements | 🔲 |

## Conventions

- Версия в шапке: `v0.x`
- **Changelog** в конце каждого документа
- Статусы: ✅ зафиксировано · 🔲 TBD · ❌ out of scope
- Новые docs: `08-`, `09-`, … по мере необходимости

## Review order (recommended)

1. Overview → Requirements
2. Architecture → Voice pipeline → **Context/token budget (20)**
3. Orchestrator → Knowledge base
4. Behavioral contracts → MVP phases → **Engineering standards** → Tech stack
5. Benchmark results (19) — включая Limitations перед стартом Phase 1

## Pending decisions

См. [19-phase0-benchmark-results.md](19-phase0-benchmark-results.md) (+ Limitations) и [14-llm-model-split.md](14-llm-model-split.md).

| ID | Decision | Status |
|----|----------|--------|
| D-1 | STT | ✅ small.en + whisper.cpp |
| D-2 | LLM Mode 1 | ✅ qwen2.5:14b-instruct |
| D-2b | LLM Summary/Vocabulary (JSON) | ✅ deepseek-r1:14b |
| D-3 | TTS | ✅ Piper lessac (piper-tts) |
| D-4 | First question | ✅ project walkthrough |
| D-5 | Live transcript | ✅ yes |
| D-6 | Skip review | ✅ minimal summary |
| D-7 | Voice debrief | ✅ text MVP |
| **D-8** | **LLM Mode 2 voice review** | ✅ **CLOSED 2026-07-03**: Qwen (R1 31–52 s/ход по Phase 1 benchmark — [doc 14](14-llm-model-split.md)) |
