# 17 — UI Screens & UX Specification

> Voice Interview Coach · Design doc · v0.1 · 2026-06-26

## Navigation (global)

```
┌────────────────────────────────────────────────────────────┐
│  Voice Interview Coach          [Interview][History][Words]│
│                                              [Settings ⚙]  │
└────────────────────────────────────────────────────────────┘
```

| Tab | Route | Phase |
|-----|-------|-------|
| Interview | — | 1 |
| Talk | — | ✅ 2026-10-17 |
| History | — | 2 |
| Useful Words | — | 2 |
| Settings | — | 1 ✅ 2026-08-13 |

⚠ **Маршрутов нет, и это решение, а не недоделка** (2026-08-13). Вкладки —
состояние в `App.tsx`. Роутер означал бы новую зависимость ради адресной
строки, которой в локальном инструменте для одного человека никто не
пользуется. Колонка `Route` оставлена пустой намеренно: обещание, которого
никто не собирается выполнять, хуже честного прочерка (урок L11 — два файла,
каждый следующий своей половине канона, вместе не работают).

---

## Screen 1a: Talk (2026-10-17)

Разговор с Генри на повседневные темы (doc 11). Приглашение — «Just talk.», три
таблетки (Everyday topics · English only · No grades) и кнопка **Start talking**
(`data-testid="start-talk"` — крючок для браузерного стенда, как у интервью). Во время
разговора — та же панель, что у интервью (`components/LiveSession.tsx`): орб,
полоска уровня, транскрипт по переключателю Live transcript; в шапке вместо счётчика
вопросов — «Talk with Henry». После конца — транскрипт и строка «Nice talk — see you
next time.» Экран «было → лучше» — D3a.2.

## Screen 1: Home / Interview (`/`)

**Purpose:** start Mode 1 or resume flow.

```
┌────────────────────────────────────────────────────────────┐
│  Mock Technical Interview                                   │
│  AI Automation Engineer · ~15 min · English                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🎙  Ready to practice?                              │   │
│  │                                                      │   │
│  │  [ Start Mock Interview ]                            │   │
│  │                                                      │   │
│  │  Last session: Jun 24 · Review pending → [Review]   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Tips: speak clearly · project details · metrics             │
└────────────────────────────────────────────────────────────┘
```

**States:**
- `idle` — Start button enabled if Ollama ok (`GET /health` + ollama probe)
- `ollama_down` — banner + setup link
- `last_review_pending` — CTA to History

---

## Screen 2: Active Session (`/session`)

**Purpose:** voice loop UI (Mode 1 or Mode 2).

```
┌────────────────────────────────────────────────────────────┐
│  ◀ End session          Technical Interview    ⏱ 12:34    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│              ┌─────────────────┐                            │
│              │   LISTENING     │  ← pulsing ring            │
│              │   (or SPEAKING) │                            │
│              └─────────────────┘                            │
│                                                             │
│  Live transcript (toggle in Settings)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Agent: Walk me through an internal tool you built.  │   │
│  │ You:  I built an inbound pipeline for our team...   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [ End session ]                                            │
└────────────────────────────────────────────────────────────┘
```

**State indicator values:** `loading_model` | `listening` | `processing` | `speaking`

**Mode 2 differences:**
- Header: «Review Together»
- Subtitle: linked interview date
- Same voice UI

**Loading model overlay** (Qwen ↔ R1):
```
Loading review model… (~10s)
```

---

## Screen 3: Interview Complete → Review prompt

**Route:** modal / `/session/complete`

```
┌────────────────────────────────────────────────────────────┐
│  Interview complete · 14 min saved                          │
│                                                             │
│  Review together with your recruiter friend?                │
│  Walk through what worked and what to sharpen.              │
│                                                             │
│  [ Start Review Together ]    [ Skip for now ]              │
└────────────────────────────────────────────────────────────┘
```

| Action | Result |
|--------|--------|
| Start Review | WebSocket `start_review` → Screen 2 (Mode 2) |
| Skip | `POST minimal-summary` → Screen 5 (minimal) |

---

## Screen 4: History (`/history`)

```
┌────────────────────────────────────────────────────────────┐
│  History                                                    │
├────────────────────────────────────────────────────────────┤
│  Jun 26, 2026 · Technical walkthrough · 14 min             │
│  Interview ✓   Review ✓   Scores available                  │
│  [View] [Review again] [Delete]                             │
├────────────────────────────────────────────────────────────┤
│  Jun 24, 2026 · Technical walkthrough · 15 min             │
│  Interview ✓   Review — not started                         │
│  [Start review] [View interview]                            │
└────────────────────────────────────────────────────────────┘
```

**Detail view (`/history/:interviewId`):**
- Tabs: Summary | Interview transcript | Review transcript
- Delete, export (P2)

---

## Screen 5: Summary (`/history/:id/summary`)

**Full debrief** (after Mode 2) or **minimal** (skip review).

```
┌────────────────────────────────────────────────────────────┐
│  Session summary                                            │
├────────────────────────────────────────────────────────────┤
│  Scores (1–5)                                               │
│  Clarity ████░  Structure ███░░  Depth ████░               │
│  English ███░░  Positioning ██░░░                            │
├────────────────────────────────────────────────────────────┤
│  Strengths                                                  │
│  · Strong queue explanation at Q4…                           │
├────────────────────────────────────────────────────────────┤
│  Improve                                                    │
│  · Q5: opened with SEO not automation → fix: …             │
├────────────────────────────────────────────────────────────┤
│  Vocabulary added (6) → [Open Useful Words]                 │
│  · human-in-the-loop · trade-off · idempotent                │
├────────────────────────────────────────────────────────────┤
│  Next focus: metrics in opening · positioning as builder     │
└────────────────────────────────────────────────────────────┘
```

**Minimal summary banner** (skip review):
> Full rubric available after Review Together. [Start review]

---

## Screen 6: Useful Words (`/vocabulary`)

```
┌────────────────────────────────────────────────────────────┐
│  Useful Words                    [Search…] [Category ▼]      │
├────────────────────────────────────────────────────────────┤
│  human-in-the-loop                                          │
│  RU: контроль человеком в цикле                             │
│  e.g. "We keep a human-in-the-loop step before auto-send."  │
│  · architecture · from Jun 26 session                       │
├────────────────────────────────────────────────────────────┤
│  trade-off                                                  │
│  RU: компромисс                                              │
│  e.g. "The trade-off was latency vs safety."                │
└────────────────────────────────────────────────────────────┘
```

---

## Screen 7: Settings (`/settings`)

| Setting | Type | Default | Построено |
|---------|------|---------|-----------|
| Speech pace | slider 0.85–1.60 | 1.15 | ✅ 2026-08-13 |
| Interview duration | 15 / 30 / 45 min | 15 | ✅ 2026-08-13 |
| Silence before end-of-turn | slider 0.8–3.0 s | 2.0 s | ✅ 2026-08-13 · default и max подняты 2026-09-07 |
| Show live transcript | toggle | **ON** | ✅ 2026-08-13 |
| Microphone device | dropdown + `Test` | system default | ✅ 2026-08-15 |

**Сохранение — на отпускании ползунка**, не на каждом движении: один проезд
иначе означал бы сорок запросов к базе. Значение, отвергнутое сервером (422 вне
коридора темпа), **показывается**, а не прячется: молчаливый зажим неотличим от
принятого значения.

Просодии (`piper_noise_scale`, `sentence_pause_ms`) здесь **нет намеренно** —
это характер голоса, а не ежедневная настройка; она живёт в конфиге (doc 03).

**Microphone** — список входов плюс кнопка `Test`: она открывает выбранный вход
и показывает живой уровень той же полоской, что видна в сессии, — с отметкой
порога VAD и словами «hearing you / silent». Без неё выбор был бы вслепую, а
слишком тихий вход обнаружился бы на середине интервью и выглядел бы как
поломка агента, а не как выбор устройства. Поток живёт **только** между двумя
нажатиями: постоянно открытый микрофон держал бы индикатор записи macOS
зажжённым всё время, пока открыт экран.

До выдачи разрешения браузер отдаёт устройства **без имён** — тогда вместо
списка стоит приглашение выдать доступ. Сохранённый вход, которого сейчас нет
(отключили или очистили данные сайта), показывается отдельной строкой
«Saved microphone — not connected»: экран не имеет права показывать «System
default», когда в базе лежит другое значение. Выбор применяется **со следующей
сессии** — микрофон открывается один раз на старте, и смена входа посреди хода
трогала бы эхо-защиту.

**Speech pace** уже существует как настройка (`speech_length_scale`, doc 15) и
меняется голосом внутри сессии — «speak slower» (doc 04). Регулятор здесь ещё
**не нарисован**: экрана Settings во фронте нет вовсе, и он появится вместе с
переработкой интерфейса. До тех пор единственный способ задать темп руками —
`PATCH /settings`.

Diagnostics section (read-only):
- Ollama status
- Models installed
- Last benchmark p95 (optional)

---

## Визуальный язык (2026-08-13)

Три поставки подряд перевели интерфейс на «жидкое стекло»:

| Поставка | Что переехало |
|---|---|
| 1 | дизайн-система (`styles/tokens|base|app.css`), оболочка, экран Interview |
| 2 | History, деталь сессии, Useful Words, разбор; **legacy-стили удалены** |
| 3 | экран Settings ✅ |

**Стекло — четыре свойства вместе:** заливка градиентом сверху вниз,
`backdrop-filter: blur+saturate`, светлая грань `inset 0 1px 0` (край ловит
свет), мягкая тень наружу. Убери любое — останется полупрозрачный прямоугольник.

**Иерархия строки списка:** когда → состояние таблетками → действия справа, где
заполненная кнопка ровно одна, а удаление — иконка без заливки. До 2026-08-13
`View`, `Review again` и `Delete` были одного веса.

## Component map (frontend)

| Component | LOC budget | Responsibility |
|-----------|------------|----------------|
| `SessionStateRing` | < 120 | listening/speaking visual |
| `TranscriptPanel` | < 150 | scrollable turns |
| `ReviewPromptModal` | < 100 | post-interview CTA |
| `SummaryCard` | < 200 | scores + lists |
| `VocabularyList` | < 200 | search/filter |
| `useVoiceSession` hook | < 200 | WebSocket + MediaRecorder |

---

## Responsive

MVP: **desktop-first** (interview at desk). Min width 1024px. Mobile — post-MVP.

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial UI screens; D-4/D-5/skip-review decisions applied |
| 2026-10-17 | Вкладка Talk — разговор с Генри; панель живой сессии общая для интервью и разговора |
