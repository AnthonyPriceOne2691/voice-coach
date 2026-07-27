---
type: Design
title: Микрофон открывается только после конца воспроизведения
description: Без этого VAD слышит собственный голос агента из колонок и режет ход сам себе; VAD работает во float-домене с порогом −50 dBFS.
status: accepted
tags: [voice, vad, audio]
implementation:
  - frontend/src/hooks/useVoiceSession.ts
  - frontend/src/lib/vad.ts
  - frontend/src/lib/audioQueue.ts
---

# Purpose

Класс багов «агент перебивает сам себя» не воспроизводится в тестах и выглядит как
проблема модели или сети. Причина всегда одна: микрофон открыли раньше, чем стихли
колонки.

# Canonical rules

- Захват микрофона стартует **только после того, как очередь воспроизведения пуста**
  и последний чанк действительно отзвучал — не по событию «LLM закончил» и не по таймеру.
- Пока `playing` истинно, VAD не принимает решений об окончании реплики.
- VAD считает в **float-домене**, порог тишины — **−50 dBFS**. Перевод в int16 или
  смена порога «на глаз» ломает детекцию на тихих микрофонах.
- Наушники проблему маскируют: проверять всегда на колонках.

# Related

- [Sentence streaming](sentence-streaming.md) — воспроизведение начинается до конца ответа,
  поэтому «конец воспроизведения» ≠ «конец генерации».
- [Transcript durability](../ops/transcript-durability.md) — что происходит при сбое хода.

# Implementation map

| Area | Path |
|---|---|
| Состояние сессии, открытие микрофона | `frontend/src/hooks/useVoiceSession.ts` |
| Детектор тишины | `frontend/src/lib/vad.ts` |
| Очередь воспроизведения + колбэк «отзвучало» | `frontend/src/lib/audioQueue.ts` |

# Sources

- `docs/03-voice-pipeline.md`, `docs/15-api-websocket-spec.md`
