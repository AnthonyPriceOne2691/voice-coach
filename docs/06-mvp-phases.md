# 06 — MVP Phases & Delivery Plan

> Voice Interview Coach · Design doc · v0.3 · 2026-07-02

## Engineering standards (все фазы)

С **Phase 1** и на всём пути к MVP — обязательны правила из **[18-engineering-standards.md](18-engineering-standards.md)**:

| Правило | Суть |
|---------|------|
| **≤ 500 LOC** | Любой файл в `backend/app/`, `frontend/src/` |
| **SOLID** | Слои, интерфейсы STT/TTS/LLM, DI, один класс — одна ответственность |
| **DRY** | Общая логика в shared; prompts/contracts — в `data/`, не в коде |
| **Тесты** | Максимальное разумное покрытие; пороги по фазам — в doc 18 |

**Phase 0** — только spike-скрипты, лимит LOC не на prod-код (его ещё нет).

## Phase overview

```
Phase 0          Phase 1           Phase 2            Phase 3
Benchmark   ──▶  Voice loop   ──▶  Full MVP      ──▶  Enhancements
(1–2 days)       (3–5 days)        (5–7 days)         (ongoing)
```

## Phase 0 — Benchmark & spike

**Status: ✅ COMPLETE** (2026-06-26) — см. [19-phase0-benchmark-results.md](19-phase0-benchmark-results.md)

**Goal:** доказать, что local voice loop укладывается в latency budget на M5.

**Deliverables:**
- [x] Script: STT → LLM question → TTS (`scripts/spike/benchmark_turn.py`)
- [x] Measured p50/p95 turn latency (warm **~3.1 s**)
- [x] Финальные модели: **small.en** + **Qwen 14B** + **Piper lessac** (piper-tts)
- [x] `docs/03-voice-pipeline.md` + `docs/19-phase0-benchmark-results.md`

**Exit criteria:**
- [x] p95 turn latency **< 5 s** warm → **~3.1 s** ✅
- [x] English interviewer voice acceptable (Piper lessac)

**No app code required** — только scripts в `scripts/spike/`.

---

## Phase 1 — Minimal voice loop

**Goal:** end-to-end без orchestrator — «echo interviewer»: STT → LLM as generic interviewer → TTS.

**Deliverables:**
- [ ] FastAPI backend: `/health`, `/session/turn` (audio in → audio out)
- [ ] Whisper integration (whisper.cpp subprocess or binding)
- [ ] Ollama LLM integration (streaming)
- [ ] Piper TTS integration
- [ ] Minimal React UI: Start, mic, play response, show transcript
- [ ] `data/prompts/interviewer_system.txt`

**Exit criteria:**
- 5 manual back-and-forth turns without crash
- Transcript logged to JSON file
- **Re-benchmark на продовом промпте** ([20-context-token-budget.md](20-context-token-budget.md)): p95 full turn < 4 s warm при 4–5K-токенном промпте; STT на 60–90 s utterance замерен
- **D-8 закрыт**: R1 c `num_predict: 2048` на review-промпте — latency + quality vs Qwen; решение зафиксировано в doc 14 (блокер для Review orchestrator в Phase 2)
- Sentence-streaming TTS работает (perceived latency, см. doc 03) — не отложено на Phase 2

**Engineering exit criteria (Phase 1):**
- [ ] Repo layout по [02-architecture.md](02-architecture.md); нет monolith-файлов
- [ ] `LlmClient`, `SpeechToText`, `TextToSpeech` — интерфейсы + Ollama/Whisper/Piper impl
- [ ] Unit-тесты: LLM client (mock), API `/health`, voice turn handler (mock pipeline)
- [ ] Coverage `backend/app/` ≥ **70%** (растёт к 85% в Phase 2)
- [ ] `ruff` + pytest в `pyproject.toml`; `npm test` (vitest) для frontend utils/hooks
- [ ] `scripts/check_module_size.py` — fail если файл > 500 LOC

---

## Phase 2 — MVP (interview simulator)

**Goal:** полный MVP из brief — structured session + debrief.

**Deliverables:**
- [ ] Interview orchestrator (state machine)
- [ ] Mode: `technical_project_walkthrough`, 15 min
- [ ] Question bank + follow-up logic
- [ ] Knowledge loader + `profile_condensed.md`
- [ ] SQLite session store
- [ ] Contract Enforcer (ABC-lite) — interview + review contracts
- [ ] Review orchestrator (Mode 2) + recruiter friend persona
- [ ] Session storage: interview + review tables
- [ ] History UI
- [ ] Summary generator + rubric UI
- [ ] Vocabulary Bank: tab UI + auto-extract
- [ ] Session list / history (minimal)

**Exit criteria (MVP definition of done):**
1. ✅ Mode 1: 15 min voice mock interview
2. ✅ Mode 2: Review Together voice dialog (recruiter friend)
3. ✅ Both transcripts saved; History shows pairs
4. ✅ Structured summary + Useful Words after review
5. ✅ CV/case study in context
6. ✅ All local, no cloud API
7. ✅ Contract Enforcer: hard rules Mode 1 before TTS

**Engineering exit criteria (Phase 2):**
- [ ] Все критерии из [18-engineering-standards.md](18-engineering-standards.md) §6 Definition of Done
- [ ] Coverage: contracts ≥ 95%, orchestrator ≥ 90%, backend `app/` ≥ **85%**
- [ ] Contract enforcer + оба orchestrator — unit-тесты на все hard rules
- [ ] Integration: interview → review → summary (mocked LLM fixtures)
- [ ] Нет файлов > 500 LOC; CI/local `pytest --cov-fail-under=85`

---

## Phase 3 — Enhancements (post-MVP)

Prioritized backlog:

| Item | Priority | Effort |
|------|----------|--------|
| Hard mode (interrupts, simplify) | P1 | M |
| Session memory / weak topic repeat | P1 | M |
| Additional modes (behavioral, system design) | P2 | L |
| Multiple personas | P2 | M |
| RAG over documents | P2 | L |
| Barge-in (interrupt agent TTS) | P2 | M |
| Streaming STT | P2 | L |
| Try again on weak questions | P2 | S |
| Flashcards export | P3 | S |
| Cloud LLM fallback (optional) | P3 | M |

---

## MVP scope checklist

Copy from brief — track in this doc:

| # | Feature | Phase |
|---|---------|-------|
| 1 | Mode 1: voice mock interview 15 min | 2 |
| 2 | Mode 2: Review Together (voice) | 2 |
| 3 | Store interview + review transcripts | 2 |
| 4 | Summary + Useful Words after review | 2 |
| 5 | CV/case in context | 2 |

**Explicitly NOT in MVP:**
- RAG
- Multiple personas
- Spaced repetition quiz
- Anki/CSV export (P2)

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Latency too high | Unusable UX | Phase 0 benchmark; smaller models; sentence TTS |
| **Prefill на продовом промпте 4–5K токенов** (не замерен в Phase 0) | +1–3 s на turn → провал NFR-1.1 | KV-prefix cache (стабильный префикс); Phase 1 re-benchmark gate (doc 20) |
| **R1 в Mode 2: ~18–21 s каждый ход, quality не проверен** | Голосовой review неюзабелен | D-8: вариант B (Qwen для voice review); закрыть до Phase 2 (doc 14) |
| **STT на длинных ответах (60–90 s)** | 3–5 s STT → превышение бюджета | Замер Phase 1; chunked STT P2 |
| LLM weak follow-ups | Generic interview | Better prompt + condensed profile; try 14B |
| TTS fatigue | Annoying voice | Piper подтверждён Phase 0; Kokoro — запасной |
| Scope creep | Never ship MVP | Phase gates; no Phase 3 until Phase 2 exit |
| M5 thermal throttling | Slowdown mid-session | Air cooling; model pre-load; avoid 14B+large whisper together |

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-26 | Initial phased plan |
| 2026-06-26 | v0.2: engineering standards (500 LOC, SOLID, DRY, tests) per phase |
| 2026-06-26 | **Phase 0 ✅ complete** — benchmark results doc 19 |
| 2026-07-02 | v0.3: Phase 1 exit criteria + re-benchmark gate и закрытие D-8; риски: prefill, R1 latency, long-utterance STT; удалена устаревшая секция «docs to add» (15–17 написаны, добавлен doc 20) |
