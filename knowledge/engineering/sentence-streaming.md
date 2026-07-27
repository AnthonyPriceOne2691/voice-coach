---
type: Design
title: TTS стримится по предложениям, а не полным ответом
description: Буферизация полного ответа LLM перед синтезом проваливает latency-гейт хода; enforcer контрактов тоже работает per-sentence.
status: accepted
tags: [voice, latency, tts]
implementation:
  - backend/app/voice/turn_runner.py
  - backend/app/voice/tts_piper.py
  - backend/app/voice/interview_flow.py
  - backend/app/voice/review_flow.py
  - backend/app/contracts/enforcer.py
  - frontend/src/lib/audioQueue.ts
---

# Purpose

Самое дорогое в голосовом ходе — ожидание. Инвариант зафиксирован здесь, потому что
«собрать ответ целиком, потом озвучить» выглядит как безобидное упрощение кода и
регулярно предлагается при рефакторинге.

# Canonical rules

- Токены LLM режутся на предложения и уходят в TTS **по мере готовности**; первое
  предложение начинает звучать до того, как модель дописала ответ.
- Contract Enforcer проверяет **каждое предложение** перед синтезом (doc 13), а не
  готовый ответ: иначе нарушение уже прозвучало в колонках.
- Буферизация полного ответа запрещена. Замерено: **4.8 s против 3.0 s** на ход —
  это провал latency-гейта, а не «немного медленнее».
- Изменение схемы стриминга = смена инварианта → нужна spec и human OK
  (`delivery/CONSTITUTION.md` §9).

# Related

- [Model split (D-8)](model-split.md) — почему в голосе не может стоять reasoning-модель.
- [Echo protection](echo-protection.md) — вторая половина тайминга хода.

# Implementation map

| Area | Path |
|---|---|
| Цикл хода (сборка предложений) | `backend/app/voice/turn_runner.py` |
| Синтез | `backend/app/voice/tts_piper.py` |
| Потоки режимов | `backend/app/voice/interview_flow.py`, `backend/app/voice/review_flow.py` |
| Per-sentence контракты | `backend/app/contracts/enforcer.py` |
| Проигрывание на клиенте | `frontend/src/lib/audioQueue.ts` |

# Sources

- `docs/03-voice-pipeline.md`, `docs/13-behavioral-contracts.md`
- Замеры: `docs/19-phase0-benchmark-results.md`
