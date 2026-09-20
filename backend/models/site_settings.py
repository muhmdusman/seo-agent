from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class SiteSettings(Base):
    __tablename__ = "site_settings"
    __table_args__ = (UniqueConstraint("user_id", "site_url", name="uq_site_settings_user_site"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    site_url: Mapped[str] = mapped_column(String(2000))
    github_owner: Mapped[str] = mapped_column(String(100), default="", server_default="")
    github_repo: Mapped[str] = mapped_column(String(200), default="", server_default="")
    google_spreadsheet_id: Mapped[str] = mapped_column(String(200), default="", server_default="")
    google_spreadsheet_name: Mapped[str] = mapped_column(String(500), default="", server_default="")
