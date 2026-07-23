from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

from core.config import settings


class JWTService:

    def _create_token(
        self,
        data: dict,
        expires_delta: timedelta,
    ) -> str:

        payload = data.copy()

        payload["exp"] = (
            datetime.now(timezone.utc)
            + expires_delta
        )

        return jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

    def create_access_token(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> str:

        return self._create_token(
            data={
                "sub": str(user_id),
                "sid": str(session_id),
                "type": "access",
            },
            expires_delta=timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            ),
        )

    def create_refresh_token(
        self,
        session_id: UUID,
    ) -> str:

        return self._create_token(
            data={
                "sid": str(session_id),
                "type": "refresh",
            },
            expires_delta=timedelta(
                days=settings.REFRESH_TOKEN_EXPIRY_DAYS,
            ),
        )

    def decode_token(
        self,
        token: str,
    ) -> dict:

        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )


jwt_service = JWTService()