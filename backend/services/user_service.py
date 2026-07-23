import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User


class UserService:

    def __init__(self, db: AsyncSession):
        self.db = db


    async def create(
        self,
        email: str,
        username:str
    ) -> User:

        user = User(
            email=email,
            username=username
        )

        self.db.add(user)

        await self.db.flush()

        return user