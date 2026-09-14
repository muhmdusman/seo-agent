"""Enforce the nine-stage framework and map legacy lens labels into stages."""

from alembic import op
import sqlalchemy as sa


revision = "d3a4b5c6d7e8"
down_revision = "c83f20a91e64"
branch_labels = None
depends_on = None

CORE = "'technical-foundation', 'crawlability', 'rendering', 'indexability', 'on-page', 'content', 'search-intent', 'semantic-seo', 'ai-geo'"


def upgrade():
    # These labels were previously accepted as stages. Preserve every task by
    # mapping it to the core stage that owns the corresponding review lens.
    # Keep the original value in review for anything that came from an older
    # prompt/category so this migration never loses historical context.
    op.execute(sa.text(f"""
        UPDATE seo_tasks
        SET review = COALESCE(review, '{{}}'::jsonb) || jsonb_build_object(
                '_migration_legacy_stage', stage,
                '_migration_note', 'Mapped to the nine-stage SEO framework during migration'
            ),
            stage = CASE lower(stage)
                WHEN 'local-seo' THEN 'on-page'
                WHEN 'ecommerce' THEN 'on-page'
                WHEN 'international-seo' THEN 'indexability'
                WHEN 'internal-linking' THEN 'crawlability'
                WHEN 'competitor-analysis' THEN 'semantic-seo'
                WHEN 'competitor-research' THEN 'content'
                WHEN 'technical' THEN 'technical-foundation'
                WHEN 'technical-seo' THEN 'technical-foundation'
                WHEN 'crawl' THEN 'crawlability'
                WHEN 'crawlability' THEN 'crawlability'
                WHEN 'javascript' THEN 'rendering'
                WHEN 'performance' THEN 'rendering'
                WHEN 'core-web-vitals' THEN 'rendering'
                WHEN 'hreflang' THEN 'indexability'
                WHEN 'schema' THEN 'semantic-seo'
                WHEN 'keyword-research' THEN 'search-intent'
                WHEN 'keywords' THEN 'search-intent'
                WHEN 'semantic' THEN 'semantic-seo'
                WHEN 'entities' THEN 'semantic-seo'
                WHEN 'link-building' THEN 'semantic-seo'
                WHEN 'ai' THEN 'ai-geo'
                ELSE 'content'
            END
        WHERE stage NOT IN ({CORE})
    """))
    op.drop_constraint("ck_seo_task_stage", "seo_tasks")
    op.create_check_constraint("ck_seo_task_stage", "seo_tasks", f"stage IN ({CORE})")


def downgrade():
    op.drop_constraint("ck_seo_task_stage", "seo_tasks")
    op.create_check_constraint("ck_seo_task_stage", "seo_tasks", "stage ~ '^[a-z][a-z0-9-]{0,39}$'")
