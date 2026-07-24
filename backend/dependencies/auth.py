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
    print("COOKIES RECEIVED:", request.cookies)

    access_token = request.cookies.get(
        "access_token"
    )


    # CASE 1:
    # Access token exists

    if access_token:

        try:

            payload = jwt_service.decode_token(
                access_token
            )

            print("DECODED PAYLOAD:", payload)  
            if payload.get("type") != "access":
                print("WRONG TOKEN TYPE")
                raise Exception()


            request.state.user = payload

            return payload


        except Exception as e:

            print("ACCESS TOKEN FAILED:", repr(e))



    # CASE 2:
    # Refresh token flow


    refresh_token = request.cookies.get(
        "refresh_token"
    )


    if not refresh_token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )


    try:

        payload = jwt_service.decode_token(
            refresh_token
        )


        if payload.get("type") != "refresh":

            raise Exception()


        session_id = payload.get(
            "sid"
        )


        session_service = SessionService(
            db
        )


        session = await session_service.get_by_id(
            session_id
        )


        if not session:

            raise Exception()


        if session.revoked:

            raise Exception()



        new_access_token = (
            jwt_service.create_access_token(
                user_id=session.user_id,
                session_id=session.id,
            )
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



    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
        )