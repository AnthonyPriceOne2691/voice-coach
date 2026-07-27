---
type: Policy
title: Транскрипт — единственный невосполнимый артефакт
description: Аудио и ответы модели воспроизводимы, транскрипт сессии — нет; он флашится на каждом ходе, а любое падение хода обязано быть recoverable.
status: accepted
tags: [data, durability, privacy]
implementation:
  - backend/app/storage/turns.py
  - backend/app/storage/repositories/interviews.py
  - backend/app/voice/turn_runner.py
---

# Purpose

Всё остальное в системе можно пересоздать: модель перегенерирует ответ, TTS
переозвучит, вопрос возьмётся из банка. Живую речь пользователя — нельзя.
Отсюда асимметрия в обработке ошибок.

# Canonical rules

- **Flush на каждом ходе.** Транскрипт пишется по мере хода, не в конце сессии.
  Сессия, оборвавшаяся на пятом вопросе, обязана оставить пять ходов на диске.
- **Падение хода — recoverable.** Ошибка STT/LLM/TTS завершает *ход*, а не сессию,
  и не должна уносить уже записанное.
- **Порядок:** сначала durable-запись реплики, потом побочные эффекты (summary,
  vocabulary bank). Обратный порядок теряет данные при сбое.
- **Приватность:** `data/sessions/**` — реальные транскрипты пользователя, gitignored.
  Не коммитить, не прикладывать к отчётам, не отправлять наружу (HITL —
  `delivery/CONSTITUTION.md` §12).

# Related

- [Echo protection](../engineering/echo-protection.md) — частый источник сбоя хода.

# Implementation map

| Area | Path |
|---|---|
| Запись ходов | `backend/app/storage/turns.py` |
| Репозиторий интервью | `backend/app/storage/repositories/interviews.py` |
| Обработка ошибок хода | `backend/app/voice/turn_runner.py` |

# Sources

- `docs/12-session-storage.md`, `docs/18-engineering-standards.md`
