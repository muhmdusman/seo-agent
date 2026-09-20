"""Add coding-agent approval lifecycle statuses."""

from alembic import op


revision = "2c9d7f4a5b81"
down_revision = "8f31c7a2d901"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_seo_task_implementation_status", "seo_tasks")
    op.create_check_constraint(
        "ck_seo_task_implementation_status", "seo_tasks",
        "implementation_status IN ('pending', 'running', 'proposed', 'applied', 'pr_created', 'blocked', 'failed')",
    )


def downgrade():
    op.drop_constraint("ck_seo_task_implementation_status", "seo_tasks")
    op.create_check_constraint(
        "ck_seo_task_implementation_status", "seo_tasks",
        "implementation_status IN ('pending', 'running', 'applied', 'blocked', 'failed')",
    )
