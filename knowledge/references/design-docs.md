---
type: Reference
title: Карта docs/00–20 ↔ concept'ы bundle
description: Где искать полный дизайн и какой concept фиксирует машинопроверяемый инвариант поверх него.
status: accepted
tags: [navigation, legacy]
implementation: []
---

# Purpose

`docs/00–20` остаются **каноническим дизайном** проекта. OKF-bundle их не заменяет
и не дублирует: он фиксирует те инварианты, которые агент чаще всего нарушает, и
привязывает их к путям в коде через `implementation:` (гейт `okf_sync_gate.py`).

# Canonical rules

- **Читать дизайн** — в `docs/`. **Проверять инвариант** — в `knowledge/`.
- Новое знание после 2026-07-28 — сразу concept'ом; `docs/` не растёт big-bang'ом.
- Тронул легаси-тему в работе → выжми её в concept (ratchet, OKF §6).

# Map

| docs | Concept |
|---|---|
| `00-project-overview`, `01-requirements`, `06-mvp-phases` | [product/overview](../product/overview.md) |
| `03-voice-pipeline`, `13-behavioral-contracts`, `19-benchmarks` | [sentence-streaming](../engineering/sentence-streaming.md) |
| `14-llm-model-split`, `16-prompts-library`, `20-token-budget` | [model-split](../engineering/model-split.md) |
| `04-interview-orchestrator`, `11-two-modes` | [orchestrator-owns-structure](../engineering/orchestrator-owns-structure.md) |
| `03-voice-pipeline`, `15-api-websocket-spec` | [echo-protection](../engineering/echo-protection.md) |
| `12-session-storage`, `18-engineering-standards` | [transcript-durability](../ops/transcript-durability.md) |

# Not yet covered by concepts

Пока живут только в `docs/`: персона и тон (09), словарь (10), post-session debrief (08),
UI-экраны (17), схема API целиком (15), knowledge base кандидата (05).
Переносятся ratchet'ом по мере касания.

# Sources

- `docs/README.md`
