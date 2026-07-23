from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.enums import OAuthProvider
from models.oauth_account import OAuthAccount
from models.oauth_credential import OAuthCredential


class OAuthService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    async def get_by_provider_user_id(
        self,
        provider_user_id: str,
        provider: OAuthProvider,
    ):

        result = await self.db.execute(
            select(OAuthAccount)
            .options(
                selectinload(OAuthAccount.user),
                selectinload(OAuthAccount.credentials),
            )
            .where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )

        return result.scalar_one_or_none()

    async def create_google_account(
        self,
        user_id,
        google_id,
        access_token,
        refresh_token,
        expires_at,
    ):

        account = OAuthAccount(
            user_id=user_id,
            provider=OAuthProvider.GOOGLE,
            provider_user_id=google_id,
        )

        self.db.add(account)

        await self.db.flush()

        credentials = OAuthCredential(
            oauth_account_id=account.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

        self.db.add(credentials)

        await self.db.flush()

        return account

    async def update_tokens(
        self,
        account: OAuthAccount,
        access_token: str,
        refresh_token: str | None,
        expires_at,
    ):

        credentials = account.credentials

        credentials.access_token = access_token

        if refresh_token:
            credentials.refresh_token = refresh_token

        credentials.expires_at = expires_at

        await self.db.flush()

        return credentials

    async def get_google_account(
        self,
        user_id,
    ):

        stmt = (
            select(OAuthAccount)
            .options(
                selectinload(OAuthAccount.user),
                selectinload(OAuthAccount.credentials),
            )
            .where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == OAuthProvider.GOOGLE,
            )
        )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()