"""Keep SEO categories open and persist observations separately from completion."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c83f20a91e64"
down_revision = "b72e4c91a630"
branch_labels = None
depends_on = None

LEGACY = "'technical-foundation', 'crawlability', 'rendering', 'indexability', 'on-page', 'content', 'search-intent', 'semantic-seo', 'ai-geo'"


def upgrade():
    op.drop_constraint("ck_seo_task_stage", "seo_tasks")
    op.create_check_constraint("ck_seo_task_stage", "seo_tasks", "stage ~ '^[a-z][a-z0-9-]{0,39}$'")
    op.add_column("seo_reports", sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default="{}"))
    op.add_column("seo_tasks", sa.Column("verification", postgresql.JSONB(), nullable=True))
    op.add_column("seo_tasks", sa.Column("review", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade():
    if op.get_bind().execute(sa.text(f"SELECT 1 FROM seo_tasks WHERE stage NOT IN ({LEGACY}) LIMIT 1")).first():
        raise RuntimeError("New SEO categories exist. Export and deliberately reconcile them before downgrading.")
    op.drop_column("seo_tasks", "review")
    op.drop_column("seo_tasks", "verification")
    op.drop_column("seo_reports", "evidence")
    op.drop_constraint("ck_seo_task_stage", "seo_tasks")
    op.create_check_constraint("ck_seo_task_stage", "seo_tasks", f"stage IN ({LEGACY})")
