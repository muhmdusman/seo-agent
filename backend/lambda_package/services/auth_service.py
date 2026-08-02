import hashlib

from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import OAuthProvider
from services.google_oauth import GoogleOAuthService
from services.oauth_service import OAuthService
from services.user_service import UserService
from services.session_service import SessionService
from services.jwt_service import JWTService
from core.config import settings


class AuthService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

        self.google_service = GoogleOAuthService()

        self.user_service = UserService(db)
        self.oauth_service = OAuthService(db)
        self.session_service = SessionService(db)

        self.jwt_service = JWTService()

    


    def hash_token(
        self,
        token: str,
    ) -> str:

        return hashlib.sha256(
            token.encode()
        ).hexdigest()

    def get_refresh_expiry(self):

        return (
        datetime.now(timezone.utc)
        + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRY_DAYS
        )
        )
    
    async def login_with_google(
        self,
        code: str,
    ):

        # 1. Exchange Google authorization code
        google_tokens = await self.google_service.exchange_code(
            code
        )


        # 2. Verify Google identity
        google_data = self.google_service.verify_id_token(
            google_tokens.id_token
        )


        # 3. Find existing Google account
        account = await self.oauth_service.get_by_provider_user_id(
            provider_user_id=google_data.google_id,
            provider=OAuthProvider.GOOGLE,
        )


        if account:

            # Update Google credentials
            await self.oauth_service.update_tokens(
                account=account,
                access_token=google_tokens.access_token,
                refresh_token=google_tokens.refresh_token,
                expires_at=google_tokens.expires_at,
            )

            user = account.user


        else:

            # Create new user + Google account
            user = await self.register_with_google(
                google_data,
                google_tokens,
            )


        # 4. Create application session
        session = await self.session_service.create_session(
            user_id=user.id,
        )


        # 5. Create refresh token
        refresh_token = self.jwt_service.create_refresh_token(
            session_id=session.id,
        )


        refresh_token_hash = self.hash_token(
            refresh_token
        )


        # 6. Store refresh token hash
        await self.session_service.update_refresh_token(
    session=session,
    refresh_token_hash=refresh_token_hash,
    expires_at=self.get_refresh_expiry(),
)


        # 7. Create access token
        access_token = self.jwt_service.create_access_token(
            user_id=user.id,
            session_id=session.id,
        )


        await self.db.commit()


        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }



    async def register_with_google(
        self,
        google_data,
        google_tokens,
    ):

        try:
            print(
    "GOOGLE DATA:",
    google_data.model_dump()
)
            user = await self.user_service.create(
                email=google_data.email,
                username=google_data.username,
            )


            await self.oauth_service.create_google_account(
                user_id=user.id,
                google_id=google_data.google_id,
                access_token=google_tokens.access_token,
                refresh_token=google_tokens.refresh_token,
                expires_at=google_tokens.expires_at,
            )


            await self.db.flush()


            return user


        except Exception:

            await self.db.rollback()

            raise