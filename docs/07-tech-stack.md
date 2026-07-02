# 07 — Tech Stack (Local M5) — Recommended

> Voice Interview Coach · Design doc · **v0.7** · 2026-07-02  
> Status: **recommended for implementation**. Модели: Mode 1 + summary закрыты Phase 0; Mode 2 voice — **D-8 open** ([14-llm-model-split.md](14-llm-model-split.md))

## Принципы выбора

1. **Local-first** — zero cloud в MVP  
2. **Familiar** — FastAPI, React/TS (твой стек)  
3. **Minimal moving parts** — без LangChain/LangGraph/Docker на старте  
4. **Latency** — streaming LLM + sentence-chunk TTS  
5. **Enforceable** — orchestrator + contract enforcer в коде, не в framework  
6. **Dialog quality** — сильная модель для разговора и рассуждений; правила **дополняют**, не заменяют интеллект  

---

## LLM strategy: quality + rules (не «или»)

```
Behavioral contracts          Сильная модель
(что нельзя / формат)    +    (как думать и говорить)
        │                              │
        └──────────▶ Voice dialog ◀────┘
```

**7B мало** для качественного mock interview + nuanced review.  
**32B на MacBook Air 32 GB** — не рекомендуем.

**Выбор: two-model split**

| Mode | Model | Status |
|------|-------|--------|
| **Mode 1 — Live Interview** | **`qwen2.5:14b-instruct`** | ✅ Phase 0 |
| **Mode 2 — Review (voice dialog)** | **`qwen2.5:14b-instruct`** | ✅ **D-8 закрыт** Phase 1: R1 31–52 s/ход vs Qwen 0.2 s TTFT ([14-llm-model-split.md](14-llm-model-split.md)) |
| **Summary + Vocabulary (JSON, offline)** | **`deepseek-r1:14b`** | ✅ latency некритична |

Правило простое: **всё голосовое — instruct, всё офлайновое — reasoning.** Бонус: model swap на входе в Mode 2 исчез — R1 нужен только summary-pass'у.

---

## Stack at a glance

```
┌─────────────────────────────────────────────────────────────┐
│  Browser: React 18 + Vite + TS + Tailwind                    │
│  Mic → WebSocket → playback                                  │
└───────────────────────────┬─────────────────────────────────┘
                            │ ws://localhost:8000
┌───────────────────────────▼─────────────────────────────────┐
│  Python 3.12 · FastAPI · uvicorn                             │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐  │
│  │ Orchestrator│ │ Contract     │ │ Session Store       │  │
│  │ (Mode 1/2)  │ │ Enforcer     │ │ SQLite + SQLAlchemy │  │
│  └──────┬──────┘ └──────┬───────┘ └─────────────────────┘  │
│         └───────────────┼──────────────────────────────────│
│                         ▼                                    │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Whisper  │  │ Qwen 14B     │  │ Piper    │  │ Silero  │ │
│  │ .cpp STT │  │ instruct +   │  │ TTS      │  │ VAD     │ │
│  └──────────┘  │ R1 14B       │  └──────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────┘
         Ollama runs as separate local daemon (brew)
```

---

## Layer-by-layer (decisions)

### Runtime & packaging

| Choice | Version | Why |
|--------|---------|-----|
| **Python** | 3.12 | Stable, fast, good async |
| **Package manager** | **uv** | Fast installs, lockfile, replaces pip+poetry |
| **Node** | 20 LTS | Vite/React |
| **Process** | 1× uvicorn + Ollama daemon | Solo local tool; split later if needed |

### Backend framework

| Choice | Why |
|--------|-----|
| **FastAPI** | Async, WebSocket, Pydantic v2, знакомый стек |
| **uvicorn[standard]** | WS + reload dev |
| **httpx** | Async streaming to Ollama API |
| **pydantic + pydantic-settings** | Schemas, debrief JSON, config |
| **PyYAML** | `data/contracts/*.yaml` |
| **structlog** | Structured logs, violation events |

**Not in MVP:** LangChain, LangGraph, Celery, Redis, Docker.

### LLM — two-model split ✅

| Role | Ollama model | RAM ~ | Pull |
|------|--------------|-------|------|
| **Mode 1 Live Interview** | **`qwen2.5:14b-instruct`** | ~9 GB | **required** |
| **Mode 2 Review** | **`deepseek-r1:14b`** | ~9 GB | already local |
| **Summary + vocabulary** | **`deepseek-r1:14b`** | (same) | already local |

**Runtime:** Ollama (MLX on Apple Silicon). Fallback if slow: mlx-lm.

**Swap rule:** во время Mode 1 loaded только **Qwen instruct** + whisper + piper. Перед Mode 2 — Ollama evict Qwen → load **R1**. Не держать обе 14B одновременно (~18 GB models alone).

#### Почему split

| | Qwen2.5 14B Instruct | DeepSeek R1 14B |
|--|---------------------|-----------------|
| **Live interview** | ✅ Оптимум — сразу spoken output | ❌ thinking-chain → latency |
| **Review dialogue** | ✅ OK | ✅ Лучше — deep reasoning |
| **Summary JSON** | ✅ OK | ✅ Лучше — rubric + vocabulary |
| **Behavioral contracts** | ✅ Instruction-following | ⚠️ нужен strip thinking |

#### Settings

> ⚠️ Канонический источник параметров — **[16-prompts-library.md](16-prompts-library.md)**; эта секция зеркалит его. Token/context бюджеты — [20-context-token-budget.md](20-context-token-budget.md).

```yaml
interview:   # Mode 1 → qwen2.5:14b-instruct
  model: qwen2.5:14b-instruct
  num_ctx: 8192
  temperature: 0.75
  max_tokens: 220
  stream: true

review:      # Mode 2 → qwen2.5:14b-instruct (D-8 закрыт, вариант B)
  model: qwen2.5:14b-instruct
  num_ctx: 8192
  temperature: 0.6
  max_tokens: 300
  stream: true

summary:     # post-review → deepseek-r1:14b (включая vocabulary — один pass)
  model: deepseek-r1:14b
  num_ctx: 16384           # два полных транскрипта не влезают в 8192 (doc 20)
  temperature: 0.3
  max_tokens: 4096         # thinking + JSON ~2500
  stream: false
  format: json
  strip_thinking: true

minimal_summary:  # skip-review fallback → Qwen (уже загружен в момент Skip!)
  model: qwen2.5:14b-instruct   # swap на R1 ради «минимальной» сводки = ~40 s ожидания, абсурд
  num_ctx: 8192
  temperature: 0.3
  max_tokens: 800
  format: json
```

**Vocabulary** — не отдельный вызов в MVP: входит в summary pass (поле `vocabulary[]` в схеме, doc 08). Отдельный `vocabulary_extract` — P1, если качество извлечения в общем pass'е окажется слабым.

#### Fallback

| If… | Then… |
|-----|--------|
| Qwen 14B p95 turn > 4 s на продовом промпте (Phase 1 re-benchmark) | try **`llama3.1:8b`** for Mode 1 (faster, slightly simpler follow-ups) |
| R1 review too slow / quality weak | **D-8 вариант B**: Qwen для Mode 2 voice, R1 только summary |
| One model only | **not recommended**; prefer Qwen solo over R1 solo for this product |

### STT

| Choice | Why |
|--------|-----|
| **whisper.cpp** (Metal build) | Best latency/quality on Apple Silicon |
| **Model** | **`ggml-small.en.bin`** MVP default; upgrade to `medium.en` if WER bad in Phase 0 |
| **Integration** | **subprocess CLI** MVP (`whisper-cli -f audio.wav`) — zero binding pain |

**Alternative if subprocess annoys:** `faster-whisper` (CPU/CTranslate2, still fast on M5).

Mode: **batch after end-of-utterance** (not streaming STT in MVP).

### TTS

| Choice | Why |
|--------|-----|
| **Piper** | Offline, fast, low RAM |
| **Voice** | `en_US-lessac-medium` or `en_GB-alan-medium` — pick **one**, document in config |
| **Integration** | `piper` binary subprocess → WAV chunk per sentence |

**Phase 0 benchmark:** Kokoro-82M — adopt only if Piper quality unacceptable.

Pipeline: LLM stream → buffer until `.` / `?` → Piper → send audio chunk to client.

### VAD (end of user turn)

| Layer | Choice |
|-------|--------|
| **Client (primary)** | Web Audio API: silence **1.2 s** @ threshold → send `utterance_end` |
| **Server (backup)** | **silero-vad** (ONNX, lightweight) if client false triggers |

No WebRTC/cloud VAD.

### Frontend

| Choice | Why |
|--------|-----|
| **React 18 + Vite + TypeScript** | Standard, fast HMR |
| **Tailwind CSS** | Quick UI: tabs, History, Useful Words, session states |
| **WebSocket** | Native API — audio chunks + JSON events |
| **MediaRecorder** | Mic capture (webm/opus → server decodes to WAV) |
| **Audio playback** | `AudioContext` queue for TTS chunks |

**Not MVP:** Tauri/Electron (browser enough for localhost tool), Next.js (overkill).

Dev proxy: Vite `proxy` `/ws` and `/api` → `:8000`.

### Storage

| Choice | Why |
|--------|-----|
| **SQLite** | Single file, local, backup = copy file |
| **SQLAlchemy 2.0** | Models for `interview_sessions`, `review_sessions`, `vocabulary_bank` |
| **aiosqlite** | Async session writes, checkpoint transcripts |
| **Migrations** | Manual SQL or Alembic post-MVP — для solo MVP можно `create_all()` |

Files: `data/sessions/app.db`, prompts/contracts in git.

### Orchestration & contracts

| Choice | Why |
|--------|-----|
| **State machine** | Plain Python `Enum` + transition functions — см. doc 04, 11 |
| **Contract Enforcer** | Pure Python module: regex, sentence count, lang detect — см. doc 13 |
| **Prompts** | Jinja2 templates in `data/prompts/` optional; plain `.txt` OK for MVP |

**Not MVP:** LangGraph (add when modes/personas multiply).

### Audio processing

| Lib | Use |
|-----|-----|
| **ffmpeg** (brew) | webm → wav 16kHz mono |
| **soundfile** or **pydub** | WAV I/O |
| **numpy** | audio buffers if needed |

---

## Project structure

```
voice-interview-coach/
├── backend/
│   ├── pyproject.toml          # uv
│   └── app/
│       ├── main.py             # FastAPI + WS routes
│       ├── config.py           # pydantic-settings
│       ├── voice/              # stt, tts, vad, gateway
│       ├── llm/                # ollama client, streaming
│       ├── orchestrator/       # interview.py, review.py
│       ├── contracts/          # enforcer, patterns, recovery
│       ├── summary/            # JSON rubric + vocabulary extract
│       ├── db/                 # models, repository
│       └── ws/                 # session handler
├── frontend/
│   ├── package.json
│   └── src/
│       ├── pages/              # Interview, Review, History, Words
│       ├── hooks/              # useVoiceSession, useWebSocket
│       └── components/
├── data/
│   ├── contracts/
│   ├── prompts/
│   ├── knowledge/              # CV, case study copies
│   └── sessions/               # app.db
├── scripts/
│   ├── setup_mac.sh            # brew deps, models
│   ├── download_models.sh
│   └── spike/                  # Phase 0 benchmark
└── docs/
```

---

## `pyproject.toml` (core deps)

```toml
[project]
name = "voice-interview-coach"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "httpx>=0.28",
  "pydantic>=2.10",
  "pydantic-settings>=2.6",
  "sqlalchemy[asyncio]>=2.0",
  "aiosqlite>=0.20",
  "pyyaml>=6.0",
  "structlog>=24.0",
  "jinja2>=3.1",
  "soundfile>=0.12",
]

[project.optional-dependencies]
vad = ["onnxruntime>=1.20", "silero-vad"]  # or manual silero setup
dev = ["pytest", "pytest-asyncio", "ruff"]
```

Frontend:

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3",
    "react-router-dom": "^6.28"
  },
  "devDependencies": {
    "typescript": "^5.6",
    "vite": "^6.0",
    "@vitejs/plugin-react": "^4.3",
    "tailwindcss": "^3.4"
  }
}
```

---

## System setup (Mac M5)

```bash
# One-time
brew install ollama ffmpeg
# whisper.cpp: brew install whisper-cpp  OR build from source with GGML_METAL=1
# piper: download release binary + voice model to data/models/piper/

ollama pull qwen2.5:14b-instruct   # Mode 1 live interview
# deepseek-r1:14b                  # already local — Mode 2 + summary

cd voice-interview-coach
uv sync
cd frontend && npm install
./scripts/download_models.sh
```

---

## Memory budget (32 GB) — concurrent load

| Phase | Loaded | RAM ~ |
|-------|--------|-------|
| **Mode 1 voice turn** | Qwen 14B instruct + whisper + Piper | ~14–16 GB |
| **Mode 2 / summary** | DeepSeek R1 14B (+ whisper in review) | ~14–16 GB |
| **Headroom** | macOS + browser | ~14 GB ✅ |

Disk: ~9 GB × 2 models ≈ 18 GB. Never load both 14B models at once.

---

## WebSocket protocol (sketch)

```json
// client → server
{ "type": "utterance_end", "audio": "<base64 webm>" }
{ "type": "start_interview" | "start_review", "interview_id?": "..." }

// server → client
{ "type": "state", "value": "listening|processing|speaking" }
{ "type": "transcript", "role": "user|agent", "text": "..." }
{ "type": "audio", "chunk": "<base64 wav>", "final": false }
{ "type": "session_end", "interview_id": "...", "review_id?": "..." }
```

---

## Phase 0 benchmark decides

| Decision | Default | Benchmark result (2026-06-26) |
|----------|---------|--------------------------------|
| STT model | small.en | ✅ **small.en** confirmed |
| STT runtime | whisper.cpp Metal | ✅ warm ~735 ms |
| **Mode 1 (live)** | **`qwen2.5:14b-instruct`** | ✅ warm ~1.8 s (no 8B fallback) |
| **Mode 2 voice** | `deepseek-r1:14b` | ⚠️ ~18–21 s/ход, output пустой при малом num_predict → **D-8 open** |
| **Summary (JSON)** | **`deepseek-r1:14b`** | ✅ latency некритична |
| TTS | Piper lessac | ✅ **piper-tts** package |
| p95 turn latency | < 5 s | ✅ **~3.1 s** warm |

> Full report: [19-phase0-benchmark-results.md](19-phase0-benchmark-results.md)

---

## Explicitly avoided

| Tech | Reason |
|------|--------|
| OpenAI Realtime / cloud STT-TTS | Privacy, offline |
| LangChain / LangGraph | Complexity; httpx + state machine enough |
| PostgreSQL | Single user |
| Docker | Native Mac tool |
| Next.js / Electron | Browser sufficient |
| Browser Web Speech API | Cloud-dependent |

---

## Dev workflow

```bash
# T1
ollama serve

# T2
cd backend && uv run uvicorn app.main:app --reload --port 8000

# T3
cd frontend && ./node_modules/.bin/vite   # :5273 → proxy :8000 (5173 занят линкбилдинг-проектом; npm run dev не работает из-за ':' в пути)
```

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | v0.1 initial |
| 2026-06-26 | v0.2 optimal stack consolidated |
| 2026-06-26 | v0.3 two-tier LLM |
| 2026-06-26 | v0.4 single-tier deepseek-r1:14b |
| 2026-06-26 | v0.5 **two-model split**: Qwen instruct (Mode 1) + R1 (Mode 2/summary) |
| 2026-06-26 | v0.6 Phase 0 benchmark results — all decisions confirmed |
| 2026-07-02 | v0.7 settings согласованы с doc 16 (канон); R1 max_tokens 450→2048 (пустой output Phase 0); summary num_ctx 16384; vocabulary merged в summary pass; Mode 2 voice → D-8 open; fallback `llama3.1:8b` |
| 2026-07-02 | v0.8 minimal_summary → Qwen (без model swap при Skip, ~40 s → мгновенно) |
| 2026-07-03 | v0.9 **D-8 закрыт**: review → qwen2.5:14b-instruct (Phase 1 benchmark); R1 остаётся только в summary |
