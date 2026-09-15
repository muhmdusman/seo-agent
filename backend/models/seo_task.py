from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class SEOTask(Base):
    __tablename__ = "seo_tasks"
    __table_args__ = (
        CheckConstraint("priority IN ('critical', 'high', 'medium', 'quick-win')", name="ck_seo_task_priority"),
        CheckConstraint("stage IN ('technical-foundation', 'crawlability', 'rendering', 'indexability', 'on-page', 'content', 'search-intent', 'semantic-seo', 'ai-geo')", name="ck_seo_task_stage"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("seo_reports.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    priority: Mapped[str] = mapped_column(String(20))
    scope: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text)
    manual_fix: Mapped[str] = mapped_column(Text)
    agent_prompt: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
