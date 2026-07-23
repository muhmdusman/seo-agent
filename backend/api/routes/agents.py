from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agents.weekly_agent import WeeklyAgent
from db.dbconfig import get_db

router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
)


@router.get("/weekly")
async def weekly_agent(
    user_id: str,
    site_url: str,
    db: AsyncSession = Depends(get_db),
):

    agent = WeeklyAgent(db)

    async def stream():

        async for chunk in agent.run(
            user_id=user_id,
            site_url=site_url,
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
    )