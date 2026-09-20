import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.dbconfig import get_db
from dependencies.auth import authenticate
from models.seo_report import SEOReport
from schemas.seo import AuditSnapshotResponse, CompletionUpdate
from services.oauth_service import OAuthService
from services.search_console_service import SearchConsoleService, verified_property_match
from services.seo_workspace_service import SEOWorkspaceService, report_json
from tools.page_speed_tool import compact_core_web_vitals, fetch_core_web_vitals
from tools.source_html_tool import compact_http_headers, fetch_http_header_snapshot
from schemas.site_settings import SiteSettingsResponse, SiteSettingsUpdate
from services.site_settings_service import SiteSettingsService

router = APIRouter(prefix="/seo", tags=["SEO workspace"])


def _site_settings_json(site_url, row):
    return {
        "site_url": site_url,
        "github_repo_url": f"https://github.com/{row.github_owner}/{row.github_repo}" if row.github_owner and row.github_repo else "",
        "github_owner": row.github_owner or "",
        "github_repo": row.github_repo or "",
        "google_spreadsheet_id": row.google_spreadsheet_id or "",
        "google_spreadsheet_name": row.google_spreadsheet_name or "",
    }


@router.get("/site-settings", response_model=SiteSettingsResponse)
async def site_settings(site_url: str = Query(min_length=1, max_length=2000),
                        user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    row = await SiteSettingsService(db).get(UUID(user["sub"]), site_url)
    return _site_settings_json(site_url, row)


@router.put("/site-settings", response_model=SiteSettingsResponse)
async def update_site_settings(site_url: str = Query(min_length=1, max_length=2000),
                               body: SiteSettingsUpdate = ..., user=Depends(authenticate),
                               db: AsyncSession = Depends(get_db)):
    try:
        row = await SiteSettingsService(db).update(UUID(user["sub"]), site_url, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _site_settings_json(site_url, row)


@router.get("/sites")
async def saved_sites(response: Response, user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    sites = await db.scalars(select(SEOReport.site_url).where(
        SEOReport.user_id == UUID(user["sub"]), SEOReport.status == "completed",
    ).distinct().order_by(SEOReport.site_url))
    return {"siteEntry": [{"siteUrl": site, "permissionLevel": "saved"} for site in sites]}


@router.get("/workspace")
async def workspace(response: Response, site_url: str = Query(min_length=1, max_length=2000),
                    user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return await SEOWorkspaceService(db).workspace(UUID(user["sub"]), site_url)


@router.get("/audit-snapshot", response_model=AuditSnapshotResponse)
async def audit_snapshot(response: Response, site_url: str = Query(min_length=1, max_length=2000),
                         user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    user_id = UUID(user["sub"])
    account = await OAuthService(db).get_valid_google_account(user_id)
    if account is None:
        raise HTTPException(403, "Reconnect your Google account.")
    sites = await SearchConsoleService().list_sites(account.access_token)
    if not verified_property_match(sites, site_url):
        raise HTTPException(403, "This property is not available in your Search Console account.")

    core_web_vitals, http_headers = await asyncio.gather(
        fetch_core_web_vitals(site_url),
        fetch_http_header_snapshot(site_url),
    )
    compact_context = {
        "core_web_vitals": compact_core_web_vitals(core_web_vitals),
        "http_headers": compact_http_headers(http_headers),
    }
    return {
        "site_url": site_url,
        "url": core_web_vitals.get("url") or http_headers.get("requested_url") or site_url,
        "collected_at": core_web_vitals.get("collected_at") or http_headers.get("checked_at"),
        "core_web_vitals": core_web_vitals,
        "http_headers": http_headers,
        "compact_context": compact_context,
    }


@router.get("/reports")
async def reports(response: Response, site_url: str = Query(min_length=1, max_length=2000),
                  offset: int = Query(default=0, ge=0), limit: int = Query(default=10, ge=1, le=20),
                  user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    rows = list(await db.scalars(select(SEOReport).where(
        SEOReport.user_id == UUID(user["sub"]), SEOReport.site_url == site_url, SEOReport.status == "completed",
    ).order_by(SEOReport.created_at.desc(), SEOReport.id.desc()).offset(offset).limit(limit + 1)))
    return {"reports": [report_json(row) for row in rows[:limit]],
            "next_offset": offset + limit if len(rows) > limit else None}


@router.get("/reports/{report_id}")
async def report(report_id: UUID, response: Response, user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    row = await db.scalar(select(SEOReport).where(
        SEOReport.id == report_id, SEOReport.user_id == UUID(user["sub"]), SEOReport.status == "completed",
    ))
    if row is None:
        raise HTTPException(404, "Report not found.")
    return report_json(row)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: UUID, body: CompletionUpdate,
                      user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    return await SEOWorkspaceService(db).set_completion(UUID(user["sub"]), task_id, body.completed)


@router.patch("/tasks/{task_id}/subtasks/{subtask_id}")
async def update_subtask(task_id: UUID, subtask_id: UUID, body: CompletionUpdate,
                         user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    return await SEOWorkspaceService(db).set_completion(UUID(user["sub"]), task_id, body.completed, subtask_id)
