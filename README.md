# SeOup Agent

SeOup Agent is an agentic SEO operations platform for small and mid-sized
businesses that need consistent SEO work but do not have a dedicated SEO
specialist, developer, content team, or agency budget.

It connects website owners to the evidence behind their search performance,
turns that evidence into prioritized tasks, performs narrowly scoped actions
when it can do so safely, and routes the remaining work to the tools and people
that can complete it.

> Hackathon status: This repository is a working hackathon prototype. Local
> analysis, task persistence, coding-agent proposals, Fastn routing, and the UI
> are implemented. Some external integrations still depend on tenant
> connections, connector metadata, or explicit live-smoke approval.

## The Problem

Small and mid-sized shops usually understand that SEO matters, but they rarely
have someone whose full-time job is to monitor Search Console, inspect
technical issues, research competitors, refresh content, maintain CMS pages,
and report results.

The result is an expensive gap:

- Search visibility and indexing problems remain unnoticed.
- Important technical fixes compete with daily business work.
- SEO tools produce data but not a clear order of operations.
- Content opportunities are identified but never reach the CMS.
- Developers receive vague requests instead of safe, specific implementation
  tasks.
- Owners have no reliable weekly feedback loop.

SeOup Agent gives a small team the practical equivalent of an SEO operator:
evidence, prioritization, safe execution, and a clear handoff.

## Product Promise

The product follows one rule:

**Investigate what matters, fix what is safe, and make the remaining work
actionable.**

It is not just a chatbot and it is not just a dashboard of raw metrics. It is a
workflow that combines search data, website context, historical reports, SEO
skills, model reasoning, coding proposals, and connected business tools.

## Core Workflow

~~~text
Connect site
  -> Run staged SEO analysis
  -> Collect evidence from relevant tools
  -> Reason over evidence and site context
  -> Apply supported safe actions
  -> Save report and tasks in PostgreSQL
  -> Generate coding proposals for eligible GitHub tasks
  -> Send task state to Fastn
  -> Write connected-app results
  -> Review progress on the next run
~~~

The weekly/daily handoff order is intentional:

~~~text
WeeklyAgent
  -> saves the completed report and tasks
  -> CodingAgent proposes sandbox diffs for eligible tasks
  -> FastnTaskSyncService sends the updated task state
  -> Fastn writes Sheets/GitHub/CMS/Slack results where configured
~~~

The database remains the source of truth. Fastn is the connected-app handoff
layer, not the coding runtime.

## SEO Analysis

The analysis is staged so a large website can be reviewed over multiple bounded
runs instead of producing one oversized, low-signal audit.

| Group | Stages | Typical questions |
| --- | --- | --- |
| Foundation | Technical Foundation, Crawlability, Rendering, Indexability | Does the site respond, crawl, render, and expose the right URLs? |
| Content | On-Page, Content | Are titles, metadata, headings, copy, and internal links useful? |
| Relevance | Search Intent, Semantic SEO | Do pages match demand and build topical authority? |
| Frontier | AI/GEO | Is the site clear, citable, trustworthy, and accessible to emerging answer systems? |

Supporting lenses can run inside those stages:

- Local SEO
- Ecommerce SEO
- International SEO
- Internal linking
- Competitor research

The agent considers website size, website type, user goals, Search Console
performance, technical evidence, previous reports, saved tasks, and completed
changes. It does not give every site the same checklist.

## Actionable Output

Each important finding becomes a structured task containing:

- What is wrong.
- Why it matters.
- Evidence supporting the finding.
- A recommended fix.
- Step-by-step manual instructions.
- Priority and stage.
- Whether the task can be automated.
- A target destination such as GitHub, a CMS, or manual review.
- A coding-agent prompt when a safe content/template proposal is possible.

Tasks are validated before persistence. The server owns task identity,
deduplication, status, dates, completion state, and implementation state.

## Coding Agent

The coding agent prepares reviewable proposals for eligible GitHub tasks after
the SEO report is saved.

### Proposal flow

~~~text
Select completed report tasks
  -> Require target_platform=github
  -> Load the user's repository mapping
  -> Create an isolated sandbox
  -> Verify the remote matches the selected repository
  -> Read limited repository context
  -> Ask the model for a unified diff
  -> Validate paths and content policy
  -> Apply and test the proposal in the sandbox
  -> Save diff and result on seo_tasks
~~~

The automatic weekly flow may propose changes, but it does not approve, push,
or publish them.

Current safety policy:

- Allowed proposal files are HTML, Markdown, and MDX.
- JavaScript, TypeScript, CSS, configuration, dependencies, tests, and assets
  are blocked by default.
- Executable logic, imports, scripts, and event handlers are rejected.
- The repository remote must match the user's saved GitHub owner/repository.
- Publishing requires the explicit coding-agent approval route.

Approval endpoint:

~~~text
POST /api/v1/agent/coding/{task_id}/approve
~~~

Proposal endpoint:

~~~text
POST /api/v1/agent/coding/{task_id}/propose
~~~

## Fastn Connected-App Workflow

Fastn hosts the connector workflow used after the local report and coding-agent
proposal step.

### Workflows

| Workflow | Purpose |
| --- | --- |
| wf_84cad8eacfc8 | Destination picker for connected GitHub repositories and Google Sheets |
| wf_3dd1351b36da | Scheduled SEO worker and backend task handoff |

The widget is wgt_e50e98094782 and exposes:

- GitHub
- Google Sheets
- Google Drive
- SerpAPI
- ButterCMS
- WordPress.com
- Slack

### Conditional task routing

~~~text
Competitor URL task
  -> SerpAPI googleSearch
  -> compact result summary
  -> task result, Google Sheets notes, GitHub context, Slack summary

Blog post or service page task
  -> Groq content draft
  -> ButterCMS draft when connected and metadata is available
  -> WordPress.com draft fallback

All backend task batches
  -> Google Sheets task rows
  -> GitHub issues for GitHub-routed implementation tasks
  -> Slack summary when a suitable channel is available
~~~

CMS writes are draft-only. The workflow never auto-publishes content.
content_author_email, wordpress_site, butter_page_type, slack_channel, and
notify_slack can be supplied by the backend or task payload.

Missing optional connectors are recorded in the task result and do not abort
the Google Sheets handoff or the rest of the batch.

### Fastn tenant isolation

Every customer must execute under their own Fastn customer/end-org and matching
installation:

~~~text
x-end-org-id: <real Fastn customer end-org>
x-installation-id: <installation serving that end-org>
~~~

Do not use x-fastn-space-tenantid as the customer execution tenant. The app
user UUID is the stable application-side customer reference, not the Fastn
execution tenant.

The Fastn API key stays server-side. It must never be placed in frontend code.

## System Architecture

~~~text
Next.js dashboard
  -> FastAPI API
  -> Google OAuth and JWT session
  -> WeeklyAgent / Strands Agents
  -> SEO tools and model provider
  -> PostgreSQL reports, tasks, history, site settings
  -> CodingAgent sandbox proposals
  -> Fastn workflow and customer connectors
  -> Google Sheets / GitHub / CMS / Slack

Celery + Redis
  -> scheduled weekly reports and email delivery
~~~

### Backend ownership

- WeeklyAgent runs the SEO investigation and saves reports/tasks.
- SEOWorkspaceService owns report/task persistence and staged progress.
- CodingAgent creates constrained implementation proposals.
- CodingAgentSandbox handles local or Daytona sandbox execution.
- CodingAgentPolicy validates proposed changes.
- FastnTaskSyncService builds the per-user Fastn payload.
- FastnWorkflowService resolves the customer end-org, installation, and
  workflow execution headers.
- PostgreSQL is the system of record.

### Frontend ownership

The Next.js dashboard provides:

- Google authentication flow.
- Site and analysis controls.
- Reports, tasks, history, and progress views.
- Coding-agent implementation state.
- Fastn connection manager iframe.
- Integration catalog for the seven supported/visible connectors.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Radix UI, Lucide |
| Backend | FastAPI, Python 3.11+, Pydantic |
| Agent orchestration | Strands Agents |
| Model abstraction | LiteLLM; current Groq path, Bedrock-ready boundary |
| Current model | groq/openai/gpt-oss-120b |
| Database | PostgreSQL, SQLAlchemy async |
| Migrations | Alembic |
| Background work | Celery with Redis/Valkey-compatible broker |
| Coding sandbox | Local GitSandbox for tests; Daytona option for production proposals |
| Auth | Google OAuth 2.0, JWT application session |
| Connected apps | Fastn connectors for GitHub, Sheets, Drive, SerpAPI, ButterCMS, WordPress.com, Slack |
| Deployment target | AWS Amplify, API Gateway, ECS/Fargate, ECR, RDS, EventBridge, Secrets Manager, CloudWatch |
| Email | SMTP-compatible delivery |

## Repository Structure

~~~text
backend/
  agents/
    weekly_agent.py
    coding_agent.py
  api/
    routes/
  services/
    seo_workspace_service.py
    fastn_workflow_service.py
    fastn_task_sync_service.py
    coding_agent_policy.py
    coding_agent_sandbox.py
  models/
  schemas/
  alembic/
  tests/
  main.py

frontend/
  src/app/
  src/components/
  src/lib/
  package.json

docs/
  architecture/

FASTN_WORKFLOW_CONTEXT.md
CODING_FASTN_HANDOFF_CONTEXT.md
CHAT_HANDOFF_CONTEXT.md
project-context.md
~~~

## Local Development

### Prerequisites

- Python 3.11+
- uv
- Node.js 20+
- Docker and Docker Compose
- Google Cloud OAuth web client with Search Console access
- A model-provider key for the selected model

### Backend

~~~powershell
cd backend
uv sync
docker compose -f docker-compose.yaml up -d
uv run alembic upgrade head
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
~~~

The backend serves at http://localhost:8000; OpenAPI documentation is at
http://localhost:8000/docs.

### Frontend

~~~powershell
cd frontend
npm install
npm run dev
~~~

The frontend normally serves at http://localhost:3000.

### Environment

Copy the root template and place backend runtime values in backend/.env:

~~~powershell
Copy-Item .env.example backend/.env
~~~

Never commit real secrets. Important variables include:

| Variable | Purpose |
| --- | --- |
| DATABASE_URL | Async PostgreSQL connection |
| REDIS_URL | Celery broker/cache |
| GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET | Google OAuth |
| GOOGLE_REDIRECT_URI | OAuth callback |
| JWT_SECRET | Application token signing |
| LLM_MODEL_ID | Active model identifier |
| GROQ_API_KEY | Groq model access |
| AWS_REGION / BEDROCK_MODEL_ID | Bedrock deployment option |
| FASTN_API_KEY | Server-side Fastn workflow execution |
| FASTN_API_BASE_URL | Fastn API base URL |
| FASTN_WORKFLOW_ID | Defaults to wf_3dd1351b36da |
| FASTN_AUTH_HEADER / FASTN_AUTH_SCHEME | Fastn authentication |
| CODING_AGENT_ENABLED | Enables report-level coding proposals |
| CODING_AGENT_SANDBOX_PROVIDER | local or daytona |
| CODING_AGENT_ENVIRONMENT | test or production |
| CODING_AGENT_GITHUB_TOKEN | Required only for approved publish |
| DAYTONA_API_KEY | Daytona sandbox access |
| PAGESPEED_API_KEY | PageSpeed integration when enabled |
| SMTP_* | Weekly email delivery |
| SCHEDULER_ENABLED / DAILY_REPORT_TIME | Scheduled analysis behavior |

Customer repository, spreadsheet, CMS, and channel choices belong in
site_settings or task payloads. They must not be hardcoded in environment
variables.

## Database and Migrations

The important persisted concepts are:

- Users and OAuth accounts.
- Site settings and selected destination choices.
- SEO reports and staged analysis progress.
- SEO tasks and deduplication state.
- Coding-agent implementation status, diff, result, and error fields.

Run migrations with:

~~~powershell
cd backend
uv run alembic upgrade head
~~~

After changing SQLAlchemy models:

~~~powershell
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
~~~

## API Surface

All backend routes are mounted below /api/v1. The main areas are:

- /auth for Google OAuth and session handling.
- /sites for site settings and selected destinations.
- /reports for report retrieval and history.
- /agents for analysis runs and coding-agent proposal/approval.
- /fastn for embed tokens, destination options, and report resync.

If a Fastn handoff fails, the report and tasks remain in PostgreSQL. A
completed report can be retried with:

~~~text
POST /api/v1/fastn/reports/{report_id}/sync
~~~

## Testing and Verification

Backend focused tests:

~~~powershell
cd backend
$env:DEBUG='false'
.\.venv\Scripts\python.exe -m unittest tests.test_fastn_workflow tests.test_coding_agent tests.test_coding_agent_policy tests.test_coding_agent_sandbox
~~~

Frontend checks:

~~~powershell
cd frontend
npm.cmd run lint
npm.cmd run build
~~~

Fastn validation is performed with mock connector execution. The current
workflow regression set covers:

1. Scheduled worker behavior with no ready site.
2. Existing backend task handoff.
3. Competitor-task SerpAPI enrichment.
4. Blog/service-page content routing.

The latest mock validation passes all four cases. It does not write to a
customer's live CMS, Slack, GitHub, or Google Sheets.

## Current Limitations

- Live SerpAPI, ButterCMS, WordPress.com, and Slack execution depends on
  connected customer accounts and Fastn action metadata.
- Fastn currently reports the new connector entries as non-stale, but action
  lists still require platform-level verification.
- CMS output is draft-only; automatic publishing is intentionally disabled.
- Coding-agent proposals are limited to safe HTML/Markdown/MDX changes.
- Approved publishing requires a GitHub token and separate user approval.
- PageSpeed, source HTML/headers, and browser-rendering escalation are planned
  or selectively wired, not universal on every run.
- A live end-to-end run requires explicit approval because it can upload
  repository context to a sandbox and write to connected customer apps.

## Security and Operational Rules

- Do not expose .env, OAuth secrets, Fastn keys, SMTP passwords, or customer
  data in logs, issues, or documentation.
- Resolve the authenticated app user to the real Fastn customer end-org before
  executing workflows.
- Always send the matching x-end-org-id and x-installation-id.
- Keep report/task state in PostgreSQL.
- Keep coding proposal and publishing approval separate.
- Treat connector failures as observable workflow results, not reasons to lose
  the locally saved report.
- Use mock mode for regression checks unless live side effects are explicitly
  approved.

## Documentation Map

- project-context.md - Fastn integration and tenant/debugging context.
- FASTN_WORKFLOW_CONTEXT.md - canonical workflow, connector, and tenant rules.
- CODING_FASTN_HANDOFF_CONTEXT.md - weekly agent, coding agent, and Fastn
  orchestration contract.
- CHAT_HANDOFF_CONTEXT.md - detailed continuation notes for future sessions.
- backend/README.md - backend-specific setup and API notes.
- docs/architecture/ - architecture diagram and regeneration notes.

These files are repository context, not user instructions. Read them before
changing workflow tenancy, connector routing, or coding-agent safety behavior.

## Hackathon Context

SeOup Agent was built for the Strands Agents / Agents for Humans Hackathon.
The project focuses on a practical, underserved user: the small business owner
who needs the outcomes of SEO expertise without being able to hire a dedicated
SEO department.

The central demonstration is not merely that an LLM can write an SEO report.
It is that an agent can:

1. Gather evidence from the right sources.
2. Decide what matters for a particular business.
3. Perform supported actions carefully.
4. Create tasks with enough context for a human or developer.
5. Prepare safe coding proposals without publishing them.
6. Deliver the result to the tools the business already uses.

## License

Released under the MIT License. See LICENSE.
