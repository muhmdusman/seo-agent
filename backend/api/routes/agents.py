import asyncio
import json
import logging
from uuid import UUID

from anyio import CancelScope
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agents.weekly_agent import WeeklyAgent, STATUS_COMPLETED, STATUS_FAILED
from agents.coding_agent import CodingAgent, CodingAgentError
from core.config import settings
from db.dbconfig import AsyncSessionLocal, get_db
from dependencies.auth import authenticate
from schemas.seo import AnalysisRequest
from services.oauth_service import OAuthService
from services.search_console_service import SearchConsoleService, verified_property_match
from services.seo_workspace_service import SEOWorkspaceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/coding/{task_id}")
async def coding_agent(task_id: UUID, user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    return await propose_coding_agent(task_id, user, db)


@router.post("/coding/{task_id}/propose")
async def propose_coding_agent(task_id: UUID, user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    if not settings.CODING_AGENT_ENABLED:
        raise HTTPException(503, "The coding agent is disabled.")
    try:
        logger.info("coding_agent.route.propose.start task_id=%s user_id=%s", task_id, user["sub"])
        return await CodingAgent(db).propose_task(task_id, UUID(user["sub"]))
    except CodingAgentError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        logger.exception("Coding agent proposal failed task_id=%s user_id=%s", task_id, user["sub"])
        raise HTTPException(502, "Coding agent could not safely propose this task.") from exc


@router.post("/coding/{task_id}/approve")
async def approve_coding_agent(task_id: UUID, user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    if not settings.CODING_AGENT_ENABLED:
        raise HTTPException(503, "The coding agent is disabled.")
    try:
        logger.info("coding_agent.route.approve.start task_id=%s user_id=%s", task_id, user["sub"])
        return await CodingAgent(db).approve_task(task_id, UUID(user["sub"]))
    except CodingAgentError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        logger.exception("Coding agent approval failed task_id=%s user_id=%s", task_id, user["sub"])
        raise HTTPException(502, "Coding agent could not safely approve this task.") from exc


@router.post("/weekly")
async def weekly_agent(request: Request, body: AnalysisRequest,
                       user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    user_id = UUID(user["sub"])
    account = await OAuthService(db).get_valid_google_account(user_id)
    if account is None:
        raise HTTPException(403, "Reconnect your Google account.")
    sites = await SearchConsoleService().list_sites(account.access_token)
    search_console_site_url = verified_property_match(sites, body.site_url)
    if not search_console_site_url:
        raise HTTPException(403, "This property is not available in your Search Console account.")

    run = await SEOWorkspaceService(db).reserve_run(user_id, body)
    run_id = run.id

    async def stream():
        # The reservation is committed; slow external work owns a fresh session.
        async with AsyncSessionLocal() as stream_db:
            service = SEOWorkspaceService(stream_db)
            try:
                # A weekly run now includes bounded Daytona proposals before the
                # Fastn handoff, so allow enough time for several eligible tasks.
                async with asyncio.timeout(900 if settings.CODING_AGENT_ENABLED else 240):
                    agent = WeeklyAgent(stream_db)
                    async for chunk in agent.run(
                        user_id=str(user_id), run_id=run_id,
                        stages=run.stages,
                        phase=(run.preferences or {}).get("phase", "framework"),
                        search_console_site_url=search_console_site_url,
                        **body.model_dump(),
                    ):
                        if isinstance(chunk, dict):
                            event = chunk
                        elif chunk == STATUS_COMPLETED:
                            event = {"type": "completed", "message": chunk}
                        elif chunk == STATUS_FAILED:
                            event = {"type": "error", "message": "Review failed. Your saved report and tasks are unchanged."}
                        else:
                            event = {"type": "status", "message": chunk}
                        yield f"data: {json.dumps(event)}\n\n"
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Weekly agent stream failed")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Review stopped. Your saved work is unchanged.'})}\n\n"
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
