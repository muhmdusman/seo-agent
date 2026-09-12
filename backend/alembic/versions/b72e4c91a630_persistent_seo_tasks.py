"""Persist staged analysis runs, tasks and subtasks without altering old reports."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b72e4c91a630"
down_revision = "a80ddacd7ea9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("seo_reports", sa.Column("status", sa.String(20), nullable=False, server_default="completed"))
    op.add_column("seo_reports", sa.Column("stages", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("seo_reports", sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default="{}"))
    op.create_check_constraint("ck_seo_report_status", "seo_reports", "status IN ('running', 'completed', 'failed')")
    op.create_index("ix_seo_reports_user_site_date", "seo_reports", ["user_id", "site_url", "created_at"])
    op.create_index("uq_seo_reports_running_site", "seo_reports", ["user_id", "site_url"], unique=True, postgresql_where=sa.text("status = 'running'"))
    op.create_table(
        "seo_tasks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("report_id", sa.UUID(), sa.ForeignKey("seo_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        *[sa.Column(name, sa.Text(), nullable=False) for name in ("scope", "evidence", "why_it_matters", "manual_fix", "agent_prompt")],
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("priority IN ('critical', 'high', 'medium', 'quick-win')", name="ck_seo_task_priority"),
        sa.CheckConstraint("stage IN ('technical-foundation', 'crawlability', 'rendering', 'indexability', 'on-page', 'content', 'search-intent', 'semantic-seo', 'ai-geo')", name="ck_seo_task_stage"),
    )
    op.create_index("ix_seo_tasks_report_id", "seo_tasks", ["report_id"])
    op.create_table(
        "seo_subtasks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("task_id", sa.UUID(), sa.ForeignKey("seo_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_seo_subtasks_task_id", "seo_subtasks", ["task_id"])


def downgrade():
    op.drop_table("seo_subtasks")
    op.drop_table("seo_tasks")
    op.drop_index("uq_seo_reports_running_site", table_name="seo_reports")
    op.drop_index("ix_seo_reports_user_site_date", table_name="seo_reports")
    op.drop_constraint("ck_seo_report_status", "seo_reports")
    for column in ("preferences", "stages", "status"):
        op.drop_column("seo_reports", column)
