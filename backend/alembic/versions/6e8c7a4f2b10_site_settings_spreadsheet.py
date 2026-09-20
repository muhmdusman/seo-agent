"""Store per-site Google Sheets routing settings."""

from alembic import op
import sqlalchemy as sa


revision = "6e8c7a4f2b10"
down_revision = "f5c7d9e1a203"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade():
    if not _has_column("site_settings", "google_spreadsheet_id"):
        op.add_column(
            "site_settings",
            sa.Column("google_spreadsheet_id", sa.String(length=200), server_default="", nullable=False),
        )
    if not _has_column("site_settings", "google_spreadsheet_name"):
        op.add_column(
            "site_settings",
            sa.Column("google_spreadsheet_name", sa.String(length=500), server_default="", nullable=False),
        )


def downgrade():
    if _has_column("site_settings", "google_spreadsheet_name"):
        op.drop_column("site_settings", "google_spreadsheet_name")
    if _has_column("site_settings", "google_spreadsheet_id"):
        op.drop_column("site_settings", "google_spreadsheet_id")
