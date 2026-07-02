# Portfolio Case Study: Internal B2B Outreach Automation Platform

> **Anonymized case study** for portfolio, interviews, and LinkedIn.  
> No company names, domains, or proprietary data.  
> Author: Anton Aspidov · 2024–2026

---

## One-liner

Production internal SaaS that automates end-to-end link-building outreach — from SERP prospecting to AI-assisted email negotiation and placement monitoring — reducing a **5-person team to 1 operator**.

---

## Problem

A growth team ran link-building outreach manually:

- Prospects found in spreadsheets and ad-hoc SERP checks
- Email threads tracked in inboxes without CRM context
- Inbound replies handled one-by-one; inconsistent tone and missed follow-ups
- Placement quality checked manually, link by link
- No audit trail, no scoring gates, no safe path to AI-assisted replies

**Cost:** ~5 FTE, slow cycle time, high error rate on donor matching and reply handling.

---

## Solution

A modular internal B2B platform with four product areas and a shared CRM core.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Operator CMS (React/TS)                      │
└────────────┬──────────────┬──────────────┬──────────────┬───────┘
             │              │              │              │
      ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐ ┌─────▼─────┐
      │    Core     │ │Prospecting│ │ Monitoring  │ │AI Agents  │
      │    CRM      │ │  + SERP   │ │  + checks   │ │+ outreach │
      └──────┬──────┘ └─────┬─────┘ └──────┬──────┘ └─────┬─────┘
             │              │              │              │
             └──────────────┴──────┬───────┴──────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  FastAPI + PostgreSQL   │
                    │  Redis/RQ job queues    │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
        DataForSEO          SendGrid            OpenAI
        Hunter              (in+out)            Ahrefs
```

---

## Architecture decisions

| Decision | Rationale |
|----------|-----------|
| Feature-layered backend (`api → services → repository → models`) | Clear boundaries; 4,200+ tests; safe refactors |
| Separate RQ queues (`inbound`, `openai`, `monitoring`) | Isolate latency-heavy AI and browser work from API |
| Prompts as versioned `.md` artifacts | Reviewable, diffable, not buried in code |
| Agent Behavioral Contracts (YAML) | Formal guardrails before autosend |
| Idempotent inbound processing | Webhook retries must not duplicate AI runs |
| HITL by default, autosend behind flags | Safe rollout of LLM autonomy |

---

## Module breakdown

### 1. Core CRM

- Projects, donors, links, contacts, stop-lists, campaigns, incidents
- Excel import, role-based access, dashboard
- Single source of truth for all downstream modules

### 2. Prospecting

- Keyword clusters → SERP runs (DataForSEO) → scoring gates
- Gates: stop-list, prior purchases, Ahrefs metrics, geo/topic signals
- Mass runs via RQ with progress/cancel in CMS
- Batch sizes: **1,000+ donors per run** in production

### 3. Monitoring

- Automated placement checks: anchor, HTTP status, noindex, canonical, sponsored tags, sitemap presence
- Mass checks up to **5,000 links** per run
- Dedicated queue + browser pool for headless checks

### 4. AI Agents (outreach)

**Outbound:** template-based first touch, situation-aware follow-ups.

**Inbound pipeline** (orchestrated, not chat):

```
SendGrid webhook
    → persist inbound reply
    → RQ job: match donor (Message-ID → thread → subject → contact)
    → classify situation (LLM + structured JSON)
    → extract conditions (price, format, deadlines)
    → generate negotiation reply
    → quality self-check
    → ABC evaluator (behavioral contract)
    → draft in CRM  OR  autosend (if policy allows)
```

**Safety layer:**
- Confidence thresholds per situation type
- `needs_human` flag on ambiguous inbound
- Prompt injection defense on untrusted email bodies
- Payment whitelist — AI cannot commit to unauthorized terms
- Max auto-rounds per thread before mandatory human review

---

## Agent Behavioral Contracts (ABC)

Custom approach to LLM reliability in production:

- **Preconditions** — what must be true before the agent runs (campaign state, donor bound, language detected)
- **Invariants** — hard rules (no payment promises outside whitelist, no PII leakage, reply language matches thread)
- **Detectors** — regex, composite, language, optional LLM-judge
- **Golden scenarios** — replay tests on fixed inputs; regression before deploy
- **Canary / enforce modes** — log violations first, then block autosend

This is the differentiator: **controlled autonomy**, not "GPT writes emails."

---

## Integrations

| Service | Role |
|---------|------|
| SendGrid | Outbound mail + inbound webhook parsing |
| OpenAI | Classification, generation, self-check |
| DataForSEO | SERP prospecting |
| Hunter | Contact enrichment |
| Ahrefs | Domain metrics for scoring gates |
| Internal payment CRM | Handoff for approved transactions |

---

## Engineering quality

- **4,200+ backend tests** (~74% coverage), 280+ frontend tests
- mypy strict, ruff, eslint, pre-commit hooks
- ADRs, runbooks, deployment checklist, security review
- GitLab CI/CD → Docker on VPS
- Documented AI autonomy policy and operator FAQ

---

## Business impact

| Metric | Before | After |
|--------|--------|-------|
| Outreach team size | ~5 FTE | 1 specialist + platform |
| Donor prospecting | Manual spreadsheets | Batch SERP runs with gates |
| Inbound reply handling | Manual, inconsistent | Classified + drafted/sent with audit trail |
| Placement QA | Spot checks | Mass automated monitoring |

---

## My role

Sole builder / product engineer for the platform:

- Requirements from operators → architecture → implementation → deploy
- Fullstack: FastAPI backend, React CMS, RQ workers, Docker
- AI pipeline design: prompts, contracts, HITL policy, eval scenarios
- Ongoing iteration: mass outreach copilot, competitor discovery agents

---

## Stack summary

**Backend:** Python 3.14, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic  
**Frontend:** React 19, TypeScript, Vite, Mantine, TanStack Query  
**Data:** PostgreSQL, Redis, RQ  
**AI:** OpenAI API, structured outputs, behavioral contracts  
**Ops:** Docker Compose, GitLab CI/CD, VPS, nginx  

---

## What I'd show in an interview (without code access)

1. **Architecture diagram** (above) — 2 min walkthrough
2. **Inbound AI pipeline** — classify → generate → gate → send/draft
3. **ABC example** — one YAML contract + one golden scenario
4. **Metrics** — 5→1 team, test count, batch sizes
5. **Trade-off story** — why separate queues, why HITL first, how donor matching avoids wrong-site placements

---

## Public companion project

[Private AI Knowledge & Workflow Assistant](private-ai-knowledge-assistant/) — open portfolio repo demonstrating RAG, tool calling, evals, tracing, and ABC patterns in a shareable codebase.

---

## Screenshots checklist (for PDF/portfolio)

- [ ] CRM dashboard (data redacted)
- [ ] Prospecting run progress UI
- [ ] Inbound reply with AI draft + confidence score
- [ ] Monitoring mass-check results table
- [ ] ABC contract violation log (synthetic example)

---

*Last updated: 2026-06-24*
