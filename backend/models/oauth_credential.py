import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class OAuthCredential(Base, TimestampMixin):
    __tablename__ = "oauth_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    oauth_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "oauth_accounts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )

    access_token: Mapped[str] = mapped_column(
        nullable=False,
    )

    refresh_token: Mapped[str] = mapped_column(
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    oauth_account = relationship(
        "OAuthAccount",
        back_populates="credentials",
    )