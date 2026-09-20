"""Store per-site GitHub repository routing settings."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f5c7d9e1a203"
down_revision = "e4b8c32a9d11"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_url", sa.String(length=2000), nullable=False),
        sa.Column("github_owner", sa.String(length=100), server_default="", nullable=False),
        sa.Column("github_repo", sa.String(length=200), server_default="", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "site_url", name="uq_site_settings_user_site"),
    )
    op.create_index("ix_site_settings_user_id", "site_settings", ["user_id"])


def downgrade():
    op.drop_index("ix_site_settings_user_id", table_name="site_settings")
    op.drop_table("site_settings")
