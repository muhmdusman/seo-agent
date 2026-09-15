from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.dbconfig import get_db
from dependencies.auth import authenticate
from models.seo_report import SEOReport
from schemas.seo import CompletionUpdate
from services.seo_workspace_service import SEOWorkspaceService, report_json

router = APIRouter(prefix="/seo", tags=["SEO workspace"])


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
