from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.dbconfig import get_db

from services.auth_service import AuthService
from services.google_oauth import GoogleOAuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.get("/google")
async def google_login():

    google_oauth = GoogleOAuthService()

    authorization_url = (
       google_oauth.get_authorization_url()
    )

    return RedirectResponse(
        url=authorization_url,
        status_code=302,
    )


@router.get("/google/callback")
async def google_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):

    auth_service = AuthService(db)

    user = await auth_service.login_with_google(code)

    return user