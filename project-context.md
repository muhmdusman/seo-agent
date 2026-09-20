# Search Console Agent: Fastn Integration

Canonical Fastn debugging guide:

```text
FASTN_WORKFLOW_CONTEXT.md
```

Use that file when diagnosing tenant, end-org, installation, embed token, repo picker, spreadsheet picker, or workflow execution issues.

## Overview

The application runs SEO analysis locally, saves reports and tasks in PostgreSQL, sends completed tasks to Fastn, and uses Fastn connectors to write task records to Google Sheets and create GitHub issues for implementation work. A Gmail summary is sent after each completed analysis.

```text
SEO analysis -> save report/tasks -> Fastn workflow -> Google Sheets -> GitHub issues -> Gmail summary
```

Fastn workflows:

```text
Destination picker:
ID: wf_84cad8eacfc8
Name: SEO Agent Destination Options

Post-agent task handoff:
ID: wf_3dd1351b36da
Name: Daily SEO Agent Site Worker
```

## User Authorization

The dashboard embeds a Fastn authorization panel for GitHub and Google Sheets:

```text
frontend/src/components/fastn-connections.tsx
```

The component requests a short-lived token from:

```text
POST /api/v1/fastn/embed-token
```

The backend then:

1. Reads the authenticated application user.
2. Requests the widget embed token using the app user UUID as the stable customer reference.
3. Requests an embed token from `POST https://api.fastn.dev/api/v1/embed/token`.
4. Reads the returned `endOrgId` for display/debugging.
5. Returns the iframe URL to the frontend.

Do not pre-resolve `/api/v1/fastn/embed-token` to the Fastn end-org before minting the widget token. Workflow execution is the path that resolves the app user to a real Fastn end-org and sends `x-end-org-id` plus `x-installation-id`.

The Fastn API key stays server-side. It must never be added to frontend code.

The iframe is hosted by Fastn and receives only a short-lived `emb_...` token. The frontend listens for Fastn's `fastn:session-expired` message and requests a new token. Fastn tokens normally last eight hours, with a maximum session lifetime of seven days.

Fastn widget:

```text
Name: SEO Agent Tools
ID: wgt_e50e98094782
Connectors: GitHub, Google Sheets
Activation mode: MULTI_CONNECTION
```

Each user has an isolated Fastn end-org and matching widget installation. Workflow requests include:

```text
x-end-org-id: <real Fastn customer/end-org id>
x-installation-id: <matching widget installation id>
```

Do not change this back to `x-fastn-space-tenantid`; that was the source of previous connector and tenant resolution failures.

## Fastn Workflow Branches

### Backend Task Handoff

After the local SEO agent completes an analysis, `FastnTaskSyncService` sends:

```json
{
  "source": "backend_tasks",
  "reportId": "report-id",
  "siteUrl": "site-url",
  "github_owner": "owner",
  "github_repo": "repository",
  "tasks": []
}
```

The `backend_tasks` branch:

1. Reads existing Sites and Tasks data from Google Sheets.
2. Skips task IDs already present in the Tasks sheet.
3. Appends each new task to the Tasks sheet.
4. Creates GitHub issues for tasks with `target_platform=github` and a configured repository.
5. Returns task and GitHub issue results.

### Scheduled Site Worker

The workflow also contains a scheduled-site branch that reads ready sites from Sheets, collects Search Console and performance evidence, advances staged SEO analysis, writes task and run history to Sheets, and synchronizes existing GitHub issues.

Active Fastn schedule:

```text
Cron: 0 9 * * *
Timezone: Asia/Karachi
```

The Fastn schedule runs Fastn's hosted workflow directly. It is separate from the local FastAPI process and cannot call a local `localhost` endpoint.

## Task Routing

Tasks use one of these target platforms:

```text
github
search_console
google_sheets
manual_review
```

Repository-backed implementation tasks are automatically routed to GitHub, including:

- Metadata and meta descriptions
- Title tags
- Keyword or page-content changes
- Canonical tags
- Robots.txt and sitemaps
- Schema and JSON-LD
- Redirects
- HTML, CSS, JavaScript, and templates
- Rendering and performance improvements
- Code or repository changes

Explicit Search Console actions remain review-only. Google Sheets is used for reporting/state. Generic or insufficiently evidenced recommendations remain `manual_review`.

Routing is applied when tasks are saved and again during Fastn handoff, so older tasks can be corrected after a repository is configured.

## GitHub Repository Mapping

The dashboard lets the user save a repository URL for each Search Console property.

Frontend:

```text
frontend/src/app/dashboard/page.tsx
```

API:

```text
GET /api/v1/seo/site-settings?site_url=...
PUT /api/v1/seo/site-settings?site_url=...
```

The mapping stores GitHub owner and repository in the `site_settings` table. Without a mapping, GitHub tasks are recorded as waiting for repository configuration and no GitHub issue is created.

## Backend Fastn Endpoints

```text
POST /api/v1/fastn/embed-token
POST /api/v1/fastn/reports/{report_id}/sync
POST /api/v1/fastn/daily-seo-agent/execute
```

Use the report sync endpoint to retry a completed report when the original Fastn handoff failed:

```text
POST /api/v1/fastn/reports/{report_id}/sync
```

The caller must be authenticated and must own the report.

## Important Files

```text
backend/api/routes/fastn.py
backend/services/fastn_workflow_service.py
backend/services/fastn_task_sync_service.py
backend/services/seo_workspace_service.py
backend/services/site_settings_service.py
backend/agents/weekly_agent.py
backend/agents/prompts/seo_review.py
frontend/src/components/fastn-connections.tsx
frontend/src/app/dashboard/page.tsx
```

## Environment Variables

Fastn configuration is in `backend/.env`:

```text
FASTN_API_BASE_URL=https://api.fastn.dev
FASTN_WORKFLOW_ID=wf_3dd1351b36da
FASTN_DESTINATIONS_WORKFLOW_ID=wf_84cad8eacfc8
FASTN_WIDGET_ID=wgt_e50e98094782
FASTN_API_KEY=<server-side Fastn API key>
FASTN_AUTH_HEADER=Authorization
FASTN_AUTH_SCHEME=Bearer
FASTN_TENANT_HEADER=x-end-org-id
FASTN_INSTALLATION_HEADER=x-installation-id
FASTN_TIMEOUT_SECONDS=30
```

Test keys automatically receive `X-fastn-Test-Mode: true`. Never commit API keys, SMTP passwords, OAuth secrets, or access tokens.

## Safeguards

- GitHub and Google Sheets workflow connectors use `MULTI_TENANT` scope.
- GitHub issue creation is limited to explicitly routed implementation tasks.
- Search Console changes are not performed automatically.
- Duplicate backend task IDs are skipped by the workflow.
- The local database remains the source of truth for reports and tasks.
- If model task generation returns no tasks, conservative evidence-based fallback tasks are used when available.
- Email delivery is independent of Fastn, so an email can arrive even when a Fastn handoff has no tasks or fails.
- Fastn executions return execution IDs and issue results for troubleshooting.

## Local Development

Start database services:

```bash
cd backend
docker compose up -d postgres redis adminer
```

Apply migrations:

```bash
cd backend
.venv/bin/alembic upgrade head
```

Start backend:

```bash
cd backend
DEBUG=false .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

Start frontend:

```bash
cd frontend
npm run dev
```

Local URLs:

```text
Frontend: http://localhost:3000
Backend: http://127.0.0.1:8000
Health: http://127.0.0.1:8000/health
```

## Verification

```bash
cd backend
DEBUG=false .venv/bin/python -m unittest tests.test_fastn_workflow tests.test_seo_output
DEBUG=false .venv/bin/python -m compileall -q api services models schemas agents
git diff --check
```

Frontend lint:

```bash
cd frontend
npm run lint
```

Current verification status: 18 backend tests pass, frontend lint passes, and the FastAPI health endpoint returns `{"status":"ok"}`.

## Troubleshooting

If an email arrives but Sheets or GitHub is empty:

1. Check the backend log for `model_candidates` and `final_candidates`.
2. Confirm the report has saved task rows in PostgreSQL.
3. Confirm the site has a GitHub repository mapping.
4. Inspect Fastn executions for the matching `reportId`.
5. Confirm the execution output contains `tasksCreated` and `githubIssuesCreated`.
6. Use the report sync endpoint to retry the handoff.

If the dashboard shows an organization error:

1. Refresh the dashboard to request a new embed token.
2. Confirm the backend can access `FASTN_API_KEY`.
3. Confirm test keys receive `X-fastn-Test-Mode: true`.
4. Confirm `resolve_customer_end_org(app_user_id)` returns the real Fastn `endOrgId`, not the app user UUID.
5. Confirm installation lookup returns the installation serving the same end-org and widget.
