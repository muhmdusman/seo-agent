# Fastn Workflow Context and Debugging Guide

This file is the canonical context for the SEO Agent Fastn integration. It exists so future agents do not repeat the tenant, end-org, installation, and Google Sheets mistakes that caused the workflow failures.

Do not treat this file as runtime configuration. It is debugging context and implementation guidance.

## Current Workflow Split

There are two different Fastn workflows. They must not be confused.

```text
Destination picker workflow
Name: SEO Agent Destination Options
ID: wf_84cad8eacfc8
Purpose: Lists the logged-in customer's writable GitHub repos and Google spreadsheet files.
Used by: UI picker endpoints only.

Task handoff workflow
Name: Daily SEO Agent Site Worker
ID: wf_3dd1351b36da
Purpose: Runs after the SEO agent saves tasks, then writes tasks to Google Sheets and creates GitHub issues when routed to GitHub.
Used by: FastnTaskSyncService after the agent completes.
```

Backend defaults live in `backend/core/config.py`:

```text
FASTN_WORKFLOW_ID=wf_3dd1351b36da
FASTN_DESTINATIONS_WORKFLOW_ID=wf_84cad8eacfc8
FASTN_WIDGET_ID=wgt_e50e98094782
FASTN_TENANT_HEADER=x-end-org-id
FASTN_INSTALLATION_HEADER=x-installation-id
```

## ID Model

Fastn has several IDs that look similar but mean different things.

```text
App user ID:
The UUID from our app/JWT/PostgreSQL user row.
Example debug user: 9e9a1342-3762-42d6-8d53-d0f8cb29652c

Fastn partner/developer org:
The org that owns the Fastn API key, workflows, and widget.
Example debug org: personal_1c088c8e482614d41416

Fastn customer/end-org:
The actual customer workspace used for connector execution.
Example debug end-org: f2367e72-0b1e-45b2-823e-5b1d3b6e06fd

Fastn installation:
The widget activation for one customer end-org. It pins the customer's connector connections.
Example debug installation: inst_8ec7e5976bce
```

The app user UUID is not the Fastn execution tenant. It is only the stable app-side customer reference.

Never hardcode the debug end-org or installation into production code.

## Correct Runtime Flow

### Connection and Picker Flow

1. The frontend calls `POST /api/v1/fastn/embed-token`.
2. The backend reads the authenticated app user.
3. The backend calls `FastnWorkflowService.create_embed_token(app_user_id)`.
4. The widget token request must use the app user UUID as the stable customer reference. Do not pre-resolve this route to the Fastn end-org before minting the widget token.
5. If Fastn returns `404 x-org-id does not match a customer organization of this account`, the backend creates the customer org using the app user UUID as `external_ref`, then retries the widget token request with the same app user UUID.
6. Fastn returns the widget token and mapped `data.endOrgId`.
7. The frontend opens the Fastn embed UI for that customer.
8. The frontend calls `GET /api/v1/fastn/destinations`.
9. The backend resolves the app user to the real Fastn end-org, then runs `wf_84cad8eacfc8`.
10. `execute()` resolves the matching installation and sends both:

```text
x-end-org-id: <real Fastn customer end-org>
x-installation-id: <matching widget installation>
```

The destination workflow must return only the connected customer's repos and spreadsheets, not the developer/API-key owner's repos.

### Post-Agent Task Handoff Flow

1. `WeeklyAgent.run(...)` generates SEO analysis.
2. `SEOWorkspaceService.finish_run(...)` saves the report and tasks locally.
3. `WeeklyAgent` calls `FastnTaskSyncService.sync_report(report_id, user_id)`.
4. `FastnTaskSyncService` loads the saved tasks and site settings.
5. It calls `resolve_customer_end_org(str(report.user_id))`.
6. It calls `FastnWorkflowService.execute(payload, tenant_id=fastn_end_org_id)`.
7. Because `FASTN_WORKFLOW_ID` defaults to `wf_3dd1351b36da`, the Daily SEO Agent Site Worker runs after the agent.
8. `execute()` resolves and sends the matching installation ID.
9. The workflow writes task rows to the selected spreadsheet and creates GitHub issues only for tasks routed to GitHub.

For backend-created tasks, the same workflow also performs conditional enrichment:

```text
Competitor-analysis task -> SerpAPI googleSearch -> compact result summary
Blog-post/service-page task -> Groq draft -> ButterCMS draft, then WordPress.com draft fallback
Completed backend task batch -> Slack channel summary when Slack is connected and a matching channel is available
```

These connector calls are best-effort per task. A missing SerpAPI, ButterCMS,
WordPress.com, or Slack connection is written into the task result and does not
discard the saved Google Sheets task handoff. CMS output is created as a draft;
the workflow does not publish content automatically.

The workflow was mock-validated after this branch was added. Fastn's manifest
readback currently still shows the original four connector entries, even after
refresh, so live execution of the newly referenced connectors remains an
explicit follow-up rather than an assumed success.

## Required Headers

Workflow execution must use:

```text
x-end-org-id: <real Fastn customer/end-org>
x-installation-id: <installation serving that same end-org and widget>
```

Do not switch back to:

```text
x-fastn-space-tenantid
```

That header appeared in inbound Fastn workflow metadata, but it did not correctly serve this connector execution path. Using it led to connector resolution against the wrong tenant.

## Important Error Meanings

### Repos Show Muhammad Usman Instead of Muhammad Muhaddis

This means the workflow is executing under the API-key owner or another tenant, not the current app user/customer end-org.

Check:

```text
fastn.customer_context.resolved customer_id=<app user UUID> end_org_id=<real Fastn end-org>
fastn.installation.lookup.success end_org_id=<same real end-org> installation_id=<matching inst_...>
fastn.execute.headers tenant_header=x-end-org-id tenant_id=<same real end-org>
```

### `No active connection for connector "googleDrive" and end-org ...`

The workflow is using an end-org that does not have that connector connected, or it is missing the matching installation.

For the debug customer, the destination workflow succeeded only when both values were present:

```text
x-end-org-id=f2367e72-0b1e-45b2-823e-5b1d3b6e06fd
x-installation-id=inst_8ec7e5976bce
```

### `Installation "inst_..." does not serve the requesting tenant`

The installation belongs to one end-org, but the request tenant header points to another ID.

Fix the customer end-org resolution first. Do not try to bypass authorization checks.

### `Requested org is outside your tenant scope`

The backend is using the app user UUID or an org-management alias as the execution tenant. Resolve the customer through the embed-token mapping and execute with the returned Fastn `endOrgId`.

### `x-org-id does not match a customer organization of this account`

This happens for a brand-new app user that does not yet have a Fastn customer org mapping. Existing users can mint a widget token immediately, which is why one account may work while another fails.

Fix:

1. Create or ensure the customer org with `external_ref=<app user UUID>`.
2. Retry `create_embed_token(<same app user UUID>)`.
3. Do not retry by passing the returned Fastn end-org as the widget token `x-org-id`.

### GitHub `createIssue` 404

Likely causes:

- The repo owner/repo values are wrong.
- The workflow is using the wrong connected GitHub account.
- The selected repo was typed manually instead of selected from the authenticated customer's repo list.

Avoid manual GitHub URL entry. Use the destination picker output.

### Google Sheets `Unable to parse range: Tasks!A1:AA500`

The selected spreadsheet does not have a tab named `Tasks`.

The workflow has been patched so the backend task handoff branch:

1. Tries the `Tasks` tab first.
2. Falls back to the first available tab, such as `Sheet1`.
3. Writes headers when the selected tab is empty.

For full scheduled-site runs, the original expected tabs are still:

```text
Sites
Stage Progress
Tasks
Runs
```

### Database Error: `column site_settings.google_spreadsheet_id does not exist`

The model/schema changed before the migration was applied.

The fix is the migration:

```text
backend/alembic/versions/6e8c7a4f2b10_site_settings_spreadsheet.py
```

It adds:

```text
site_settings.google_spreadsheet_id
site_settings.google_spreadsheet_name
```

Apply migrations against the same database the backend is using.

## Code Rules for Future Agents

- Use `resolve_customer_end_org(app_user_id)` as the authoritative app-user-to-Fastn-end-org mapping.
- For `/api/v1/fastn/embed-token`, call `create_embed_token_for_customer(app_user_id, display_name)`. The widget token boundary uses the app user reference, creates the Fastn customer mapping if missing, and returns the mapped `endOrgId`.
- Do not use `ensure_customer_org()` as the execution tenant resolver for existing customer workflow runs.
- Keep `FASTN_TENANT_HEADER=x-end-org-id`.
- Keep installation handling. Do not remove `x-installation-id`.
- On installation lookup HTTP 4xx/5xx, raise/log the real Fastn error. Do not silently continue without an installation ID.
- Do not hardcode customer end-org IDs, app user IDs, emails, installation IDs, spreadsheet IDs, or repo names in production code.
- The destination workflow is for UI pickers only. The second workflow after the agent is `wf_3dd1351b36da`.
- Use selected repo owner/name and spreadsheet id/name from saved site settings.
- Keep the backend database as the source of truth for reports/tasks.
- Never put Fastn API keys or OAuth secrets in frontend code or docs.

## Key Files

```text
backend/core/config.py
backend/api/routes/fastn.py
backend/services/fastn_workflow_service.py
backend/services/fastn_task_sync_service.py
backend/services/site_settings_service.py
backend/models/site_settings.py
backend/alembic/versions/6e8c7a4f2b10_site_settings_spreadsheet.py
backend/agents/weekly_agent.py
frontend/src/components/fastn-connections.tsx
frontend/src/app/dashboard/page.tsx
```

## Expected Logs

Successful picker flow:

```text
fastn.customer_context.resolved customer_id=<app_user_uuid> end_org_id=<fastn_end_org>
fastn.destinations.start workflow_id=wf_84cad8eacfc8 tenant_id=<fastn_end_org>
fastn.installation.lookup.success end_org_id=<fastn_end_org> widget_id=wgt_e50e98094782 installation_id=<inst_id>
fastn.execute.success workflow_id=wf_84cad8eacfc8 tenant_id=<fastn_end_org>
fastn.destinations.success github_login=<customer_login> repositories=<count> spreadsheets=<count>
```

Successful post-agent handoff:

```text
fastn.task_sync.start report_id=<report_id> requested_user_id=<app_user_uuid>
fastn.task_sync.loaded report_id=<report_id> task_count=<n> repo=<owner>/<repo> spreadsheet_id=<sheet_id>
fastn.customer_context.resolved customer_id=<app_user_uuid> end_org_id=<fastn_end_org>
fastn.task_sync.customer_resolved report_id=<report_id> app_user_id=<app_user_uuid> end_org_id=<fastn_end_org>
fastn.installation.lookup.success end_org_id=<fastn_end_org> installation_id=<inst_id>
fastn.execute.success workflow_id=wf_3dd1351b36da tenant_id=<fastn_end_org>
fastn.task_sync.success report_id=<report_id> end_org_id=<fastn_end_org>
```

## Verification Checklist

Before calling the issue fixed:

1. Confirm `/api/v1/fastn/destinations` shows the logged-in customer's GitHub login, not the API-key owner.
2. Confirm it returns the selected repo and spreadsheet name.
3. Confirm site settings save `github_owner`, `github_repo`, `google_spreadsheet_id`, and `google_spreadsheet_name`.
4. Confirm migrations are at head in the backend database.
5. Run focused backend tests:

```powershell
cd backend
$env:DEBUG='false'; .\.venv\Scripts\python.exe -m unittest tests.test_fastn_workflow
$env:DEBUG='false'; .\.venv\Scripts\python.exe -m compileall -q api services models schemas dependencies alembic
```

6. Smoke-test `wf_3dd1351b36da` with `source=backend_tasks`, the real end-org, and matching installation.
7. Replay and save Fastn workflow validation after editing workflow code.

## Known Debug Customer Snapshot

These values are examples from the September 20, 2026 debugging session. They are not production constants.

```text
App user email: muhaddisdev.ineer@gmail.com
App user ID: 9e9a1342-3762-42d6-8d53-d0f8cb29652c
Fastn end-org: f2367e72-0b1e-45b2-823e-5b1d3b6e06fd
Fastn installation: inst_8ec7e5976bce
GitHub login: Muhaddis-igis
Repo verified by picker: Muhaddis-igis/Bitoreal_New_Site
Spreadsheet verified by picker: Bitoreal_SEO_AGENT
```
