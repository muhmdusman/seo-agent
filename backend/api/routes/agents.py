import asyncio
import json
import logging
from uuid import UUID

from anyio import CancelScope
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agents.weekly_agent import WeeklyAgent, STATUS_COMPLETED, STATUS_FAILED
from core.config import settings
from db.dbconfig import AsyncSessionLocal, get_db
from dependencies.auth import authenticate
from schemas.seo import AnalysisRequest
from services.oauth_service import OAuthService
from services.search_console_service import SearchConsoleService
from services.seo_workspace_service import SEOWorkspaceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/weekly")
async def weekly_agent(request: Request, body: AnalysisRequest,
                       user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    user_id = UUID(user["sub"])
    account = await OAuthService(db).get_valid_google_account(user_id)
    if account is None:
        raise HTTPException(403, "Reconnect your Google account.")
    sites = await SearchConsoleService().list_sites(account.access_token)
    if not any(site.get("siteUrl") == body.site_url and site.get("permissionLevel") != "siteUnverifiedUser"
               for site in sites.get("siteEntry", [])):
        raise HTTPException(403, "This property is not available in your Search Console account.")

    run = await SEOWorkspaceService(db).reserve_run(user_id, body)
    run_id, stages = run.id, run.stages

    async def stream():
        # The reservation is committed; slow external work owns a fresh session.
        async with AsyncSessionLocal() as stream_db:
            service = SEOWorkspaceService(stream_db)
            try:
                async with asyncio.timeout(240):
                    agent = WeeklyAgent(stream_db)
                    async for chunk in agent.run(
                        user_id=str(user_id), run_id=run_id, stages=stages,
                        **body.model_dump(),
                    ):
                        if isinstance(chunk, dict):
                            event = chunk
                        elif chunk == STATUS_COMPLETED:
                            event = {"type": "completed", "message": chunk}
                        elif chunk == STATUS_FAILED:
                            event = {"type": "error", "message": "Analysis failed. Your saved report and tasks are unchanged."}
                        else:
                            event = {"type": "status", "message": chunk}
                        yield f"data: {json.dumps(event)}\n\n"
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Weekly agent stream failed")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Analysis stopped. Your saved work is unchanged.'})}\n\n"
            finally:
                # A killed process is recovered by the reservation TTL.
                # This conditional update leaves successful runs intact.
                with CancelScope(shield=True):
                    await service.fail_run(run_id)

    response = StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-store", "X-Accel-Buffering": "no",
    })
    new_access_token = getattr(request.state, "new_access_token", None)
    if new_access_token:
        response.set_cookie(
            key="access_token", value=new_access_token, httponly=True,
            secure=settings.APP_URL.startswith("https://"), samesite="lax",
            max_age=60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES, path="/",
        )
    return response
