<!-- Копия CV от 2026-08-11 из Other:Another/ANTON_ASPIDOV_CV_EN.md.
     Обновляется вручную (docs/05). Блок <style> для PDF срезан.
     ⚠ Часть цифр здесь ЗАНИЖЕНА против замера по репозиториям
     (LinkBuilder 4,200+ против 7,393; Local Web Agent 380 против 409).
     В промпт идёт profile_condensed.md с измеренными числами. -->

# Anton Aspidov

**AI / Fullstack Product Engineer (Builder) · LLM Applications · Internal Tools**

Saint Petersburg, Russia · Fully remote · MSK daytime overlap  
Telegram: `@AnthonyPriceOne` · Email: `anthonypriceone@gmail.com` · LinkedIn: `linkedin.com/in/anton-aspidov/` · English B2 · Russian Native

## Profile

Sole builder shipping **AI products from idea to production** — not “I know Cursor,” but systems operators use every day. Production LLM apps and internal B2B SaaS: tool-calling agents, HITL workflows, CRM platforms, async Python backends, React UIs, queues, and integrations.

**How I build with AI:** plan → agent (Cursor + Claude Code) → automated gates → live scenario → human merge. I own architecture, priorities, and production; the agent accelerates implementation under mechanical checks (style, types, size, secrets, tests). Red blocks merge.

**Best-fit roles:** AI / fullstack product engineer (builder), LLM Application Engineer, AI Automation Engineer, Applied AI Engineer, Internal Tools Developer.

## Highlights

- **Sole builder** of a production outreach SaaS: **5-person team → 1 operator** in ~**5 months** from zero to daily use; **~16k donors / ~15k links** under monitoring; **4,200+ tests**, diff-coverage ≥70%, red blocks merge.
- Shipped **production domain agents** (prospecting, competitors, mass outreach, email AI) with tool catalogs, behavioral gates, scheduled autonomy, and HITL on deal-critical steps.
- **Local Web Agent** (~3 weeks): multi-site research agent on-device — tool-calling + browser actions, HITL on CAPTCHA/login, **380 tests**, live-site findings turned into fixtures.
- **Voice Interview Coach** (~2 weeks): local ASR → LLM → TTS loop under a **~3 s/turn** latency budget; exam + review modes.
- **Lash Try-On** (~1 month, iOS): custom **Metal** renderer after SceneKit hit an image-quality ceiling; accepted with salon master on device.
- Cut content preparation **~5×** (10 → 2 min/unit); **~120 hours/month** saved at ~900 units/month.

## Professional Experience

### Bookmaker Ratings

**AI Automation Engineer / Fullstack Internal Tools Builder**  
*(within SEO & Content Project Manager role)*  
August 2021 — Present · Remote

Primary focus since 2024–2025: designing and shipping internal products for outreach, content, and SEO operations. Most tools are live in daily operator use.

- **Sole builder** of **LinkBuilder** (internal outreach SaaS): architecture, HITL design, refactor waves (V1→V3), production ownership — SERP prospecting → outreach CRM → payments → placement monitoring.
- Built **domain AI agents** (Competitors, Mass Outreach, Email AI): OpenAI tool-calling loops, read/action tools, behavioral contracts per action, operator memory, autonomous scheduler; ambiguous / money cases → human.
- Enforced agent-friendly code discipline: hard **~500-line file limit**, feature modules, ratchet quality — so agents do not sprawl across the monolith.
- Built **Event Content System** — Node.js pipeline + React CMS for sports/event content: match ingest, visual generation, AI image QA, run logs.
- Built **SEO:Content Automation Toolkit** — plugin-style CLI pipelines for Google Workspace, SEO metadata, editorial QA, Telegram notifications.
- Stack: Python/FastAPI, asyncio/async SQLAlchemy, PostgreSQL, Redis/RQ, Node.js, React/TypeScript, Vite, Mantine, Docker, GitLab CI/CD. Daily build tools: **Cursor + Claude Code**; production LLM: OpenAI API.
- Integrations: OpenAI, SendGrid, DataForSEO, Hunter, Ahrefs, Google Workspace APIs, SofaScore, Telegram Bot API.

**Measurable impact**

- Link building ops: **5 FTE → 1 specialist** with internal SaaS + automation.
- Content pipelines: **~80% less manual work** per unit; **~120 hours/month** saved.
- SEO (domain context): organic traffic ~30–40K → ~180K monthly visits (Ahrefs) for Brazil/Portugal markets.

## Selected Projects

### LinkBuilder — Internal Outreach Platform *(production · sole builder · ~5 mo · NDA code)*

End-to-end B2B SaaS: prospecting, CRM threads/campaigns, email AI, monitoring. Operators run the portfolio from one screen instead of inbox + spreadsheet chaos.

**Stack / quality:** Python/FastAPI, React/TypeScript, PostgreSQL, Redis/RQ, OpenAI · **4,200+** backend tests, 280+ frontend tests, mypy strict, CI gates, diff-coverage ≥70%.

**Scale & modules:** ~16k donors · ~15k links monitored · auto prospecting (up to ~600 keywords / hundreds of candidates per run) · placement monitoring · competitor gap analysis · mass outreach copilot · email AI (draft / classify / HITL / autosend with injection defense).

**Agent pattern:** deterministic core + LLM at boundaries; tool-calling loops; bounded autonomy (`propose` → `auto`); Agent Behavioral Contracts (YAML guardrails, budgets, audit trail).

### Local Web Agent — On-device research agent *(~3 weeks)*

URLs + plain-language task → agent browses, compares, reports. **Zero data egress** — runs on Mac with local LLMs.

- **6** research tools + browser actions (tool-calling, not one giant prompt); HITL on CAPTCHA and login.
- Live-site bugs → tests: **7/9** findings closed with fixtures; **380 tests**.
- **Stack:** FastAPI, React, Playwright, local LLMs.

### Voice Interview Coach *(~2 weeks)*

Local voice interview trainer: **ASR → LLM → TTS** under a **~3 s** turn budget (~0.7 s ASR + ~1.8 s LLM + ~0.5 s TTS). Exam mode + review-together mode; recordings and models stay on machine.

- **Stack:** FastAPI, React, Ollama, whisper, Piper. Verified via latency benchmark + e2e smoke.

### Lash Try-On — iOS salon try-on *(~1 month)*

Client sees lashes on her own face before the procedure. Off-the-shelf SceneKit hit a quality ceiling (MSAA, transparency, custom passes) → **custom Metal** pipeline for try-on realism; acceptance with salon master on iPhone.

- **Stack:** Swift, ARKit, Metal. Same AI-assisted delivery loop (plan → implement → on-device smoke).

### Event Content System

Sports/event content automation: match data → covers → AI image QA → operator CMS. Node.js + React; **~5×** faster content prep.

### SEO:Content Automation Toolkit

Node.js plugin-style CLI for Google Workspace, SEO metadata, editorial QA, Telegram bots — foundation for later Event Content and LinkBuilder modules.

## Technical Skills

**Backend & Automation:** Python, FastAPI, asyncio, SQLAlchemy 2.0 async, Pydantic, Alembic, PostgreSQL, Redis/RQ, Node.js, Express, REST, CLI pipelines, background workers.  
**Frontend:** React, TypeScript, Vite, Mantine, Tailwind, TanStack Query/Table, React Router.  
**AI / LLM / Agents:** OpenAI API, local LLMs (Ollama), tool calling / function calling, agent orchestration, HITL, structured outputs, evals, golden/replay scenarios, Agent Behavioral Contracts, prompt injection defense, voice loops (ASR/TTS).  
**AI-assisted delivery:** Cursor, Claude Code — plan / implement / gates / live / human merge.  
**Browser & mobile:** Playwright, Swift, ARKit, Metal.  
**Architecture:** service layer, feature modules, internal tools, B2B SaaS, CRM.  
**Infrastructure & quality:** Docker, GitLab CI/CD, VPS, pytest, Vitest, contract/replay tests, diff-coverage gates.  
**Integrations:** SendGrid, DataForSEO, Hunter, Ahrefs, Google Workspace APIs, SofaScore, Telegram Bot API.

## Domain Expertise (secondary)

SEO strategy, keyword clustering, technical/on-page SEO, GA4, GSC, Ahrefs, editorial ops, multilingual team coordination (up to 20 writers), Brazil/Portugal/LATAM markets.

## Education

Saint Petersburg State University of Service and Economics — Degree completed in 2014.
