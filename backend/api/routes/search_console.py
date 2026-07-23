from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from db.dbconfig import get_db
from dependencies.auth import authenticate
from services.oauth_service import OAuthService
from services.search_console_service import SearchConsoleService


router = APIRouter(
    prefix="/search-console",
    tags=["Search Console"],
)


@router.get("/sites")
async def list_sites(
    user=Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):

    user_id = UUID(user["sub"])

    print("Authenticated user:", user)


    oauth_service = OAuthService(db)

    account = await oauth_service.get_google_account(
        user_id=user_id,
    )


    if account is None:

        raise HTTPException(
            status_code=404,
            detail="Google account not found.",
        )


    service = SearchConsoleService()

    return await service.list_sites(
        account.credentials.access_token,
    )