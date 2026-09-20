"""Store the intended platform for generated SEO tasks."""

from alembic import op
import sqlalchemy as sa


revision = "e4b8c32a9d11"
down_revision = "4745c7b2ed2e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("seo_tasks", sa.Column("target_platform", sa.String(30), nullable=False,
                                         server_default="manual_review"))
    op.create_check_constraint("ck_seo_task_target_platform", "seo_tasks",
                               "target_platform IN ('github', 'search_console', 'google_sheets', 'manual_review')")


def downgrade():
    op.drop_constraint("ck_seo_task_target_platform", "seo_tasks")
    op.drop_column("seo_tasks", "target_platform")
