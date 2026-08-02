import uuid
from sqlalchemy import Enum

from core.enums import OAuthProvider
from sqlalchemy import UniqueConstraint




from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class OAuthAccount(Base, TimestampMixin):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_provider_user",
        ),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    provider: Mapped[OAuthProvider] = mapped_column(
    Enum(OAuthProvider),
    nullable=False,
    )

    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    user = relationship(
        "User",
        back_populates="oauth_accounts",
    )

    credentials = relationship(
    "OAuthCredential",
    back_populates="oauth_account",
    uselist=False,
    cascade="all, delete-orphan",
    )