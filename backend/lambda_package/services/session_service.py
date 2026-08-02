from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.session import Session


class SessionService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    async def create_session(
        self,
        user_id: UUID,
    ) -> Session:

        session = Session(
            user_id=user_id,
            refresh_token_hash="",
            expires_at=datetime.utcnow(),
            last_used_at=datetime.utcnow(),
        )

        self.db.add(session)

        await self.db.flush()

        return session

    async def update_refresh_token(
        self,
        session: Session,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> Session:

        session.refresh_token_hash = refresh_token_hash
        session.expires_at = expires_at

        await self.db.flush()

        return session

    async def get_by_id(
        self,
        session_id: UUID,
    ) -> Session | None:

        result = await self.db.execute(
            select(Session).where(
                Session.id == session_id,
            )
        )

        return result.scalar_one_or_none()

    async def touch_session(
        self,
        session: Session,
    ) -> Session:

        session.last_used_at = datetime.utcnow()

        await self.db.flush()

        return session

    async def revoke_session(
        self,
        session: Session,
    ) -> None:

        session.revoked = True

        await self.db.flush()

    async def revoke_all_sessions(
        self,
        user_id: UUID,
    ) -> None:

        result = await self.db.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.revoked.is_(False),
            )
        )

        sessions = result.scalars().all()

        for session in sessions:
            session.revoked = True

        await self.db.flush()