import hashlib
import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.dbconfig import get_db

from dependencies.auth import authenticate
from services.auth_service import AuthService
from services.google_oauth import GoogleOAuthService
from services.jwt_service import JWTService
from services.session_service import SessionService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def _cookie_secure() -> bool:
    return settings.APP_URL.startswith("https://")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRY_DAYS,
        path="/",
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

    redirect_response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/callback?status=success",
        status_code=302,
    )
    _set_auth_cookies(
        redirect_response,
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )

    return redirect_response


@router.get("/me")
async def get_me(user=Depends(authenticate)):
    return {"user_id": user["sub"]}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = JWTService().decode_token(refresh_token)
            session_id = payload.get("sid")

            if payload.get("type") == "refresh" and session_id:
                session_service = SessionService(db)
                session = await session_service.get_by_id(UUID(session_id))

                if (
                    session
                    and hmac.compare_digest(
                        session.refresh_token_hash,
                        _hash_token(refresh_token),
                    )
                ):
                    await session_service.revoke_session(session)
                    await db.commit()
        except Exception:
            await db.rollback()

    response.delete_cookie(
        "access_token",
        path="/",
        secure=_cookie_secure(),
        samesite="lax",
    )
    response.delete_cookie(
        "refresh_token",
        path="/",
        secure=_cookie_secure(),
        samesite="lax",
    )
    return {"status": "ok"}
