<div align="center">

# SeOup Agent

**An AI SEO agent for small and mid-sized websites that analyzes Search Console, performance, and technical data, fixes what it can, and turns the rest into actionable tasks.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](backend/.python-version)
[![Strands Agents](https://img.shields.io/badge/Strands%20Agents-Agents%20for%20Humans%20Hackathon-232F3E.svg)](https://strandsagents.com/)

[Live application](https://main.d2cjd8wxgkx3po.amplifyapp.com/) · [Repository](https://github.com/muhmdusman/seo-agent)

</div>

---

## Problem

Small and mid-sized websites often know SEO matters, but they do not always have the budget for dedicated SEO professionals, expensive platforms, or daily manual monitoring. The team is usually busy with the actual business while SEO becomes one of those important but boring tasks that keeps getting postponed.

That gap is costly. Common search visibility, indexing, performance, content, and technical issues can sit unnoticed for weeks, and by the time a business sees the traffic drop, the fix is already overdue.

SeOup Agent was built for exactly this problem:

**When you are busy focusing on important business work, SeOup Agent handles the boring but important SEO work for you.**

## Who It's For

SeOup Agent is designed for small to mid-sized websites and businesses:

- Founders and small teams that need SEO direction without hiring a full-time specialist.
- Local businesses that want visibility but do not have time to check technical search issues every day.
- Small agencies that need repeatable, evidence-backed SEO monitoring for client sites.
- Developers and site owners who want clear tasks instead of generic SEO checklists.

## Solution

SeOup Agent is not a simple chatbot or a raw SEO data dashboard. It is an agentic SEO workflow that investigates a website through multiple tools, reasons over the results, performs supported actions when it safely can, and creates actionable tasks for everything else.

The core workflow is:

```text
Collect -> Analyze -> Reason -> Fix -> Create Tasks -> Report
```

The agent combines tool data, SEO skills, website context, user goals, saved history, and Strands agent reasoning to decide what matters most for a specific website.

## How SeOup Agent Works

The agent gathers evidence from Google Search Console, sitemap data, website context, saved historical reports, and the current SEO skill framework. The intended toolset also includes PageSpeed Insights/Core Web Vitals and a dedicated source HTML/HTTP headers tool, documented here so the README already matches the near-term architecture without claiming those integrations are fully wired yet.

After collecting evidence, the agent determines:

1. What is wrong with the website's SEO.
2. Why the issue matters.
3. What should be improved.
4. How it can be improved.
5. What should be done first.
6. Which actions can be performed autonomously.
7. Which actions require the website owner or developer.

The result is a structured report, prioritized SEO tasks, manual fix instructions, and coding-agent prompts that can be handed directly to a developer.

## Agentic Workflow

SeOup Agent uses a staged workflow rather than returning a one-time audit:

```text
User goal
  -> Strands SEO Agent
  -> Select relevant tools
  -> Collect evidence
  -> Apply SEO skills
  -> Reason over the site context
  -> Fix supported issues or create tasks
  -> Save report and history
  -> Continue monitoring
```

The product has three main analysis modes:

- **SEO review & fixes** identifies evidence-backed technical, content, indexing, and visibility issues.
- **Check changes and their results** revisits saved task URLs, checks observable changes, and compares later Search Console performance windows when enough data exists.
- **Opportunities to get more visibility** runs after the nine-stage framework and looks for growth opportunities, competitor evidence, internal-linking improvements, and follow-up experiments.

The agent does not treat the end of the framework as the end of the workflow. Once a site has gone through the staged review, SeOup Agent keeps reviewing results and looking for the next useful opportunity.

## Agent Tools & Capabilities

### Google Search Console

Search Console is used for search performance data, queries, clicks, impressions, indexing information, URL inspection, sitemap-related operations, and supported indexing actions.

The agent uses Search Console to reason about actual search visibility and indexing problems, not just to display data. When the app is configured with the required write permissions, supported actions such as sitemap submission or indexing requests can be performed as user-approved agent actions.

### PageSpeed Insights

PageSpeed Insights is part of the intended agent toolset. It will use the Google PageSpeed Insights API to retrieve relevant performance and SEO signals, including Core Web Vitals, LCP, CLS, INP, performance score, SEO score, and Lighthouse diagnostics.

The agent should not blindly call PageSpeed at every stage. Strands decides when performance information is relevant to the current investigation and invokes the tool when required. The PageSpeed tool should normalize the API response and extract important signals instead of passing the entire raw response into the model context. Its API key belongs in secure environment configuration and must never be exposed publicly.

### Source HTML & HTTP Headers

The planned dedicated source HTML tool will retrieve HTTP response status, headers, source HTML, and important SEO signals from the page. It should extract compact structured evidence such as title, meta description, canonical, robots directives, H1 and main headings, important links, content visibility, and other technical SEO signals.

The full raw HTML should not be passed into the agent context. The tool should parse the page and provide only the information needed for SEO reasoning. That lets the agent decide whether the page returns correctly, whether important metadata exists, whether meaningful content is visible in source HTML, whether content appears server-rendered, and whether browser rendering is needed.

Browser rendering, such as Playwright, can be used as an escalation path when source HTML is insufficient. It should not be the default for every page.

### Sitemap Analysis

Sitemap analysis helps the agent inspect sitemap health, discover important URLs, identify sitemap/index gaps, and decide which pages should be checked first.

### SEO Skills

Structured SEO skills and rules provide the domain knowledge used by the agent when interpreting tool results. They keep the output grounded in a repeatable SEO framework instead of a generic checklist.

## Intelligent Tool Calling

The system is not designed as:

```text
Call every tool -> combine everything -> generate report
```

The point of using an agent architecture is that Strands can decide which tool is relevant to the current SEO investigation:

- Search Console for search visibility, indexing, queries, and URL inspection.
- PageSpeed Insights for performance and Core Web Vitals.
- Source HTML for metadata, headings, content availability, and technical HTML.
- HTTP headers for server response and technical signals.
- Sitemap analysis for sitemap health and URL discovery.
- Browser rendering only when rendering needs to be verified.

This avoids unnecessary API calls, latency, cost, and oversized context. The agent calls tools when they add useful evidence.

## Autonomous SEO Actions

For supported Search Console operations, the intended workflow is:

```text
Agent can fix -> Agent performs the action
Agent cannot safely or directly fix -> Agent creates a task with instructions
```

Examples of user-approved autonomous actions include submitting a sitemap, requesting indexing for a URL, or performing other supported Search Console actions when the required permissions are configured.

For website code, content, design, CMS, or business decisions that cannot safely be changed by the agent, SeOup Agent creates a clear task for the user or developer.

## SEO Skills & Reasoning

Every site moves through a nine-stage SEO framework. Website size controls how many stages fit into one bounded run; it does not remove stages.

| Group | Ordered stages | Typical focus |
|---|---|---|
| Foundation | 1. Technical Foundation, 2. Crawlability, 3. Rendering, 4. Indexability | HTTP status, robots, sitemaps, redirects, raw HTML, JavaScript dependencies, canonicals, indexing signals |
| Content | 5. On-Page, 6. Content | Titles, metadata, headings, links, page copy, depth, freshness, useful coverage |
| Relevance | 7. Search Intent, 8. Semantic SEO | Query/page alignment, striking-distance queries, entities, topical relationships, internal authority paths |
| Frontier | 9. AI/GEO | Clear answers, E-E-A-T signals, citable content, brand clarity, AI crawler accessibility |

Supporting lenses run inside these stages rather than becoming competing stage labels:

- Local SEO
- Ecommerce SEO
- International SEO
- Internal linking
- Competitor analysis and competitor research

Run size caps are `1-10: up to 4 stages`, `11-30: up to 3`, `31-100: up to 2`, and `101+: 1 stage`. Saved coverage determines the next sequential bundle.

## Personalized / Goal-Based Analysis

SeOup Agent does not give every website the same checklist. The final analysis is based on:

```text
Tool data + SEO skills + website context/size + user goal + agent reasoning
```

The agent considers website size, website type, user goals, Search Console analytics, technical signals, performance signals, existing SEO issues, historical reports, and saved tasks. That context helps it prioritize the problems that actually matter for that website.

## Actionable Tasks

The agent does not stop at "you have an SEO problem." For every important issue, the output explains:

- What's wrong.
- Why it matters.
- How to improve it.
- Step-by-step instructions.
- Priority.
- Whether the agent can fix it automatically.
- Whether the user needs to perform the action.

Each model response is validated against a strict schema before it is saved. The server owns task identity, status, dates, deduplication, completion state, and later review state.

## Historical Reports

SeOup Agent saves previous SEO reports so users can access earlier findings, review what was recommended, track previously identified issues, and understand SEO progress over time.

Historical reports also become context for later runs. The agent can avoid repeating the same work and can focus on the next stage, a saved change review, or a new visibility opportunity.

## Weekly Email Reports

The platform supports scheduled weekly SEO analysis and email delivery. This matters for busy users who may not log into the dashboard regularly.

```text
Weekly scheduler -> SEO Agent -> Tool analysis -> Reasoning -> Report -> Email -> User inbox
```

The user can stay informed about important SEO issues even when they have not opened the dashboard.

## Strands Agents Integration

Strands Agents is the orchestration and reasoning layer of SeOup Agent. It is central to the product behavior, not just a dependency.

Strands enables the agent to:

- Reason over information gathered from multiple tools.
- Decide which tools are necessary for a particular SEO investigation.
- Call tools only when relevant.
- Combine results from different sources.
- Apply SEO skills to those results.
- Decide whether an issue can be fixed automatically.
- Determine when a user task needs to be created.
- Produce prioritized and contextual SEO analysis.

Conceptually:

```text
User goal
  -> Strands SEO Agent
  -> Select relevant tools
  -> Collect evidence
  -> Apply SEO skills
  -> Reason
  -> Fix / create tasks
  -> Report
```

The active checked-in model path uses LiteLLM provider abstraction with `groq/openai/gpt-oss-120b`. The AWS deployment path is designed to support Amazon Bedrock through the same provider boundary and an IAM task role.

## AWS Architecture

The AWS deployment is organized around a public dashboard, a backend API, a Strands-powered SEO agent runtime, persistent storage, and scheduled reporting.

The documented deployment uses AWS Amplify, an Amazon API Gateway entry point, Amazon ECS on Fargate, Amazon ECR, Amazon RDS for PostgreSQL, Amazon EventBridge, AWS Secrets Manager, AWS IAM, and Amazon CloudWatch. Amazon Bedrock is the AWS model provider option; the checked-in model default uses Groq. The container configuration runs FastAPI, Redis, and a Celery worker together.

## Architecture Diagram

![SeOup Agent architecture with official AWS icons, the dashboard request path, Strands runtime, evidence sources, model providers, persistence, and scheduled email delivery](docs/architecture/seo-agent-architecture.svg)

[High-resolution PNG](docs/architecture/seo-agent-architecture.png) · [Editable SVG](docs/architecture/seo-agent-architecture.svg) · [Architecture notes and regeneration instructions](docs/architecture/README.md)

The request path is **Website owner → Amplify dashboard → API Gateway → FastAPI / Strands runtime**. Results return through the API to the dashboard, while PostgreSQL saves reports, tasks, and history. Redis and Celery support scheduled email reports.

The diagram uses [official AWS Architecture Icons](https://aws.amazon.com/architecture/icons/). It shows the logical ECS/Fargate deployment; exact API Gateway and scheduler targets depend on deployment configuration. Dashed amber connections identify the planned PageSpeed integration and the Bedrock provider option. HTTP/source HTML evidence already comes from the scraper; dedicated tool wiring and Search Console write actions remain future extensions. No backend endpoints or credentials appear in the diagram.

## Technology Stack

| Layer | Technology |
|---|---|
| Agent orchestration | Strands Agents |
| Model abstraction | LiteLLM, Groq model path, Bedrock-ready provider boundary |
| Backend API | FastAPI, Python 3.11, Pydantic |
| Persistence | PostgreSQL, SQLAlchemy, Alembic |
| Background jobs | Celery, Redis/Valkey-compatible broker |
| Frontend | Next.js, React, TypeScript |
| Deployment | AWS Amplify, ECS Fargate, ECR, RDS, EventBridge, Secrets Manager, CloudWatch |
| Email | SMTP-compatible email delivery |

## Setup / Installation

Prerequisites:

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- Docker and Docker Compose
- Google Cloud OAuth client with the Search Console API enabled
- Model provider credentials or AWS Bedrock/IAM configuration

Quick start:

```bash
cp .env.example .env
./dev.sh
```

Manual backend setup:

```bash
cd backend
docker compose -f docker-compose.yaml up -d
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend setup:

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Public documentation lists variable names and purpose only. Do not publish actual values.

| Variable | Purpose |
|---|---|
| `APP_NAME` | Application display name |
| `DEBUG` | Local debug behavior |
| `APP_URL` | Backend application base URL for server-side use |
| `FRONTEND_URL` | Allowed frontend origin and OAuth return target |
| `BACKEND_API_URL` | Server-side frontend rewrite target; do not expose as `NEXT_PUBLIC_*` |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Queue/cache connection string |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Registered OAuth callback |
| `JWT_SECRET` | Token signing secret |
| `LLM_MODEL_ID` | Active model identifier |
| `GROQ_API_KEY` | Groq provider key when using the Groq model path |
| `AWS_REGION` | AWS region for deployed services |
| `BEDROCK_MODEL_ID` | Bedrock model identifier for the AWS provider path |
| `PAGESPEED_API_KEY` | PageSpeed API key for the planned performance tool |
| `SMTP_*` | SMTP server, sender, and credential configuration |
| `SCHEDULER_ENABLED` | Enables or disables scheduled report routes |
| `DAILY_REPORT_TIME` | Scheduled report time setting |

Secrets should be injected through AWS Secrets Manager or the deployment platform's secret store.

## Usage

1. Connect a verified Google Search Console property.
2. Select the site, website size, website type, and primary goal.
3. Run an SEO review.
4. Review the agent's evidence, reasoning, fixes, and tasks.
5. Complete manual tasks or allow supported Search Console actions when configured.
6. Re-run change/result review to see what changed and what should happen next.
7. Use weekly email reports to stay informed without opening the dashboard every day.

## Example Workflow

```text
Small business owner connects Search Console
  -> chooses "local visibility" as the goal
  -> SeOup Agent checks Search Console, sitemap, site evidence, and saved history
  -> Strands selects only the relevant tools
  -> agent finds an indexing, metadata, or performance issue
  -> supported Search Console action is performed when allowed
  -> remaining work becomes prioritized tasks
  -> weekly report is emailed to the user
```

## Future Improvements

- Wire the dedicated PageSpeed Insights tool with compact normalized output.
- Wire the dedicated source HTML and HTTP headers tool with structured SEO extraction.
- Add browser rendering as an escalation path for pages where source HTML is not enough.
- Expand Search Console write actions behind explicit user approval.
- Add richer result comparison for completed tasks.
- Improve dashboard views for historical reports and progress over time.

## Hackathon / Agents for Humans

SeOup Agent was built for the Strands Agents / Agents for Humans Hackathon. The project focuses on a practical human problem: small businesses do not need another dashboard full of raw SEO data; they need an agent that investigates, reasons, fixes what it can, and turns the rest into clear next steps.

Strands Agents is the heart of that behavior. It lets the system choose tools, combine evidence, apply SEO skills, and produce contextual actions instead of a generic SEO report.

## Authors and License

Built by [Muhammad Usman](https://github.com/muhmdusman) and [Muhaddis](https://github.com/Muhaddis-igis) for the Strands Agents / Agents for Humans Hackathon.

Released under the [MIT License](LICENSE).
