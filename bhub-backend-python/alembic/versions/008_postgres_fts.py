"""Add PostgreSQL TSVector search support

Revision ID: 008_postgres_fts
Revises: 007_fix_analytics_metric_types
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "008_postgres_fts"
down_revision: Union[str, None] = "007_fix_analytics_metric_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        with op.batch_alter_table("articles") as batch_op:
            batch_op.add_column(sa.Column("search_vector", sa.Text(), nullable=True))
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS search_vector TSVECTOR")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION articles_search_vector_update()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('portuguese', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('portuguese', coalesce(NEW.abstract, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.abstract, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS articles_search_vector_trigger ON articles")
    op.execute(
        """
        CREATE TRIGGER articles_search_vector_trigger
        BEFORE INSERT OR UPDATE ON articles
        FOR EACH ROW EXECUTE FUNCTION articles_search_vector_update()
        """
    )
    op.execute(
        """
        UPDATE articles
        SET search_vector =
            setweight(to_tsvector('portuguese', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('portuguese', coalesce(abstract, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(abstract, '')), 'B')
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_search_vector "
        "ON articles USING GIN (search_vector)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_title_trgm "
        "ON articles USING GIN (title gin_trgm_ops)"
    )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_articles_title_trgm")
        op.execute("DROP INDEX IF EXISTS idx_articles_search_vector")
        op.execute("DROP TRIGGER IF EXISTS articles_search_vector_trigger ON articles")
        op.execute("DROP FUNCTION IF EXISTS articles_search_vector_update")

    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_column("search_vector")
