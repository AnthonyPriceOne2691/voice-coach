<style>
@page {
  margin: 0.55in 0.65in;
}
body {
  color: #111;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 10pt;
  line-height: 1.25;
}
h1 {
  font-size: 20pt;
  margin-bottom: 0.1rem;
}
h2 {
  border-bottom: 1px solid #ddd;
  font-size: 12pt;
  margin: 0.75rem 0 0.25rem;
  padding-bottom: 0.1rem;
}
h3 {
  font-size: 10.5pt;
  margin: 0.55rem 0 0.15rem;
}
p {
  margin: 0.2rem 0 0.35rem;
}
ul {
  margin: 0.15rem 0 0.35rem;
  padding-left: 1.1rem;
}
li {
  margin-bottom: 0.12rem;
}
p, li, h1, h2, h3 {
  -webkit-hyphens: none;
  hyphens: none;
  overflow-wrap: normal;
  word-break: normal;
}
</style>

# Anton Aspidov

**LLM Application Engineer · AI Agent / Automation Engineer · Fullstack Internal Tools Builder**

Saint Petersburg, Russia · Open to remote / contract  
Telegram: `@AnthonyPriceOne` · Email: `anthonypriceone@gmail.com` · LinkedIn: `linkedin.com/in/anton-aspidov/` · English B2 · Russian Native

## Profile

Fullstack engineer building **production LLM applications** and **internal B2B SaaS**: domain AI agents, tool-calling loops, workflow automation, CRM platforms, async Python backends, React operator UIs, job queues, and third-party integrations. I ship **applied AI systems** — not chat wrappers or ML research — with human-in-the-loop, structured outputs, evals, audit trails, and measurable business impact.

**Core practice:** modular **domain agents** inside a monolith — OpenAI **function calling** / tool-use loops (read + action tools), **agent orchestration** with bounded autonomy (`propose` → `auto`), **Agent Behavioral Contracts** (YAML runtime guardrails on every action), deterministic scoring cores with LLM only at pipeline gates, and **4,200+ tests** on internal products.

**Best-fit roles:** AI Automation Engineer, LLM Application Engineer, Applied AI Engineer, AI Workflow Engineer, Internal Tools Developer, Agentic AI Engineer (production systems).

## Highlights

- Built a production internal SaaS that reduced a **5-person outreach team to 1 operator** with CRM, queues, domain AI agents, and AI-assisted email workflows.
- Shipped **production module agents** (Competitors, Mass Outreach) with tool catalogs, ABC gates, autonomous scheduled runs, and operator chat surfaces — beyond email bots.
- Cut content preparation time **~5×** (10 min → 2 min per unit); **~120 hours saved monthly** at ~900 units/month.
- **4,200+ backend tests**, contract/replay/golden scenarios, strict typing, CI/CD — engineering discipline on AI-powered internal products.
- Designed reusable **Agent Behavioral Contracts** engine (preconditions, invariants, governance, recovery, drift) for safe LLM autonomy in production.

## Professional Experience

### Bookmaker Ratings

**AI Automation Engineer / Fullstack Internal Tools Builder**  
*(within SEO & Content Project Manager role)*  
August 2021 — Present · Remote

Primary focus since 2024–2025: designing and shipping internal products for outreach, content, and SEO operations. Most tools are live MVPs in daily use.

- Architected and built **LinkBuilder SaaS** — end-to-end B2B platform with **multi-module AI agents**: SERP prospecting → outreach → payment tracking → placement monitoring (see Selected Projects).
- Built **domain AI agents** (Competitors, Mass Outreach): OpenAI tool-calling loops, read/action tool catalogs, ABC behavioral gates per action, operator memory, autonomous scheduler runs.
- Built **Event Content System** — Node.js pipeline + React CMS for sports/event content: match ingest, visual generation, AI image QA, run logs, operator workflows.
- Built **SEO:Content Automation Toolkit** — plugin-style CLI pipelines for Google Workspace, SEO metadata, editorial QA, and Telegram notifications.
- Implemented **LLM application workflows**: classification, structured JSON extraction, reply generation, hybrid rules+LLM pipeline gates, self-check quality gates, draft/autosend, prompt injection defense.
- Stack: Python/FastAPI, **asyncio**/async SQLAlchemy, PostgreSQL, Redis/RQ, Node.js, React/TypeScript, Vite, Mantine, Docker, GitLab CI/CD.
- Integrated OpenAI API, SendGrid (outbound + inbound webhooks), DataForSEO, Hunter, Ahrefs, Google Workspace APIs, SofaScore, Telegram Bot API.
- Documented production policies: AI autonomy rules, deployment checklists, security notes, runbooks, replay/golden scenarios, and agent design specs.

**Measurable impact**

- Link building ops: **5 FTE → 1 specialist** with internal SaaS and automation layer.
- Content pipelines: **~80% less manual work** per unit; **~120 hours/month** saved at current volume.
- SEO (domain context): grew organic traffic from ~30–40K to ~180K monthly visits (Ahrefs) for Brazil/Portugal markets.

## Selected Projects

### LinkBuilder SaaS — Outreach & Link-Building Automation Platform

Production internal B2B SaaS. Goal: complete outreach-to-placement cycle with minimal human involvement (approval, not manual execution). Deployed on VPS with Docker; feature-layered backend (`features/{api,services,repository,models}`), service layer, strict typing, pre-commit hooks.

**Stack:** Python 3.14, FastAPI, async SQLAlchemy, Alembic, Pydantic, React/TypeScript (Vite, Mantine), PostgreSQL, Redis/RQ, Docker. **Quality:** 4,200+ backend tests (~74% coverage), 280+ frontend tests, mypy strict, ruff/eslint.

**Modules:**
- **Core** — CRM: projects, donors, links, contacts, stop-lists, campaigns, incidents, Excel import, dashboard.
- **Prospecting** — SERP via DataForSEO, mass RQ jobs, scoring gates (stop-list, purchase history, Ahrefs), keyword-cluster base collection.
- **Monitoring** — placement checks (anchor, HTTP, noindex, canonical, sponsored, sitemap); mass runs up to 5,000 links (dedicated queue, browser pool, cancel/progress in CMS).
- **Competitors** — auto-discovery, crawl, donor gap analysis; hybrid rules + LLM classification gates; **production domain agent** (tool-use loop, autonomous review/crawl orchestration).
- **Mass Outreach** — campaign lifecycle, bulk sends, analytics; **operator copilot agent** (read-tools Q&A + action-tools via ABC gate).
- **Email AI** — outbound/inbound outreach: letter generation, reply classification, condition extraction, payment requests, scheduled follow-ups; 30+ versioned prompts; multilingual threads.

**Domain agent architecture (Pattern B — LLM as operator over deterministic core):**
- **Tool calling / ReAct-style loops:** OpenAI function calling, read-tools (DB-grounded facts) + action-tools (mutations via same APIs as UI), multi-hop agent loop, numeric grounding verifier (model cannot invent stats).
- **Agent orchestration:** Q&A mode, operator chat, scheduled autonomous runs (`propose` / `auto`), money-actions behind confirmation, operator preference memory.
- **Agent Behavioral Contracts (ABC):** reusable YAML contract engine — preconditions, hard/soft invariants, governance budgets (Ahrefs/tokens), recovery loop, drift detection, audit trail on every agent action.
- **LLM-in-pipeline gates (Pattern A):** site-type classifier, hybrid anchor classifier (rules → LLM batch → lexicon fallback); deterministic niche/affiliate scoring ($0 embeddings) in the core.

**Email AI layer:** classify → generate → ABC evaluator → draft / autosend / HITL; prompt injection defense on inbound mail.

**Integrations:** DataForSEO, Hunter, SendGrid, Ahrefs, OpenAI, payment/CRM handoff.

**Portfolio (open):** `private-ai-knowledge-assistant` — RAG, tool calling, LangGraph labs, evals, tracing, ABC patterns (shareable demo codebase).

### Event Content System

Sports/event content automation: match data → prediction covers → news image selection → AI QA → operator CMS.

- Node.js pipeline, Express API, React/Vite/Tailwind CMS; Google Docs/Sheets, SofaScore, OpenAI, Puppeteer, Sharp, Docker, GitLab CI/CD.
- OpenAI image relevance checks with strict mode, confidence thresholds, and documented QA contract.
- **Impact:** ~5× faster content prep; reproducible, auditable operator workflows.

### SEO:Content Automation Toolkit

Node.js toolkit: Google Workspace automation, SEO metadata collection, editorial QA, sports visuals, Telegram bots.

- Plugin-style actions, presets, retry/backoff; rule-based + AI hybrid QA for editorial documents.
- Foundation that evolved into Event Content System and LinkBuilder modules.

## Technical Skills

**Backend & Automation:** Python, FastAPI, asyncio, SQLAlchemy 2.0 async, Pydantic, Alembic, PostgreSQL, Redis/RQ, Node.js, Express, REST API, CLI pipelines, background workers, job queues.  
**Frontend:** React, TypeScript, Vite, Mantine, Tailwind, TanStack Query/Table, React Router.  
**AI / LLM / Agents:** OpenAI API, LLM application development, agent orchestration, AI agents, tool calling, function calling, structured outputs, JSON Schema tools, prompt engineering, human-in-the-loop (HITL), quality gates, evals, golden/replay scenarios, Agent Behavioral Contracts, guardrails, prompt injection defense, workflow automation, business process automation.  
**Agent patterns (production):** domain agents, read/action tool catalogs, ReAct-style multi-hop loops, bounded autonomy, deterministic core + LLM at boundaries, audit/tracing of agent decisions.  
**AI / LLM (portfolio & learning):** RAG, embeddings, vector search, LangGraph, multi-agent workflows, tool-use primitives.  
**Architecture:** OOP, SOLID, service layer, feature modules, design patterns, internal tools, B2B SaaS, CRM platforms.  
**Infrastructure:** Docker, Docker Compose, GitLab CI/CD, VPS deploy, nginx, runbooks.  
**Testing:** pytest, pytest-asyncio, Vitest, API tests, contract tests, agent QA eval harnesses, httpx.  
**Integrations:** SendGrid, DataForSEO, Hunter, Ahrefs, Google Workspace APIs, SofaScore, Telegram Bot API.

## Domain Expertise (secondary)

SEO strategy, keyword clustering, technical/on-page SEO, GA4, GSC, Ahrefs, editorial ops, multilingual team coordination (up to 20 writers), Brazil/Portugal/LATAM markets, competitive content niches.

## Education

Saint Petersburg State University of Service and Economics — Degree completed in 2014.
