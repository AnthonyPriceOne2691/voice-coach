---
type: Overview
title: Voice Interview Coach — что это и для кого
description: Локальный офлайн-агент для mock technical interviews на английском; один пользователь, приватность по умолчанию, latency как продуктовое требование.
status: accepted
tags: [product, scope]
implementation: []
---

# Purpose

Границы продукта, из которых следуют почти все инженерные решения. Без них
предложения вида «добавим мультипользовательский режим» или «вынесем модель в
облако» выглядят улучшениями, а не сменой продукта.

# What it is

Голосовой AI-агент (**Генри**), проводящий mock technical interview на английском:
whisper.cpp (STT) → Ollama `qwen2.5:14b-instruct` (LLM) → Piper (TTS), FastAPI + React.

Два режима: **Mode 1** — интервью, **Mode 2** — review-диалог по прошедшей сессии.
После сессии — offline summary и Vocabulary Bank.

# Canonical rules (границы)

- **Один пользователь, локальная машина.** MacBook Air M5 / 32 GB. Нет
  мультитенантности, нет аутентификации, нет облачного состояния.
- **Всё офлайн, privacy-first.** Ни один фрагмент речи или транскрипта не покидает
  машину. Внешние API-вызовы к LLM-провайдерам — вне продукта.
- **Latency — продуктовое требование**, не оптимизация: тёплый ход ~3.0 s.
  Всё, что его ломает, ломает продукт.
- **Английский — язык сессии**; русский появляется только в `translation_ru`
  словаря и в summary для пользователя.

# Non-goals

- Оценка «пройдёт/не пройдёт» реальное собеседование.
- Многопользовательский или облачный режим.
- Замена живой практики с человеком.

# Related

- [Model split (D-8)](../engineering/model-split.md)
- [Sentence streaming](../engineering/sentence-streaming.md)
- [Transcript durability](../ops/transcript-durability.md)

# Sources

- `docs/00-project-overview.md`, `docs/01-requirements.md`, `docs/06-mvp-phases.md`
