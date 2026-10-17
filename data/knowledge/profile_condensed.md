# Candidate Profile (condensed — injected into system prompts)

<!-- Spec: docs/05-knowledge-base.md. Budget <= 1500 tokens (doc 20), enforced by
     backend/tests/test_knowledge_profile.py. Dated measurements (portfolio #):
     #4, #5 on 2026-10-17; #2, #3 on 2026-10-08; #7 on 2026-10-02; #1 on
     2026-09-28. Where the CV disagrees, the measurement wins. -->

## Who

Anton Aspidov — **AI Delivery Lead**: takes AI services from a bare spec to production in weeks. He leads AI coding agents (Claude Code, Cursor) like a tech lead — writes the spec, sets the architecture, accepts the result — and every change must pass 22 automatic checks. Saint Petersburg, remote (UTC+3), Russian native, English B1. Aug 2021 – Aug 2026 at a sports-media company: SEO & content PM (grew organic traffic from 30–40K to ~180K visits a month), from 2024 its sole builder of internal AI tools as **AI Automation Engineer**. Changed careers: his degree is in automotive service; self-employed since July 2026.

## Now (October 2026)

- Client work for an SEO agency (NDA): a case-study platform, donor search and outreach, an email lead funnel.
- Selling AI automation to Western SEO and link-building agencies: LinkedIn and email first, then discovery calls in English.
- Looking for a remote role at a foreign company (AI Delivery Lead / Senior AI Engineer), no relocation — frame interviews for these.
- Piloting a YouTube Shorts series where he explains automation for agencies in 60 seconds.

**Why spoken English matters to him:** discovery calls with Western clients, job interviews, and voice-overs for his demo videos. Reading is ahead of speaking.

## Signature story — "I put LLMs under contract"

Every LLM action passes a runtime behavioral contract before it reaches the world, not a prompt-only rule; autonomy is earned by measurement. Second layer: private, local AI.

## Portfolio — probe any of these, not just the first

1. **LinkBuilder** — outreach CRM (ran in production, NDA, sole engineer, ~5 months): one operator instead of a team of five; 11,000+ backend and 700 front-end tests, 137 migrations, 20+ workers, 16,000+ placed links monitored; AI drafts under 10 YAML contracts, a human approves.

2. **SEO case-study platform** (agency, production since Sep 2026): live data on day 4, production on day 14 against a 4–4.5-week estimate; 1,152 tests.

3. **Prospecting & outreach platform** (agency): a GPT-5-mini judge must quote the page for every verdict; live in 8 days, 4,670 tests. With #2: 180,000+ lines and 280+ merged PRs in four weeks.

4. **Voice Interview Coach** — this very tool (local, July–October 2026): whisper.cpp → Qwen2.5 14B → Piper, ~1.3 s from end of turn to first word; buffering the full answer measured 4.8 s, so TTS streams per sentence. 213 backend + 51 front-end tests; 21 contract rules, 10 of them gate every sentence before it is spoken.

5. **Local Web Agent** — on-device research agent, open source: 451 tests, 14 hard rules in code; a claim must match a real page quote (≥0.85) or it is dropped; anti-bot is human-in-the-loop.

6. **Quality contour** — his own product: four rulebooks deployed into a repo, "only what a mechanism can reject counts"; 22 automatic checks, 16 on every commit, used in 8 repositories.

7. **G connect** — MCP server for Google Sheets, Drive and Docs (TypeScript): 6 tools, 43 policy rules in code, preview-first writes, 605 tests.

8. **RAG over a rulebook** — 680 answers over his 110K-token rulebooks, none without a file-and-section address; right section in the top 20 for 76% of 314 questions, exact match 50% — published as is.

9. **Lash Try-On** — iOS AR PoC, frozen since August 2026: lash extensions on the client's live 3D face; ARKit + custom Metal shaders, 59 fps on an iPhone 11.

10. **Event Content System** — work tool from a company hackathon: ~5× faster content prep, ~120 hours a month saved.

## How he works

Versioned design docs with numbered decisions; behavior rules in code, not prompts; a human approves anything paid or irreversible; measure before fixing; weak results are published; local models where privacy matters.

**Stack:** Python (FastAPI, asyncio, SQLAlchemy 2, Pydantic), PostgreSQL, Redis/RQ, TypeScript/React, Playwright, Ollama, whisper.cpp, Piper, OpenAI, MCP, RAG (BM25 + RRF), evals, mutation testing, GitHub Actions, Docker.

## Positioning rules

| Do | Don't |
|----|-------|
| AI delivery: spec → production, agents behind gates | "SEO lead", "link building manager" |
| Measurable impact: 5 → 1 operator, 8 and 14 days | Vague "improved efficiency" |
| Contracts, HITL, trade-offs, weak results published | Buzzwords without architecture |

SEO is secondary domain expertise — the business his tools serve, never the identity.

## Weak spots to probe

1. Live system design in English — structure under pressure.
2. Long monologues without a conclusion; openings that omit the metric.
3. Slipping into "SEO lead" framing instead of builder.
4. Pauses and fillers under follow-up pressure.
5. Defending his own numbers — ask how he counts a number he gives.
