"""Persist isolated coding-agent state for SEO tasks."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "8f31c7a2d901"
down_revision = "6e8c7a4f2b10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("seo_tasks", sa.Column("implementation_status", sa.String(20), nullable=False, server_default="pending"))
    op.add_column("seo_tasks", sa.Column("implementation_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("seo_tasks", sa.Column("implementation_branch", sa.String(255), nullable=False, server_default=""))
    op.add_column("seo_tasks", sa.Column("implementation_diff", sa.Text(), nullable=False, server_default=""))
    op.add_column("seo_tasks", sa.Column("implementation_result", postgresql.JSONB(), nullable=False, server_default="{}"))
    op.add_column("seo_tasks", sa.Column("implementation_error", sa.Text(), nullable=False, server_default=""))
    op.add_column("seo_tasks", sa.Column("implementation_started_at", sa.DateTime(timezone=True)))
    op.add_column("seo_tasks", sa.Column("implementation_completed_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_seo_task_implementation_status", "seo_tasks",
        "implementation_status IN ('pending', 'running', 'applied', 'blocked', 'failed')",
    )


def downgrade():
    op.drop_constraint("ck_seo_task_implementation_status", "seo_tasks")
    for column in (
        "implementation_completed_at", "implementation_started_at", "implementation_error",
        "implementation_result", "implementation_diff", "implementation_branch",
        "implementation_attempts", "implementation_status",
    ):
        op.drop_column("seo_tasks", column)
