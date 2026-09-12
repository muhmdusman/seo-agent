<div align="center">

# Search Console Agent

**An agentic SEO growth system that turns Google Search Console data into a prioritized, evidence-backed action plan.**

Built on Strands Agents with a skill-driven analysis framework, Celery + Redis background workers, and automated email delivery.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](backend/.python-version)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white)](backend/docker-compose.yaml)

[Live Demo](https://main.d3vozze6u0rukp.amplifyapp.com/) · [Repository](https://github.com/muhmdusman/seo-agent)

</div>

---

## Overview

Most SEO tooling stops at reporting. You get a dashboard full of impressions, clicks, and average position, and you are still left deciding what to actually fix this week.

Search Console Agent closes that gap. It connects to a site's verified Google Search Console property, pulls real performance and sitemap data, crawls the pages behind it, and runs the combined signal through an LLM agent that follows a **structured 9-stage SEO framework** rather than free-associating. The output is a Markdown report scoped to the site's size and the owner's stated goal, plus a short summary that is persisted so the next run knows what was already covered.

Two execution paths share the same agent layer:

- **Interactive** — the dashboard streams an on-demand analysis over Server-Sent Events, with live progress as each stage completes.
- **Scheduled** — a Celery worker pool generates daily digests for every connected site and emails them, driven by queued jobs rather than in-request work.

### Who it's for

| Audience | Value |
|---|---|
| Solo founders and indie makers | SEO direction without hiring a consultant or learning the discipline first |
| Small agencies | Repeatable, evidence-backed audits across a client roster, delivered on a schedule |
| In-house marketers | A weekly shortlist of what to fix, prioritized against a business goal |
| Developers | Every finding ships with a copy-paste agent prompt, so fixes can be handed straight to a coding assistant |

---

## Features

**Agentic analysis**
- Strands Agents orchestration with tool calling over Google Search Console, sitemap crawling, user credentials, and historical reports
- A dedicated SEO skill definition (`backend/system-prompt/SKILL.md`) encoding a 9-stage framework across four groups: Foundation, Content Layer, Relevance Layer, and AI/GEO frontier
- **Bounded scope per run.** Site size maps to a tier (Micro through Enterprise) that caps how many stages and pages a single run may touch, which keeps tool-call volume predictable and stops the model from inventing findings to fill space
- **History as context.** Past report summaries are exposed to the agent through a database-backed tool, so successive runs build on prior work instead of repeating it
- Goal-weighted prioritization — the same technical finding ranks differently for *increase conversions* than for *build topical authority*

**Data collection**
- Google OAuth 2.0 with the `webmasters.readonly` scope; per-user tokens stored server-side
- Parallel Search Console snapshot across queries, pages, devices, countries, daily performance, and submitted sitemaps
- Sitemap-driven crawler extracting title, meta description, canonical, and heading structure per page

**Background processing**
- Celery workers with Redis as broker, retry backoff, and a `jobs` table tracking `queued → processing → completed / failed` with attempt counts and error messages
- Fan-out scheduling: one job per user-site pair, so a slow site never blocks the rest
- HTML email delivery over SMTP with Markdown-to-HTML rendering

**Interface**
- Next.js 16 App Router dashboard with real-time SSE streaming of agent progress
- Site picker sourced from the user's verified Search Console properties
- Markdown report rendering with GFM tables

---

## Tech Stack

<div align="center">

**Backend**

![Python](https://img.shields.io/badge/Python%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy%202-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-6BA81E?style=for-the-badge&logo=alembic&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![uv](https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=uv&logoColor=white)

**Queue & Data**

![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-FF4438?style=for-the-badge&logo=redis&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL%2017-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**AI & Agents**

![Strands Agents](https://img.shields.io/badge/Strands%20Agents-232F3E?style=for-the-badge&logo=probot&logoColor=white)
![LiteLLM](https://img.shields.io/badge/LiteLLM-4B0082?style=for-the-badge&logo=litellm&logoColor=white)
![Mistral AI](https://img.shields.io/badge/Mistral%20AI-FA520F?style=for-the-badge&logo=mistralai&logoColor=white)
![Google Search Console](https://img.shields.io/badge/Search%20Console-458CF5?style=for-the-badge&logo=googlesearchconsole&logoColor=white)

**Frontend**

![Next.js](https://img.shields.io/badge/Next.js%2016-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React%2019-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript%205-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS%204-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Radix UI](https://img.shields.io/badge/Radix%20UI-161618?style=for-the-badge&logo=radixui&logoColor=white)

**Runtime**

![Docker Compose](https://img.shields.io/badge/Docker%20Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white)
![Gunicorn](https://img.shields.io/badge/Supervisord-2C5BB4?style=for-the-badge&logo=linux&logoColor=white)

</div>

| Layer | Choice | Why |
|---|---|---|
| Agent runtime | **Strands Agents** + LiteLLM | Model-agnostic tool calling with a thin, inspectable loop. Replaced an earlier LangGraph implementation, whose graph abstraction added ceremony without buying anything for a linear, tool-driven pipeline |
| Model | Mistral Small (`temperature=0`) via LiteLLM | Deterministic-leaning output at low cost; the LiteLLM layer keeps a switch to another model provider a config change rather than a rewrite |
| Queue | **Celery + Redis** | Report generation takes minutes and calls third-party APIs. Moving it off the request path gives retries with backoff, per-job status, and horizontal worker scaling |
| API | FastAPI + async SQLAlchemy | Native async suits an I/O-bound workload dominated by Google API and HTTP crawl latency |
| Transport | Server-Sent Events | One-way progress streaming without WebSocket overhead |
| Frontend | Next.js 16 + Tailwind 4 | App Router with server-rendered shell and a streaming client dashboard |

---

## Architecture

```
                          ┌────────────────────────────┐
                          │   Next.js 16 Frontend      │
                          │   Dashboard · SSE client   │
                          └─────────────┬──────────────┘
                                        │  HTTPS / Bearer JWT
                          ┌─────────────▼──────────────┐
                          │  FastAPI Service           │
                          │  /auth  /search-console    │
                          │  /agent  /scheduler        │
                          └──┬──────────────────────┬──┘
                             │                      │
         interactive path    │                      │   scheduled path
         (SSE stream)        │                      │   (enqueue only)
                             │                      ▼
                             │            ┌────────────────────┐
                             │            │  Redis  (broker)   │
                             │            └─────────┬──────────┘
                             │                      │
                             │            ┌─────────▼──────────┐
                             │            │  Celery Worker     │
                             │            │  retry + backoff   │
                             │            └─────────┬──────────┘
                             │                      │
                    ┌────────▼──────────────────────▼────────┐
                    │           Agent Layer (Strands)         │
                    │  WeeklyAgent · DailyAgent               │
                    │  ┌───────────────────────────────────┐  │
                    │  │ SKILL.md — 9-stage SEO framework  │  │
                    │  └───────────────────────────────────┘  │
                    │  Tools: search_console · website        │
                    │         user_context · historical       │
                    └────┬───────────┬───────────┬────────────┘
                         │           │           │
              ┌──────────▼──┐ ┌──────▼─────┐ ┌───▼──────────┐
              │ Search      │ │ Sitemap    │ │ PostgreSQL   │
              │ Console API │ │ Crawler    │ │ 17           │
              └─────────────┘ └────────────┘ │ users        │
                                             │ oauth_*      │
              ┌─────────────┐                │ sessions     │
              │ Mistral AI  │◄───────────────│ jobs         │
              │ via LiteLLM │                │ seo_reports  │
              └─────────────┘                └───────┬──────┘
                                                     │ history
              ┌──────────────────────────┐            │ summaries
              │ Cron trigger · 08:00 UTC │            │
              │   → POST /scheduler      │◄───────────┘
              └──────────────────────────┘
                            │
                            ▼
                     SMTP email digest
```

### Request flow — interactive analysis

1. **Authorize.** `GET /api/v1/auth/google` redirects to Google consent. The callback exchanges the code, upserts `users` / `oauth_accounts` / `oauth_credentials`, opens a `sessions` row, and issues access + refresh JWTs.
2. **Select.** `GET /api/v1/search-console/sites` lists verified properties for the linked Google account.
3. **Contextualize.** The dashboard collects three inputs the framework depends on: page count, site type (ecommerce / service / content / SaaS), and business goal.
4. **Stream.** `GET /api/v1/agent/weekly` opens an SSE stream. The agent fetches a 30-day Search Console snapshot, resolves the sitemap (submitted sitemap first, `/sitemap.xml` as fallback), crawls up to 150 pages, and truncates the payload to stay inside a prompt budget.
5. **Analyze.** A Strands `Agent` runs with the historical-reports tool attached. It loads the SEO skill, applies the tier caps, calls back for prior run summaries, and returns a single JSON object holding a Markdown `report` and a short `summary`.
6. **Persist.** The summary lands in `seo_reports` and becomes context for the next run.

### Request flow — scheduled digests

1. **A cron trigger** fires daily at 08:00 UTC and calls the scheduler endpoint. Any scheduler works here — a platform cron job, a container sidecar, or Celery beat.
2. **`SchedulerService.queue_daily_reports()`** finds every user with live Google credentials, filters to properties they own, and inserts one `jobs` row per user-site pair.
3. **Only the job ID is published** to Redis, keeping the message small and the database the single source of truth for job state.
4. **The Celery worker** claims the job, marks it `processing`, increments `attempts`, runs `DailyAgent` over a 7-day window, emails the digest, and marks it `completed`. Failures record `error_message` and re-raise so Celery retries with exponential backoff (three attempts, capped at 600s).

### The SEO skill

The agent's domain knowledge lives in a versioned skill file rather than an inline prompt string, so it can be reviewed and edited like any other artifact. It defines:

- **Required context** — site size, site type, goal, with a tier table mapping size to per-run stage and page-sample caps
- **Mandatory data collection** — Search Console tool calls before any analysis, plus derived signals: striking-distance queries (positions 4–20), high-impression/low-CTR pages, sitemap-versus-index gaps
- **Resume rules** — load prior findings first, advance to the next stage group, never re-analyze a stage with pending items
- **The 9 stages** — Technical Foundation, Crawlability, Rendering, Indexability, On-Page, Content, Search Intent, Semantic SEO, AI/GEO
- **Output contract** — every finding carries evidence, a business rationale, a manual fix, *and* a self-contained agent prompt, priced into a Critical / High / Medium / Quick Win priority band weighted by the user's goal

### Data model

```
users ──1:N── oauth_accounts ──1:1── oauth_credentials
  ├──1:N── sessions
  └──1:N── seo_reports

jobs  (queue state: user_id, site_url, status, attempts, error_message, timestamps)
```

`oauth_credentials` holds the Google access token, refresh token, and expiry. `sessions` holds this application's own state: a hashed refresh token, expiry, and revocation flag. Keeping them separate means revoking an app session never touches the Google grant. `seo_reports` stores the full Markdown report alongside the short summary used for historical context.

---

## Setup / Installation

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| [Python](https://www.python.org/) | 3.11+ | Pinned in `backend/.python-version` |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Dependency and virtualenv management |
| [Node.js](https://nodejs.org/) | 20+ | Required by Next.js 16 |
| [Docker](https://docs.docker.com/get-docker/) + Compose | latest | Local PostgreSQL and Redis |
| Google Cloud project | — | OAuth client + Search Console API |
| [Mistral API key](https://console.mistral.ai/) | — | Powers the agent's analysis |
| SMTP credentials | — | Gmail app password works for local testing |

### 1. Google Cloud setup

Do this first. Most setup failures happen here, not in the code.

1. Create or select a project in the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **Google Search Console API** under *APIs & Services → Library*.
3. Under *Google Auth Platform → Clients*, create an **OAuth client ID** of type *Web application* with this authorized redirect URI:
   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```
4. Under *Google Auth Platform → Audience*, set **User type** to *External* and register the scopes `openid`, `email`, and `.../auth/webmasters.readonly`.
5. Add your own Google account under **Test users**.

> [!IMPORTANT]
> `webmasters.readonly` is a sensitive scope. While the app sits in **Testing**, only accounts on the test-user list can complete the flow; everyone else gets `Error 403: access_denied` before the consent screen appears. Expect an "unverified app" warning on first sign-in and continue via *Advanced*.

### 2. Configuration

Create a `.env` in the repository root:

```env
# Application
APP_NAME="Search Console Agent"
DEBUG=true
APP_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

# Database
DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5433/app_db"

# Queue
REDIS_URL="redis://localhost:6379/0"

# Google OAuth
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"

# Tokens
JWT_SECRET="generate-a-long-random-string"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRY_DAYS=7

# AI
MISTRAL_API_KEY="your-mistral-api-key"

# Email (SMTP)
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-specific-password"
SMTP_FROM_EMAIL="your-email@gmail.com"
SMTP_FROM_NAME="Search Console Agent"

# Scheduler
SCHEDULER_ENABLED=true
DAILY_REPORT_TIME="08:00"
ADMIN_EMAIL="your-email@gmail.com"
```

| Variable | Purpose |
|---|---|
| `APP_NAME` / `DEBUG` | FastAPI title and debug mode; `DEBUG` also enables SQLAlchemy statement echo |
| `APP_URL` | Declared in settings; not currently used by request handling |
| `FRONTEND_URL` | Post-OAuth redirect target **and** the only allowed CORS origin |
| `DATABASE_URL` | Async SQLAlchemy connection string; also read by Alembic |
| `REDIS_URL` | Celery broker and the Redis client pinged on app startup |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Identify the *application* to Google. One pair serves every user; per-user tokens live in the database |
| `GOOGLE_REDIRECT_URI` | Must match the Google Cloud registration byte for byte |
| `JWT_SECRET` / `JWT_ALGORITHM` | Sign and verify this app's own access and refresh tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRY_DAYS` | Token lifetimes |
| `MISTRAL_API_KEY` | Authenticates the LiteLLM model used by both agents |
| `SMTP_*` | Mail server connection, credentials, and sender identity for report delivery |
| `SCHEDULER_ENABLED` | Gates the `/scheduler/*` routes; returns 503 when false |
| `DAILY_REPORT_TIME` | Reported by `/scheduler/status`; the actual cadence is set by whatever cron calls the trigger |
| `ADMIN_EMAIL` | Recipient for `/scheduler/test-email` and error notifications |

The frontend reads one browser-visible value from `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### 3. Run locally

**Quick start** — brings up Postgres, Redis, migrations, the Celery worker, the API, and the frontend, then tears them all down on `Ctrl+C`:

```bash
./dev.sh
```

**Manual start**, if you want each piece in its own terminal:

```bash
# Infrastructure: PostgreSQL on 5433, Redis on 6379, Adminer on 8081
cd backend
docker compose -f docker-compose.yaml up -d

# Dependencies and schema
ln -sfn ../.env .env
uv sync
uv run alembic upgrade head

# API
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Celery worker (separate terminal)
uv run celery -A core.celery_app worker --loglevel=info

# Frontend (separate terminal)
cd ../frontend && npm install && npm run dev
```

> [!NOTE]
> On Windows the worker sets `WindowsSelectorEventLoopPolicy` because psycopg's async driver cannot run on the Proactor event loop. No action needed, but it explains the policy override in `workers/daily_report_worker.py`.

**Service URLs**

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://127.0.0.1:8000 |
| OpenAPI docs | http://127.0.0.1:8000/docs |
| Adminer | http://localhost:8081 |

**Verify**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/openapi.json       # 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/auth/me     # 401 without a token
curl -s http://127.0.0.1:8000/api/v1/scheduler/status                              # scheduler config
```

### 4. Deploy

The backend ships as a container, so it runs on any platform that can take a Docker image. `deployment/docker/` holds a multi-stage `Dockerfile` (Python 3.11 slim, non-root user, port 8000) and a supervisord config that runs three processes in one image: Redis, the Celery worker, and Uvicorn. That keeps a single-container deployment viable for small instances, while nothing stops you from splitting the three into separate services once traffic justifies it.

What the platform needs to provide:

| Requirement | Notes |
|---|---|
| Container runtime | One image, port 8000 |
| PostgreSQL 17 | Managed or self-hosted; set `DATABASE_URL` |
| Redis | Bundled in the image by default; point `REDIS_URL` at a managed instance to split it out |
| Cron / scheduled job | Daily `POST /api/v1/scheduler/trigger` |
| Environment variables | The `.env` keys documented above |
| Static hosting for the frontend | Any Next.js-capable host; `npm run build` output |

The frontend is a standard Next.js 16 build with one public variable, `NEXT_PUBLIC_API_BASE_URL`, so it deploys to any Node or static host.

---

## Usage

### Generate an analysis from the dashboard

1. Open the app and choose **Authorize with Google**.
2. Pick a verified Search Console property.
3. Set the three context fields — page count, site type, and primary goal. These drive the framework's tier caps and priority weighting, so answering them accurately changes the output materially.
4. Start the analysis. Progress streams live as the agent gathers credentials, pulls Search Console data, crawls the site, and reasons over current plus historical signal.
5. Read the Markdown report. Each finding includes the evidence behind it, a manual fix, and a ready-to-paste prompt for a coding agent.

### Trigger scheduled reports manually

```bash
# Enqueue one job per user-site pair
curl -X POST http://127.0.0.1:8000/api/v1/scheduler/trigger

# Inspect scheduler configuration
curl http://127.0.0.1:8000/api/v1/scheduler/status

# Send a sample report to ADMIN_EMAIL
curl -X POST http://127.0.0.1:8000/api/v1/scheduler/test-email
```

Job state is queryable straight from the `jobs` table:

```sql
SELECT site_url, status, attempts, error_message, created_at
FROM jobs ORDER BY created_at DESC LIMIT 20;
```

### API reference

All routes are mounted under `/api/v1`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/auth/google` | — | 302 redirect to Google's consent screen |
| `GET` | `/auth/google/callback` | — | Exchanges `code`, persists user + credentials + session, redirects to the frontend with tokens |
| `GET` | `/auth/me` | Bearer | Returns the authenticated user ID |
| `POST` | `/auth/logout` | — | Clears auth cookies |
| `GET` | `/search-console/sites` | Bearer | Lists Search Console properties for the linked Google account |
| `GET` | `/agent/weekly` | — | SSE stream of analysis progress and the final Markdown report |
| `POST` | `/scheduler/trigger` | — | Enqueues daily report jobs for all active users |
| `GET` | `/scheduler/status` | — | Reports scheduler configuration |
| `POST` | `/scheduler/test-email` | — | Sends a sample report to `ADMIN_EMAIL` |

`GET /agent/weekly` accepts `user_id`, `site_url`, `website_number_of_pages`, `website_type`, and `user_goal` as query parameters and emits `data: {"message": "..."}` frames. Progress markers are literal strings (`Getting Google credentials...`, `Fetching Search Console...`, `Scraping website...`, `Analyzing current and historical SEO data...`), terminating in `Completed.` or `Failed.`; anything else in the stream is the report body.

---

## Project structure

```
.
├── backend/
│   ├── main.py                      # FastAPI app, CORS, lifespan (DB + Redis health)
│   ├── api/
│   │   ├── main.py                  # /api/v1 router aggregation
│   │   └── routes/                  # auth, search_console, agents (SSE), scheduler
│   ├── agents/
│   │   ├── weekly_agent.py          # Skill-driven analysis, history-aware, SSE generator
│   │   └── daily_agent.py           # Compact 7-day digest for scheduled runs
│   ├── system-prompt/
│   │   └── SKILL.md                 # staged-seo-growth-agent: 9-stage framework
│   ├── tools/                       # Strands @tool adapters
│   │   ├── search_console_tool.py   #   GSC snapshot collection
│   │   ├── website_tool.py          #   sitemap crawl
│   │   ├── user_context_tool.py     #   per-user credential lookup
│   │   └── historical_reports_tool.py  # prior run summaries (capped)
│   ├── core/
│   │   ├── celery_app.py            # Celery application
│   │   ├── celery_config.py         # Broker, serialization, imports
│   │   ├── redis_config.py          # Async Redis client
│   │   ├── config.py                # pydantic-settings
│   │   └── enums.py                 # OAuthProvider, JobStatus
│   ├── workers/
│   │   └── daily_report_worker.py   # Celery task: job lifecycle + retries
│   ├── services/                    # OAuth, JWT, sessions, GSC, scraper, email, scheduler, reports
│   ├── models/                      # User, OAuthAccount, OAuthCredential, Session, Job, SEOReport
│   ├── db/dbconfig.py               # Async engine + session factory
│   ├── alembic/                     # Migration history
│   └── docker-compose.yaml          # Local PostgreSQL + Redis + Adminer
├── frontend/
│   └── src/
│       ├── app/                     # App Router: landing, callback, dashboard
│       ├── components/              # Site selector, analysis display, UI primitives
│       └── lib/                     # API client, auth, config, types
├── deployment/docker/               # Dockerfile + supervisord (Redis, worker, API)
└── dev.sh                           # One-command local stack
```

---

## Known limitations

This is a working project, not a hardened production deployment. Contributions welcome on any of these:

- `GET /agent/weekly` takes `user_id` as a query parameter without the authentication dependency, so it neither verifies the caller nor checks site ownership. The `/scheduler/*` routes are likewise unauthenticated.
- Google access and refresh tokens are stored as plaintext columns rather than encrypted at rest.
- `WeeklyAgent.SKILLS_PATH` points at `backend/skills/staged-seo-growth-agent/SKILL.md`, but the skill actually lives at `backend/system-prompt/SKILL.md`. The loader falls back silently, so the staged framework is not reaching the model until the path is reconciled.
- The skill specifies structured todo objects with resume state; the current prompt asks for a `{report, summary}` pair instead, and there is no `todos` table yet. Persistent, resumable per-stage findings are the next milestone.
- `backend/requirements.txt` is stale relative to `pyproject.toml`: it still pins LangChain and LangGraph, which no longer appear anywhere in application code, and omits `celery`, `redis`, and `strands-agents`. Regenerate it with `uv pip compile pyproject.toml -o requirements.txt`.
- The SSE protocol is untyped: progress versus result is decided by literal string matching, so changing backend wording changes UI classification.
- No `/health` route exists in application code, though the container healthcheck probes it. Add one before relying on container health signals.
- The Alembic revision graph drops and recreates `sessions` across revisions; reconcile against a deployed schema before upgrading an existing database.

## Contributing

Issues and pull requests are welcome.

1. Fork the repository and branch from `main`.
2. Keep the layering intact: HTTP in `api/`, business and provider logic in `services/`, agent-callable adapters in `tools/`, orchestration in `agents/`, background execution in `workers/`.
3. Run `uv run alembic revision --autogenerate -m "..."` for any model change.
4. Verify the frontend with `npx tsc --noEmit` and `npm run lint`.
5. Open a PR describing the change and how you tested it.

## Authors

Built by [Muhammad Usman](https://github.com/muhmdusman) and [Muhaddis](https://github.com/Muhaddis-igis).

## License

Released under the [MIT License](LICENSE).

## Topics

`ai-seo-agent` `seo` `seo-tools` `google-search-console` `ai-agent` `agentic-ai` `strands-agents` `llm` `litellm` `mistral-ai` `celery` `redis` `fastapi` `nextjs` `react` `typescript` `python` `postgresql` `sqlalchemy` `oauth2` `server-sent-events` `tailwindcss` `seo-automation` `search-console-api`
