from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.dbconfig import get_db

from dependencies.auth import authenticate
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

    # For cross-domain auth, we need to pass tokens via URL
    # Frontend will store them in localStorage
    params = urlencode(
        {
            "status": "success",
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
        }
    )

    redirect_response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/callback?{params}",
        status_code=302,
    )

    return redirect_response


@router.get("/me")
async def get_me(user=Depends(authenticate)):
    return {"user_id": user["sub"]}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"status": "ok"}
