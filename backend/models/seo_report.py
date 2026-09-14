from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class SEOReport(Base):
    __tablename__ = "seo_reports"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'completed', 'failed')", name="ck_seo_report_status"),
        Index("ix_seo_reports_user_site_date", "user_id", "site_url", "created_at"),
        Index("uq_seo_reports_running_site", "user_id", "site_url", unique=True,
              postgresql_where=text("status = 'running'")),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    site_url: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    report: Mapped[str] = mapped_column(
        JSONB,
        nullable=False,
    )

    summary: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(20), default="completed", server_default="completed")
    stages: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    user = relationship(
        "User",
        back_populates="seo_reports",
    )
