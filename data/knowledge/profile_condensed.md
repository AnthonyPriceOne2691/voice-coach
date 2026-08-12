# Candidate Profile (condensed — injected into system prompts)

<!-- Spec: docs/05-knowledge-base.md. Budget: <= 1500 tokens (doc 20), enforced by
     backend/tests/test_knowledge_profile.py. Numbers are MEASURED against the
     repositories on 2026-08-12 unless marked "(audit 2026-07-20)". Where the CV
     disagrees, the measurement wins and the CV is the thing to update. -->

## Who

Anton Aspidov — **AI / Fullstack Product Engineer (builder)**: ships production LLM applications and internal B2B SaaS end to end, alone. Tool-calling agents, HITL workflows, async Python backends, React operator UIs, queues, integrations. Saint Petersburg, fully remote, English B2. At a sports-media company since Aug 2021; primary focus since 2024 — internal AI products in daily operator use. **Not** a chat-wrapper builder, **not** ML research.

Delivery loop he owns: plan → agent (Cursor + Claude Code) → automated gates → live scenario → human merge. Red blocks merge.

**Best-fit roles he targets:** AI / Fullstack Product Engineer (builder), LLM Application Engineer, **AI Automation Engineer**, Applied AI Engineer, Internal Tools Developer. Frame the interview for one of these.

## Signature story — "I put LLMs under contract"

One pattern, four systems: every LLM action passes a **runtime behavioral contract** (ABC, arXiv:2602.22302) *before* it reaches the world — not prompt-only. Controlled autonomy, not "GPT writes emails". Second layer: **local-first** — three of four personal projects run inference 100% on-device.

## Portfolio — probe any of these, not just the first

**1. LinkBuilder — outreach SaaS** *(production, NDA code, sole builder, ~5 months)*
SERP prospecting → CRM → AI email negotiation → payments → placement monitoring. Impact: **5-person team → 1 operator**. **7,393 test functions in 1,454 files**; ~30 Docker services (~24 RQ workers); 102 DB migrations; **17 YAML contracts** (payment whitelist, governance caps ≤25 campaigns, kill-switch, injection defense); 12,200+ emails, **97.9% delivery** on a 5,471-recipient campaign; **1,371 of 1,373 commits by one author** (audit 2026-07-20). Python/FastAPI, PostgreSQL, Redis/RQ, React/TS, OpenAI. AI drafts + human approval — not autonomous sending.

**2. Voice Interview Coach — this very tool** *(local, ~2 weeks)*
Offline voice interview: whisper.cpp → Qwen2.5 14B → Piper, **~3.0 s per turn**; buffering the full answer measured 4.8 s, so TTS streams per sentence. **93 backend + 20 frontend tests, 93% coverage**, mypy strict, ≤500 LOC/file. Contract enforcer gates **every sentence before it is spoken**; orchestrator owns interview structure, the LLM owns wording only. DeepSeek-R1 14B runs the offline summary and vocabulary bank; the two models are never loaded together (32 GB budget).

**3. Local Web Agent — on-device research agent** *(~3 weeks)*
URLs + a plain-language task → the agent browses real sites, compares them, returns a ranked report with quote evidence. **409 test functions in 116 files**, 24 design docs. Contract shield validates every action before the browser (**<10 ms**, audit 2026-07-20). Anti-hallucination: a claim must fuzzy-match a real quote (≥0.85) or it is dropped — honest `not_found` over invention. Anti-bot is **HITL**: the agent pauses, a human passes the challenge, no spoofing. Playwright + Qwen3 14B + Qwen2.5-VL.

**4. Lash Try-On — iOS AR consultation** *(~1 month, PoC, real salon in the loop)*
The client sees lash extensions on **her own live 3D face mesh** before the procedure. ARKit mesh + MediaPipe landmarks; SceneKit scene graph with **custom Metal shaders** after SceneKit hit an image-quality ceiling. **59 fps on an iPhone 11** (audit 2026-07-20); 48 Swift files, 24 design docs. A local vision-LLM critic under contract proposes bounded parameter tweaks — **a human applies them**. No automated tests: validated by an expert rubric with the salon master.

**5. Event Content System + SEO:Content Toolkit** *(work, Node.js/React)*
Match ingest → cover generation → AI image QA → operator CMS. **~5× faster** content prep, **~120 hours/month** saved at ~900 units/month.

## Stack keywords

Python, FastAPI, asyncio, SQLAlchemy 2.0 async, Pydantic, PostgreSQL, Redis/RQ, Node.js, React, TypeScript, Playwright, Swift, ARKit, Metal, OpenAI function calling, local LLMs (Ollama), structured outputs, HITL, evals, golden/replay scenarios, prompt injection defense, Docker, GitLab CI/CD, GitHub Actions, pytest, Vitest.

## Positioning rules

| Do | Don't |
|----|-------|
| Builder / automation engineer, internal tools, LLM apps | "SEO lead", "link building manager" |
| Measurable impact: 5 FTE → 1, ~120 h/month, 97.9% delivery | Vague "improved efficiency" |
| HITL, queues, contracts, bounded autonomy, trade-offs | Buzzwords without architecture |
| Name what failed and why (SceneKit ceiling, 4.8 s buffering) | Only success stories |

SEO/content is **secondary domain expertise** — the business the tools serve, never the identity.

## Weak spots to probe

1. Live system design in English — structure under pressure.
2. Long monologues without a conclusion; openings that omit the metric.
3. Slipping into "SEO lead" framing instead of builder/automation.
4. Pauses and fillers under follow-up pressure.
5. **Defending his own numbers.** His CV understates LinkBuilder (says 4,200+ tests; the repository has 7,393) and Local Web Agent (380 vs 409). Ask what the number is and how he counts it — a builder should know his own systems better than his résumé does.
