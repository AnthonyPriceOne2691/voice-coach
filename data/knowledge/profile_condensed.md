# Candidate Profile (condensed — injected into system prompts)

<!-- Spec: docs/05-knowledge-base.md. Budget: <= 1500 tokens. -->
<!-- Maintain manually: refresh after editing ANTON_ASPIDOV_CV_EN.md or PORTFOLIO_LINKBUILDER_CASE.md (copies in this folder). -->

## Positioning (one-liner)

Anton Aspidov — **AI Automation Engineer / LLM Application Engineer / Fullstack Internal Tools Builder**. Ships production LLM applications and internal B2B SaaS: domain AI agents with tool-calling loops, HITL workflows, behavioral contracts, async Python backends, React operator UIs. NOT a chat-wrapper builder, NOT ML research. English B2, targeting remote/contract roles abroad.

## Flagship projects (with metrics)

1. **LinkBuilder SaaS** — internal B2B outreach automation platform (sole builder). SERP prospecting → AI-assisted email negotiation → placement monitoring. Reduced a **5-person team to 1 operator**. Stack: Python/FastAPI, async SQLAlchemy, PostgreSQL, Redis/RQ, React/TS. **4,200+ backend tests (~74% coverage)**, mypy strict. Separate RQ queues for inbound mail, OpenAI calls, and monitoring (isolate latency-heavy work from API). Monitoring: mass checks up to 5,000 links per run; prospecting: 1,000+ donors per batch.

2. **Inbound AI pipeline** (part of LinkBuilder) — orchestrated, not chat: SendGrid webhook → donor matching → LLM classification (structured JSON) → condition extraction → reply generation → quality self-check → **ABC evaluator → draft OR autosend**. Safety: confidence thresholds, `needs_human` flag, prompt injection defense on untrusted email bodies, payment whitelist, max auto-rounds before mandatory human review. Idempotent webhook processing.

3. **Agent Behavioral Contracts (ABC)** — reusable YAML guardrail engine for LLM autonomy in production: preconditions, hard/soft invariants, governance budgets, recovery, drift detection, audit trail on every agent action. Golden/replay scenarios for regression; canary → enforce rollout. The differentiator: **controlled autonomy**, not "GPT writes emails."

Secondary: Event Content System (~5x faster content prep, ~120 hours/month saved); domain agents (Competitors, Mass Outreach) with read/action tool catalogs and bounded autonomy (`propose` → `auto`).

## Tech stack keywords

Python, FastAPI, asyncio, SQLAlchemy 2.0 async, Pydantic, PostgreSQL, Redis/RQ, Node.js, React, TypeScript, OpenAI function calling, structured outputs, ReAct-style loops, HITL, evals, golden scenarios, prompt injection defense, Docker, GitLab CI/CD, pytest.

## Positioning rules

| Do | Don't |
|----|-------|
| Automation engineer, internal tools, LLM apps | "SEO lead", "link building manager" |
| Measurable impact: 5 FTE → 1, ~120 h/month saved, 4,200+ tests | Vague "improved efficiency" |
| HITL, queues, behavioral contracts, bounded autonomy | Buzzwords without architecture |
| Trade-offs and failures (why HITL first, why separate queues) | Only success stories |

SEO/content background is **secondary domain expertise**, mention only as the business domain the tools serve.

## Weak spots to probe (interviewer: push on these)

1. Live system design in English — structure under pressure.
2. Long monologues without a conclusion; missing metrics in openings.
3. Slipping into "SEO lead" framing instead of builder/automation angle.
4. Pauses and fillers under follow-up pressure.

## Trade-off stories worth probing

- Why separate RQ queues for inbound vs OpenAI vs monitoring.
- HITL by default vs autosend behind flags — safe LLM autonomy rollout.
- Donor matching design (Message-ID → thread → subject → contact) and how it avoids wrong-site placements.
- Deterministic scoring core with LLM only at pipeline gates ($0 embeddings decision).
