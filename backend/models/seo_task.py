from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


CORE_STAGE_SQL = "'technical-foundation', 'crawlability', 'rendering', 'indexability', 'on-page', 'content', 'search-intent', 'semantic-seo', 'ai-geo'"


class SEOTask(Base):
    __tablename__ = "seo_tasks"
    __table_args__ = (
        CheckConstraint("priority IN ('critical', 'high', 'medium', 'quick-win')", name="ck_seo_task_priority"),
        CheckConstraint(f"stage IN ({CORE_STAGE_SQL})", name="ck_seo_task_stage"),
        CheckConstraint(
            "implementation_status IN ('pending', 'running', 'proposed', 'applied', 'pr_created', 'blocked', 'failed')",
            name="ck_seo_task_implementation_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("seo_reports.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    priority: Mapped[str] = mapped_column(String(20))
    target_platform: Mapped[str] = mapped_column(String(30), default="manual_review", server_default="manual_review")
    scope: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text)
    manual_fix: Mapped[str] = mapped_column(Text)
    agent_prompt: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    review: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    implementation_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False,
    )
    implementation_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    implementation_branch: Mapped[str] = mapped_column(String(255), default="", server_default="", nullable=False)
    implementation_diff: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    implementation_result: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    implementation_error: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    implementation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    implementation_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report = relationship("SEOReport")
    subtasks: Mapped[list["SEOSubtask"]] = relationship(
        cascade="all, delete-orphan", order_by="SEOSubtask.position", lazy="raise",
    )


class SEOSubtask(Base):
    __tablename__ = "seo_subtasks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("seo_tasks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
