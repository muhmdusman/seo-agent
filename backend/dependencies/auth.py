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



async def authenticate(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Try Authorization header first (for localStorage-based auth)
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
            # Fall through to cookie-based auth
    
    # Fall back to cookie-based auth (legacy)
    access_token = request.cookies.get("access_token")

    # CASE 1: Access token exists in cookies
    if access_token:
        try:
            payload = jwt_service.decode_token(access_token)
            
            if payload.get("type") != "access":
                raise Exception("Wrong token type")

            request.state.user = payload
            return payload

        except Exception as e:
            print(f"Access token from cookie failed: {repr(e)}")

    # CASE 2: Refresh token flow (cookie-based only)
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

        session_service = SessionService(db)
        session = await session_service.get_by_id(session_id)

        if not session or session.revoked:
            raise Exception("Invalid session")

        new_access_token = jwt_service.create_access_token(
            user_id=session.user_id,
            session_id=session.id,
        )

        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )

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