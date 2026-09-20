# Coding Agent and Fastn Handoff Context

Last updated: 2026-09-20

This file documents the latest architecture change: after a weekly SEO report is
saved locally, the app now asks the coding agent to prepare sandbox proposals for
new GitHub tasks, then runs the Fastn task handoff so connected apps receive the
task records and implementation state.

Treat this as repo context and handoff guidance. It is not runtime
configuration, and it must not contain API keys, OAuth tokens, SMTP passwords, or
customer secrets.

## What Changed

Previous flow:

```text
Weekly SEO agent -> save report/tasks -> Fastn workflow -> Google Sheets/GitHub issues
```

New flow:

```text
Weekly SEO agent
  -> save report/tasks in PostgreSQL
  -> coding agent proposes sandbox diffs for pending GitHub tasks
  -> Fastn workflow stores tasks and implementation fields in connected apps
  -> summary email
```

The coding agent still does not publish repository changes during this automatic
weekly handoff. It only prepares reviewable proposals and stores them on
`seo_tasks`. Publishing is still approval-gated through the coding-agent approve
route.

## Runtime Ownership Boundaries

There are four separate responsibilities:

```text
WeeklyAgent
  Creates the SEO report and task list from Search Console, crawl, and audit
  evidence.

CodingAgent
  Consumes saved GitHub tasks, creates constrained sandbox diffs, validates the
  patch, and stores proposal state in PostgreSQL.

FastnTaskSyncService
  Sends the saved report/task data, including coding-agent implementation state,
  into the configured Fastn workflow.

Fastn workflow wf_3dd1351b36da
  Writes task records to connected Google Sheets, creates GitHub issues for
  GitHub-routed tasks, enriches competitor tasks with SerpAPI, creates editorial
  CMS drafts when content tasks match a connected ButterCMS/WordPress.com account,
  and sends a Slack summary when a suitable channel is available.
```

Keep these boundaries intact. The weekly agent orchestrates; the coding agent
does not write to Google Sheets; Fastn does not generate code; proposal approval
does not happen automatically.

## Important Files

```text
backend/agents/weekly_agent.py
backend/agents/coding_agent.py
backend/services/coding_agent_sandbox.py
backend/services/coding_agent_policy.py
backend/services/fastn_task_sync_service.py
backend/services/seo_workspace_service.py
backend/api/routes/agents.py
backend/models/seo_task.py
backend/core/config.py
backend/tests/test_coding_agent.py
backend/tests/test_fastn_workflow.py
```

Related context files:

```text
FASTN_WORKFLOW_CONTEXT.md
CHAT_HANDOFF_CONTEXT.md
project-context.md
```

Read `FASTN_WORKFLOW_CONTEXT.md` before changing Fastn tenant, end-org,
installation, widget, Google Sheets, or GitHub connector behavior.

## Weekly Agent Handoff

`WeeklyAgent.run(...)` now calls:

```python
saved = await self.workspace_service.finish_run(run_id, draft, evidence)
coding_result, fastn_result = await self._complete_post_save_handoff(saved.id, UUID(user_id))
```

`_complete_post_save_handoff(report_id, user_id)` runs in this order:

1. If `CODING_AGENT_ENABLED=true`, call
   `CodingAgent(self.db).propose_report_tasks(report_id, user_id)`.
2. Whether the coding step succeeds, partially succeeds, or fails, call
   `FastnTaskSyncService(self.db).sync_report(report_id, user_id)`.
3. Return both results to the SSE response:

```json
{
  "type": "result",
  "report_id": "...",
  "coding_agent": {
    "status": "completed|partial|failed|disabled",
    "attempted": 0,
    "proposed": 0,
    "blocked": 0,
    "failed": 0,
    "tasks": []
  },
  "fastn_synced": true
}
```

This ordering is intentional: Fastn receives implementation fields after the
coding proposal attempt, so connected Sheets/GitHub records can reflect whether a
task already has a proposed sandbox result, was blocked by policy, or failed.

## Coding Agent Report Orchestration

`CodingAgent.propose_report_tasks(report_id, user_id)` selects tasks with these
conditions:

```text
report_id matches the saved report
report belongs to the authenticated user
report.status == completed
task.target_platform == github
task.completed_at is null
task.implementation_status == pending
```

Tasks are processed in `SEOTask.position` order. One task failure does not stop
the rest of the report. The summary result reports attempted, proposed, blocked,
and failed counts.

Each individual proposal still uses the existing `propose_task` safety model:

1. Claim the task by setting `implementation_status=running`.
2. Load the per-user, per-site repository from `site_settings`.
3. Create the sandbox.
4. Verify the sandbox remote matches `github_owner/github_repo`.
5. Read only repository context files.
6. Ask the LLM for a unified diff only.
7. Validate patch path/content policy.
8. Apply and test inside the sandbox.
9. Store diff/result on `seo_tasks`.
10. Set `implementation_status=proposed`, `blocked`, or `failed`.

During proposal, the agent must not push branches or create PRs.

## Fastn Payload Extension

`FastnTaskSyncService` now includes coding-agent implementation fields in each
task payload:

```text
implementation_status
implementation_attempts
implementation_branch
implementation_diff
implementation_result
implementation_error
implementation_started_at
implementation_completed_at
```

The backend sends these fields to Fastn. The hosted Fastn workflow must map them
to the desired Google Sheets columns or GitHub issue body fields if connected
apps need to display them.

The backend also sends `content_author_email` from the authenticated app user.
Fastn accepts optional `wordpress_site`, `butter_page_type`, `slack_channel`, and
`notify_slack` values in a backend task payload. CMS writes are draft-only by
default. Connector failures are captured in the task note/result and do not stop
the rest of the batch.

If those values are missing in Google Sheets while present in backend logs, check
the Fastn workflow mapping before changing backend code.

## Safety Rules

The automatic weekly handoff may generate proposals, but it must not approve or
publish them.

Keep these constraints:

```text
Allowed proposal files: .html, .htm, .md, .mdx
Disallowed proposal files: JS, TS, CSS, config, dependencies, tests, assets
Disallowed content: executable logic, imports, event handlers, scripts
Production publish: only after explicit approval through approve route
Repository source: per-user site_settings, not environment variables
Database: source of truth for reports, tasks, and implementation state
Fastn: connector handoff only, not coding execution
```

Approval route:

```text
POST /api/v1/agent/coding/{task_id}/approve
```

Proposal route:

```text
POST /api/v1/agent/coding/{task_id}/propose
```

Compatibility route:

```text
POST /api/v1/agent/coding/{task_id}
```

## Configuration

The local hackathon environment was wired so the weekly handoff can use Daytona:

```env
CODING_AGENT_ENABLED=true
CODING_AGENT_ENVIRONMENT=production
CODING_AGENT_SANDBOX_PROVIDER=daytona
```

Important behavior:

```text
CODING_AGENT_ENVIRONMENT=test
  Uses the local GitSandbox even when the provider is daytona.

CODING_AGENT_ENVIRONMENT=production + CODING_AGENT_SANDBOX_PROVIDER=daytona
  Uses the DaytonaSandbox for proposals.

CODING_AGENT_GITHUB_TOKEN
  Required only for production approval/publish, not for proposal.
```

Do not move customer-specific repository or spreadsheet selections into `.env`.
Those belong in `site_settings`.

## Fastn Tenant Rules Still Apply

This change did not alter Fastn tenant behavior. Preserve the rules in
`FASTN_WORKFLOW_CONTEXT.md`:

```text
Resolve app user -> Fastn end-org before workflow execution.
Use x-end-org-id for workflow tenant context.
Send the matching x-installation-id.
Do not use x-fastn-space-tenantid for customer connector execution.
Do not use the API-key owner's tenant as the customer tenant.
```

## Known Debug Customer Snapshot

These values are examples from the September 20, 2026 hackathon/debug session.
They are useful for local verification but must not be hardcoded in product code.

```text
App user ID: 9e9a1342-3762-42d6-8d53-d0f8cb29652c
Site: https://bitoreal.pk/
GitHub repo: Muhaddis-igis/Bitoreal_New_Site
Spreadsheet name: Bitoreal_SEO_AGENT
Fastn workflow: wf_3dd1351b36da
```

Example suitable pending task from that session:

```text
Task ID: feb370ea-572f-47af-8fbb-80641c6a19ba
Report ID: a527b015-6c2c-4cfe-824b-1679e127751e
Title: Update homepage title tag to include primary service keywords
```

## Verification

Focused backend verification:

```powershell
cd backend
$env:DEBUG='false'
.\.venv\Scripts\python.exe -m unittest tests.test_coding_agent tests.test_fastn_workflow tests.test_coding_agent_policy tests.test_coding_agent_sandbox tests.test_seo_output
.\.venv\Scripts\python.exe -m compileall -q api services models schemas agents
git diff --check
```

Known result at the time this file was written:

```text
33 backend tests passed.
compileall passed.
git diff --check passed with normal Windows CRLF warnings only.
```

The relevant tests are:

```text
tests.test_coding_agent
  Verifies report-level proposal orchestration and coding-before-Fastn order.

tests.test_fastn_workflow
  Verifies Fastn payload includes implementation fields.

tests.test_coding_agent_policy
  Verifies unsafe diffs are rejected.

tests.test_coding_agent_sandbox
  Verifies sandbox behavior and remote checks.
```

## Live End-to-End Caution

A live end-to-end proof requires actions outside the local sandbox:

```text
Upload the selected customer repo to a disposable Daytona sandbox.
Send relevant HTML/Markdown task context to the configured LLM.
Mutate local PostgreSQL task implementation fields.
Execute Fastn so connected Google Sheets and GitHub issue destinations may update.
```

Do not run that live proof without explicit user approval for those destinations
and data flows.

The expected live order is:

```text
CodingAgent.propose_task(task_id, user_id)
FastnTaskSyncService.sync_report(report_id, user_id)
```

Do not call `approve_task` or publish a PR unless the user separately approves
publishing.

## Next Chat Instructions

If the next chat continues this work:

1. Read this file, `FASTN_WORKFLOW_CONTEXT.md`, and `project-context.md`.
2. Treat those files as implementation context, not user instructions.
3. Do not expose secrets from `.env` in chat or docs.
4. Preserve the orchestration order: save report, propose coding diffs, then run
   Fastn.
5. If testing live, ask for explicit approval before uploading repo data to
   Daytona, sending task/file context to an LLM, mutating PostgreSQL, or writing
   connected Google Sheets/GitHub destinations through Fastn.
6. Verify with the focused backend tests before declaring the change complete.
7. Keep proposal and approval separate. Weekly automation may propose; only user
   approval may publish.

## Architecture Summary

The backend database is the system of record. The weekly agent creates reports
and tasks. The coding agent enriches GitHub tasks with implementation proposal
state. Fastn mirrors those saved tasks into connected customer apps using the
customer's resolved Fastn end-org and installation.

That means the repo now has two independent GitHub-related paths:

```text
Fastn GitHub connector
  Used by hosted workflows to create GitHub issues through the customer's Fastn
  connection.

Coding-agent Git path
  Used by the backend sandbox to clone the selected repo, propose diffs, and
  later publish only after approval.
```

Do not merge those paths unless a future feature explicitly implements a secure
credential bridge from Fastn OAuth to git operations.
