import hashlib
import hmac
from datetime import datetime, timezone
from uuid import UUID

from fastapi import (
    Request,
    Depends,
    HTTPException,
    status,
    Response,
)

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.dbconfig import get_db

from services.jwt_service import JWTService
from services.session_service import SessionService


jwt_service = JWTService()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _cookie_secure() -> bool:
    return settings.APP_URL.startswith("https://")


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return expires_at <= datetime.now(timezone.utc)


async def authenticate(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    access_token = request.cookies.get("access_token")

    if access_token:
        try:
            payload = jwt_service.decode_token(access_token)
            
            if payload.get("type") != "access":
                raise Exception("Wrong token type")

            request.state.user = payload
            return payload

        except Exception as e:
            print(f"Access token from cookie failed: {repr(e)}")

    # Temporary compatibility for old browser sessions created before the
    # cookie migration. New frontend requests do not send this header.
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        access_token = auth_header.split(" ")[1]

        try:
            payload = jwt_service.decode_token(access_token)

            if payload.get("type") != "access":
                raise Exception("Wrong token type")

            request.state.user = payload
            return payload

        except Exception as e:
            print(f"Authorization header token failed: {repr(e)}")

    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        payload = jwt_service.decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise Exception("Wrong token type")

        session_id = payload.get("sid")
        if not session_id:
            raise Exception("Missing session id")

        session_service = SessionService(db)
        session = await session_service.get_by_id(UUID(session_id))

        if not session or session.revoked:
            raise Exception("Invalid session")

        if _is_expired(session.expires_at):
            raise Exception("Session expired")

        if not hmac.compare_digest(
            session.refresh_token_hash,
            _hash_token(refresh_token),
        ):
            raise Exception("Refresh token does not match session")

        new_access_token = jwt_service.create_access_token(
            user_id=session.user_id,
            session_id=session.id,
        )

        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=_cookie_secure(),
            samesite="lax",
            max_age=60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            path="/",
        )
        request.state.new_access_token = new_access_token

        await session_service.touch_session(session)
        await db.commit()

        request.state.user = {
            "sub": str(session.user_id),
            "sid": str(session.id),
            "type": "access",
        }

        return request.state.user

    except Exception as e:
        print(f"Refresh token failed: {repr(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
        )
