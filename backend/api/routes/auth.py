from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
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

    result = await auth_service.login_with_google(
        code
    )


    params = urlencode(
        {
            "status": "success",
        }
    )


    redirect_response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/callback?{params}",
        status_code=302,
    )


    redirect_response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


    redirect_response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRY_DAYS,
    )


    return redirect_response