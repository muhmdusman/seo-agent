import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from agents.weekly_agent import WeeklyAgent
from core.config import settings
from db.dbconfig import AsyncSessionLocal
from dependencies.auth import authenticate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
)


@router.get("/weekly")
async def weekly_agent(
    request: Request,
    site_url: str,
    website_number_of_pages: str,
    website_type: str,
    user_goal: str,
    user=Depends(authenticate),
):
    """Stream a weekly SEO analysis as Server-Sent Events.

    This route deliberately does not take `db: AsyncSession = Depends(get_db)`.
    FastAPI closes dependency-provided sessions as soon as the handler returns,
    which for a StreamingResponse is *before* the generator body runs. The
    agent would then be holding a session whose transaction has already been
    torn down, and the first write attempt failed with
    "current transaction is aborted, commands ignored until end of transaction
    block". The stream owns its own session instead, for the full lifetime of
    the stream.
    """

    async def stream():
        async with AsyncSessionLocal() as db:
            agent = WeeklyAgent(db)

            try:
                async for chunk in agent.run(
                    user_id=user["sub"],
                    site_url=site_url,
                    website_number_of_pages=website_number_of_pages,
                    website_type=website_type,
                    user_goal=user_goal,
                ):
                    yield f"data: {json.dumps({'message': chunk})}\n\n"

            except Exception:
                # The generator is already streaming, so an HTTPException here
                # could not change the status code. Report in-band instead of
                # letting the connection drop with no explanation.
                logger.exception("Weekly agent stream failed")

                await db.rollback()

                message = (
                    "The analysis stopped unexpectedly. "
                    "Check the server logs for details."
                )
                yield f"data: {json.dumps({'message': message})}\n\n"
                yield f"data: {json.dumps({'message': 'Failed.'})}\n\n"

    response = StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            # Without this, a proxy may buffer the whole stream and defeat the
            # point of streaming progress.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
    new_access_token = getattr(request.state, "new_access_token", None)

    if new_access_token:
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=settings.APP_URL.startswith("https://"),
            samesite="lax",
            max_age=60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            path="/",
        )

    return response
