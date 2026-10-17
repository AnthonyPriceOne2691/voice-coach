<!-- Копия CV от 2026-10-08 из Other:Another/ANTON_ASPIDOV_CV_EN.md.
     Обновляется вручную (docs/05). Блок <style> для PDF срезан. ⚠ Где цифры расходятся с замером (2026-10-17): G connect —
     400+ тестов и 34 правила против 605 и 43 (замер 2026-10-02); Prospecting &
     outreach — 2,200+ на 10-й день против 4,670 (2026-10-08). В промпт идёт
     profile_condensed.md с измеренными числами, CV правит человек. -->

# Anton Aspidov

<p class="role">AI Delivery Lead · AI services from a bare spec to production in weeks</p>

<p class="contacts">Saint Petersburg, Russia · Remote, UTC+3 · English B1, Russian native<br>
anthonypriceone@gmail.com · Telegram @AnthonyPriceOne · linkedin.com/in/anton-aspidov<br>
Portfolio with demos: anton.aspidov.workers.dev</p>

## Profile

I lead a team of AI coding agents and the system that checks their work, taking AI services from an idea or a bare spec to production in weeks. I write the spec, set the architecture and accept the result; agents write the code, and every change must pass 22 automatic checks before it merges. My latest two services for an SEO agency went live in 8 and 14 days: 180,000+ lines of code and tests, 5,800+ automated tests and 280+ merged PRs in four weeks.

## What I bring

- **Full cycle, spec to production.** Requirements, architecture, data model, integrations, deploy and operations: MVP in a week, production in two, and a handover that describes the live system, not the plan.
- **A quality system for AI-written code.** 22 automatic checks on every change: tests, strict typing, import-layer contracts, security, ratchets that only tighten. A doctor plants a known mistake in front of each check, so a silent check counts as broken; each live failure becomes a test. Runs in 8 repos.
- **LLMs under control, not just connected.** Behavioral contracts as versioned specs: hard rules block a message, soft rules force a rewrite, checks switch live without a restart. Autonomy is earned by measurement, not trust: auto-send stays off until replays on real mail clear the bar.
- **Cost and evaluation discipline.** Pre-run estimates, fail-closed quotas and per-request cost ledgers: a three-stage funnel cut spend by 37% on a measured run. Held-out sets, predictions written before the run, golden sets behind LLM judges.
- **Private, local AI.** Ollama-based agents that never leave the laptop: a browsing research agent and a voice interviewer whose first word lands ~1.3 s after the end of your turn is detected.

## Selected work

- **LinkBuilder — outreach CRM** *(ran in production, sole engineer)*. One operator ran what took a team of five: competitor mining, site-quality gates, mass outreach, AI-drafted replies under versioned contracts, payment requests, and monitoring of 16,000+ placed links. 11,000+ backend and 700 frontend tests, 137 migrations, 20+ workers.
- **SEO case-study platform** *(production, for an SEO agency)*. Ahrefs history → classification → one-page PDF case studies. Live data in 4 days, production on day 14 against a 4–4.5-week estimate; 1,100+ tests; paid runs commit after every task, so a crash loses only in-flight requests.
- **Prospecting & outreach platform** *(donor search live, for an SEO agency)*. A GPT-5-mini site judge that quotes the page for every verdict, email-masked letter rewriting and reply-price extraction; eval gates on two of three. Live in 8 days; 100 PRs and 2,200+ tests by day 10.
- **G connect — MCP server** for Google Sheets and Drive, so coding agents can edit safely: 6 tools, 34 policy rules enforced in code, preview-first writes confirmed by plan hash, snapshot undo. Built in 8 days, 400+ tests.
- **Local Web Agent · Voice Interview Coach · RAG over a rulebook.** An on-device agent that browses real sites and backs its answers with quotes checked against the page (451 tests, open source); an offline voice interviewer with a per-sentence contract; retrieval with zero uncited answers.

## Experience

**Independent** — AI Delivery Lead for clients (self-employed) · Jul 2026 — Present · Remote

**Bookmaker Ratings** — AI Automation Engineer / Internal Tools Builder · Aug 2021 — Aug 2026 · Remote

- Built and owned LinkBuilder in production: architecture, refactor waves, human-in-the-loop design, and a handover document that describes the live state of the system, not its design.
- Built content automation: ~5× faster content preparation, ~120 hours a month saved. SEO background: grew organic traffic from 30–40K to ~180K monthly visits (Brazil, Portugal).

## Skills

**Backend:** Python, FastAPI, asyncio, SQLAlchemy 2, Pydantic, Alembic, PostgreSQL, Redis/RQ, Node.js · **Frontend:** React, TypeScript, Vite, Mantine, TanStack Query · **AI:** OpenAI API, Ollama, tool calling, MCP, behavioral contracts, HITL, evals, RAG, ASR/TTS · **AI delivery:** Claude Code, Cursor, agent specs, pre-commit gates, GitHub Actions, Docker, Playwright, pytest, Vitest, mutation testing

**Education:** Saint Petersburg State University of Service and Economics, 2014
