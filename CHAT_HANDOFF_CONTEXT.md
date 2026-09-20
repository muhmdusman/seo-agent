# Chat Handoff Context Pack

Last updated: 2026-09-20

This file is for the next Codex session. It is intentionally detailed because this
chat covered Fastn tenant isolation, widget credentials, Google/GitHub connector
routing, conditional SerpAPI/CMS/Slack task enrichment, and a Daytona-backed SEO
coding agent. Treat this as handoff context, not runtime configuration.

## Current Objective

The app is an SEO agent platform. The weekly/daily SEO agent analyzes a user's
site and saves tasks in the database. Fastn workflows handle connector-backed
destinations such as Google Sheets and GitHub issues, enrich competitor tasks
with SerpAPI, create draft content in a connected CMS, and send task summaries
to Slack when available. A separate coding agent generates safe code diffs for
selected GitHub tasks and only creates branches/PRs after approval.

The coding agent must:

- Be separate from the weekly agent.
- Read task context from the database.
- Read the selected GitHub repo from per-user `site_settings`, not environment
  variables.
- Work in a sandbox before approval.
- Only modify SEO-safe content files: `.html`, `.htm`, `.md`, `.mdx`.
- Avoid JavaScript logic, CSS, config, dependencies, tests, assets, and unrelated
  code.
- Generate and store a diff first.
- Require user approval before publishing.
- In test mode, keep changes local/preview-only.
- In production mode, create a branch and GitHub PR only after approval.

## Canonical Fastn Context

Read `FASTN_WORKFLOW_CONTEXT.md` before changing Fastn code. It is the canonical
record of the Fastn failures and fixes.

Important Fastn workflow IDs:

- Destination picker workflow: `wf_84cad8eacfc8`
- Daily SEO Agent Site Worker: `wf_3dd1351b36da`

Important Fastn rule:

- Workflow execution must resolve the logged-in app user to the real Fastn
  end-org and then send matching `x-end-org-id` plus `x-installation-id`.
- Do not use `x-fastn-space-tenantid` for customer connector execution.
- Do not pass the API-key owner's tenant as the customer tenant.
- Do not store customer repo or spreadsheet choices in env vars. They change per
  user and per site, so they belong in `site_settings`.

Known validated account facts from logs:

- User email: `muhaddisdev.ineer@gmail.com`
- App user ID: `9e9a1342-3762-42d6-8d53-d0f8cb29652c`
- Resolved Fastn end-org: `f2367e72-0b1e-45b2-823e-5b1d3b6e06fd`
- Matching installation seen in logs: `inst_8ec7e5976bce`
- Correct GitHub login for this customer: `Muhaddis-igis`
- Correct repo selected by user: `Muhaddis-igis/Bitoreal_New_Site`

Previous wrong behavior:

- Workflows showed `muhmdusman` repos for Muhaddis because the request was using
  the wrong tenant/installation boundary.
- Google Drive/Sheets failed with messages like "No active connection for
  connector googleDrive and end-org ..." when the end-org and installation did
  not match.
- GitHub issue creation returned 404 when the repo was typed manually or when the
  caller/tenant did not have access.

Current Fastn implementation to preserve:

- `backend/services/fastn_workflow_service.py` resolves customer end-orgs and
  installation IDs and logs the flow.
- `backend/api/routes/fastn.py` logs user ID/email/end-org and routes destination
  picker requests through resolved customer context.
- The second workflow, `wf_3dd1351b36da`, must run after the SEO agent.

The Fastn widget `wgt_e50e98094782` now displays GitHub, Google Sheets, Google
Drive, SerpAPI, ButterCMS, WordPress.com, and Slack. The task workflow creates
CMS drafts only, prefers ButterCMS when its connection and required metadata are
available, falls back to WordPress.com, and records connector failures without
aborting the Google Sheets handoff. Slack uses `slack_channel` when supplied or
looks for `seo-agent`, `seo`, or `general`.

The new workflow branches were mock-validated after publication. Fastn's
connector-manifest readback still reports only the original four workflow
connectors, so live SerpAPI/CMS/Slack execution is not considered verified until
that platform metadata is refreshed or an explicitly approved live smoke test is
run.

## Coding Agent Implementation State

New or modified backend files:

- `backend/agents/coding_agent.py`
- `backend/services/coding_agent_sandbox.py`
- `backend/services/coding_agent_policy.py`
- `backend/api/routes/agents.py`
- `backend/models/seo_task.py`
- `backend/services/seo_workspace_service.py`
- `backend/core/config.py`
- `backend/scripts/daytona_smoke_test.py`
- `backend/tests/test_coding_agent_policy.py`
- `backend/tests/test_coding_agent_sandbox.py`
- `backend/alembic/versions/8f31c7a2d901_coding_agent_task_state.py`
- `backend/alembic/versions/2c9d7f4a5b81_coding_agent_approval_statuses.py`

New or modified frontend files:

- `frontend/src/components/seo-task-list.tsx`
- `frontend/src/components/seo-workspace.tsx`
- `frontend/src/lib/seo-types.ts`

Configuration files changed:

- `.env.example`
- `backend/.env.production.example`
- `backend/pyproject.toml`
- `backend/uv.lock`

The coding agent API endpoints are:

- `POST /api/v1/agent/coding/{task_id}`
- `POST /api/v1/agent/coding/{task_id}/propose`
- `POST /api/v1/agent/coding/{task_id}/approve`

The compatibility route `/coding/{task_id}` calls `propose`.

The coding agent state is stored on `seo_tasks`:

- `implementation_status`
- `implementation_attempts`
- `implementation_branch`
- `implementation_diff`
- `implementation_result`
- `implementation_error`
- `implementation_started_at`
- `implementation_completed_at`

Allowed statuses:

- `pending`
- `running`
- `proposed`
- `applied`
- `pr_created`
- `blocked`
- `failed`

## Coding Agent Flow

Proposal flow:

1. Frontend calls `POST /api/v1/agent/coding/{task_id}/propose`.
2. Backend authenticates the logged-in user.
3. `CodingAgent.propose_task(task_id, user_id)` loads a completed GitHub task for
   that same user.
4. It loads `SiteSettings` for `user_id + task.report.site_url`.
5. It builds the repo URL from the saved DB fields:
   `https://github.com/{github_owner}/{github_repo}.git`
6. In test mode only, `CODING_AGENT_TEST_REPOSITORY_ROOT` may override the source
   as an offline fixture. This is not a customer repo setting.
7. It creates a sandbox:
   - test mode: local `GitSandbox`
   - production + provider `daytona`: `DaytonaSandbox`
8. The sandbox verifies the checkout remote matches the selected DB repo.
9. The coding agent gathers `.html`, `.htm`, `.md`, `.mdx` files.
10. In test mode, it narrows files to homepage paths configured by
    `CODING_AGENT_TEST_ALLOWED_PATHS`.
11. The LLM must return only a unified git diff.
12. `validate_patch` rejects unsafe files or unsafe content.
13. The sandbox applies the patch, runs `git diff --check`, scans protected
    content, commits inside the sandbox, and returns a diff.
14. The diff is stored in `seo_tasks.implementation_diff` with status `proposed`.
15. No GitHub push happens during proposal.

Approval flow:

1. Frontend calls `POST /api/v1/agent/coding/{task_id}/approve`.
2. Backend requires existing `implementation_status = proposed`.
3. Backend confirms the selected repo still matches the repo used for proposal.
4. In test mode, it applies the stored diff locally and sets status `applied`.
5. In production mode, it publishes a branch and creates a GitHub PR, then sets
   status `pr_created`.

Important production limitation:

- Fastn GitHub connector OAuth is not currently used as a git push credential.
- Production PR publishing uses `CODING_AGENT_GITHUB_TOKEN`.
- That token must have permission to push branches and create PRs in the selected
  customer repo.

## Daytona / MCP Context

Daytona was selected as the sandbox provider with a free-start/trial-style
hosted sandbox option. The official Daytona CLI was installed and authenticated.

CLI path used on Windows:

`C:\Users\jg\AppData\Roaming\bin\daytona\daytona.exe`

Codex MCP config was updated outside the repo at:

`C:\Users\jg\.codex\config.toml`

The appended MCP config was:

```toml
[mcp_servers.daytona]
command = 'C:\Users\jg\AppData\Roaming\bin\daytona\daytona.exe'
args = ['mcp', 'start']
startup_timeout_sec = 120

[mcp_servers.daytona.env]
APPDATA = 'C:\Users\jg\AppData\Roaming'
HOME = 'C:\Users\jg'
```

The user has restarted VS Code and Codex after this config change. In the next
session, check whether Daytona MCP tools are now available. If not, continue with
the repo's Daytona SDK adapter in `backend/services/coding_agent_sandbox.py`.

The SDK smoke test was created at:

`backend/scripts/daytona_smoke_test.py`

It only creates an empty sandbox, runs `pwd`, and deletes it. It does not upload
repository data.

Previous successful smoke output:

```text
daytona_create=True
exec_exit_code=0
exec_result=/home/daytona
daytona_deleted=True
```

Do not print or expose API keys. A Daytona API key exists in `backend/.env`.

## Environment Rules

Customer-varying repo/spreadsheet settings must not live in environment files.

These are app-level settings:

```env
CODING_AGENT_ENABLED=true
CODING_AGENT_SANDBOX_PROVIDER=local
CODING_AGENT_ENVIRONMENT=test
CODING_AGENT_PREVIEW_ROOT=.coding-agent/previews
CODING_AGENT_TEST_REPOSITORY_ROOT=
CODING_AGENT_TEST_ALLOWED_PATHS=index.html,home.html,homepage.html,public/index.html,pages/index.md,pages/index.mdx,pages/index.html,app/page.md,app/page.mdx,app/page.html,src/app/page.md,src/app/page.mdx,src/app/page.html
CODING_AGENT_GITHUB_BASE_BRANCH=main
CODING_AGENT_GITHUB_TOKEN=
```

Daytona settings are provider-level settings:

```env
DAYTONA_API_KEY=
DAYTONA_API_URL=https://app.daytona.io/api
DAYTONA_TARGET=
DAYTONA_SANDBOX_NAME_PREFIX=SEO_agent_sandbox
DAYTONA_SANDBOX_AUTO_STOP_MINUTES=15
DAYTONA_SANDBOX_AUTO_ARCHIVE_MINUTES=10080
DAYTONA_SANDBOX_EPHEMERAL=true
```

Current important behavior:

- If `CODING_AGENT_ENVIRONMENT=test`, `create_sandbox` intentionally uses
  `GitSandbox` even if `CODING_AGENT_SANDBOX_PROVIDER=daytona`.
- To test the Daytona-backed proposal path without editing `.env`, run a process
  with:

```powershell
$env:CODING_AGENT_ENVIRONMENT='production'
$env:CODING_AGENT_SANDBOX_PROVIDER='daytona'
```

This changes only that shell process.

## Useful Commands

Run backend focused tests:

```powershell
cd backend
$env:DEBUG='false'
.\.venv\Scripts\python.exe -m unittest tests.test_coding_agent_policy tests.test_coding_agent_sandbox tests.test_fastn_workflow
```

Run Daytona smoke test:

```powershell
cd backend
$env:DEBUG='false'
.\.venv\Scripts\python.exe scripts\daytona_smoke_test.py
```

Run migrations:

```powershell
cd backend
$env:DEBUG='false'
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Run frontend checks:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

On Windows, standalone scripts that use async psycopg may need:

```python
import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

Place that before importing DB/session code.

## Direct Daytona Adapter Test

Use this after confirming the user approves uploading the selected repo into an
ephemeral Daytona sandbox. In this chat, the user did approve changes and sandbox
testing.

```powershell
cd backend
$env:DEBUG='false'
@'
import asyncio
from services.coding_agent_sandbox import DaytonaSandbox

async def main():
    async with DaytonaSandbox(
        "https://github.com/Muhaddis-igis/Bitoreal_New_Site.git",
        "main",
    ) as sandbox:
        await sandbox.verify_remote("Muhaddis-igis", "Bitoreal_New_Site")
        files = await sandbox.files_for_context()
        print("daytona_adapter=True")
        print("remote_verified=True")
        print(f"context_file_count={len(files)}")
        print(f"context_files={','.join(sorted(files)[:12])}")

asyncio.run(main())
'@ | .\.venv\Scripts\python.exe -
```

This command had started once near the end of the prior session but was
interrupted. Before rerunning if needed, use the Daytona dashboard or CLI to check
whether a sandbox named like `SEO_agent_sandbox-main-...` was left behind. Do not
delete the user's manually created `SEO_agent_sandbox` unless they ask.

## Direct Coding Agent Proposal Test

Known open GitHub tasks for Muhaddis from the database:

- `5021ce7b-8702-4490-8fcd-924c49b6b149`
- `44cb0e12-647f-43ab-9d7e-4ab862620a05`
- `df4f19f0-8950-447e-9037-e513c8d12cd7`
- `4100b0c8-58dc-4835-8936-24c3914fe49d`

User ID:

- `9e9a1342-3762-42d6-8d53-d0f8cb29652c`

Example direct service invocation:

```powershell
cd backend
$env:DEBUG='false'
$env:CODING_AGENT_ENVIRONMENT='production'
$env:CODING_AGENT_SANDBOX_PROVIDER='daytona'
@'
import asyncio
from uuid import UUID

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from db.dbconfig import AsyncSessionLocal
from agents.coding_agent import CodingAgent

async def main():
    async with AsyncSessionLocal() as db:
        result = await CodingAgent(db).propose_task(
            UUID("5021ce7b-8702-4490-8fcd-924c49b6b149"),
            UUID("9e9a1342-3762-42d6-8d53-d0f8cb29652c"),
        )
        print(f"task_id={result['task_id']}")
        print(f"branch={result.get('branch', '')}")
        print(f"commit_present={bool(result.get('commit'))}")
        print(f"diff_length={len(result.get('diff', ''))}")
        print(f"tests={result.get('sandbox_tests')}")

asyncio.run(main())
'@ | .\.venv\Scripts\python.exe -
```

This will mutate DB task implementation state and may call the LLM. It should not
push to GitHub during proposal.

## UI State

The task list now shows coding-agent controls for GitHub tasks:

- Status
- Error text
- Branch
- Expandable diff
- Sandbox check summary
- Pull request link, when present
- `Generate diff`
- `Approve change`

This is implemented in `frontend/src/components/seo-task-list.tsx` and wired from
`frontend/src/components/seo-workspace.tsx`.

The UI does not create a separate page; it adds a compact hackathon-ready proposal
panel inside each GitHub task card.

## Validation Already Run

Focused backend tests passed:

```text
python -m unittest tests.test_coding_agent_policy tests.test_coding_agent_sandbox tests.test_fastn_workflow
```

Frontend lint passed:

```text
npm.cmd run lint
```

Frontend build passed when rerun with the needed network/escalation for Next font
fetching. There was an existing Next.js middleware convention warning.

`git diff --check` was clean except normal Windows line-ending warnings.

## Known Caveats / Next Work

1. Daytona MCP may now be available after the VS Code/Codex restart. Check tool
   availability first. If it is still unavailable in-tool, use the SDK adapter.

2. `CODING_AGENT_ENVIRONMENT=test` intentionally avoids Daytona so localhost
   preview remains possible. Production-mode proposal is needed to exercise
   Daytona.

3. Production PR publishing uses a GitHub token, not Fastn's GitHub connector.
   This is acceptable for the current hackathon build, but document it clearly.

4. `GitSandbox` with a remote source and `keep_preview=True` may leave preview
   files after removing the temporary clone metadata. The files remain viewable,
   but the preview may not remain a usable Git worktree. If local preview quality
   matters, improve this behavior before demo.

5. Do not mark SEO tasks completed just because a GitHub issue exists. Completion
   should be based on implementation/review state.

6. Do not change Fastn request headers while working on the coding agent unless
   the user explicitly asks. The recent DB/migration and coding-agent issues are
   separate from Fastn header behavior.

## Current Git Status at Pack Creation

The working tree is intentionally dirty with the coding-agent work. Do not revert
unrelated changes.

```text
 M .env.example
 M backend/.env.production.example
 M backend/api/routes/agents.py
 M backend/core/config.py
 M backend/models/seo_task.py
 M backend/pyproject.toml
 M backend/services/seo_workspace_service.py
 M backend/uv.lock
 M frontend/src/components/seo-task-list.tsx
 M frontend/src/components/seo-workspace.tsx
 M frontend/src/lib/seo-types.ts
?? backend/agents/coding_agent.py
?? backend/alembic/versions/2c9d7f4a5b81_coding_agent_approval_statuses.py
?? backend/alembic/versions/8f31c7a2d901_coding_agent_task_state.py
?? backend/scripts/
?? backend/services/coding_agent_policy.py
?? backend/services/coding_agent_sandbox.py
?? backend/tests/test_coding_agent_policy.py
?? backend/tests/test_coding_agent_sandbox.py
?? CHAT_HANDOFF_CONTEXT.md
```

## Mental Model for Future Agents

There are three identities. Keep them separate:

- App user: the authenticated user in this SaaS app.
- Fastn end-org: the customer tenant inside Fastn, resolved from the app user.
- Fastn installation: a connector activation that must belong to that exact
  end-org.

There are also two GitHub paths:

- Fastn GitHub connector path: used by workflows to list repos/create issues for
  the connected customer's end-org.
- Coding-agent Git path: used by the backend sandbox to clone/propose/publish
  code changes for the repo saved in `site_settings`.

Do not mix those two paths unless a future feature explicitly maps Fastn OAuth
credentials into a secure git credential flow.
