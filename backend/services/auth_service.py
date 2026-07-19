from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import OAuthProvider

from services.google_oauth import GoogleOAuthService
from services.oauth_service import OAuthService
from services.user_service import UserService


class AuthService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

        self.google_service = GoogleOAuthService()

        self.user_service = UserService(db)
        self.oauth_service = OAuthService(db)

    async def login_with_google(
        self,
        code: str,
    ):

        tokens = await self.google_service.exchange_code(code)

        google_data = self.google_service.verify_id_token(
            tokens.id_token
        )

        account = await self.oauth_service.get_by_provider_user_id(
            provider_user_id=google_data.google_id,
            provider=OAuthProvider.GOOGLE,
        )

        if account:

            await self.oauth_service.update_tokens(
                account=account,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                expires_at=tokens.expires_at,
            )

            await self.db.commit()

            return account.user

        return await self.register_with_google(
            google_data,
            tokens,
        )

    async def register_with_google(
        self,
        google_data,
        tokens,
    ):

        try:

            user = await self.user_service.create(
                email=google_data.email,
            )

            await self.oauth_service.create_google_account(
                user_id=user.id,
                google_id=google_data.google_id,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                expires_at=tokens.expires_at,
            )

            await self.db.commit()

            await self.db.refresh(user)

            return user

        except Exception:

            await self.db.rollback()

            raise