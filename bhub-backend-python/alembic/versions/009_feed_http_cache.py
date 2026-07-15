"""Add HTTP conditional-GET cache columns to feeds

Revision ID: 009_feed_http_cache
Revises: 008_postgres_fts
Create Date: 2026-07-04 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_feed_http_cache"
down_revision: Union[str, None] = "008_postgres_fts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona colunas de cache HTTP (ETag / Last-Modified) à tabela feeds."""
    op.add_column("feeds", sa.Column("http_etag", sa.String(255), nullable=True))
    op.add_column("feeds", sa.Column("http_last_modified", sa.String(64), nullable=True))


def downgrade() -> None:
    """Remove colunas de cache HTTP da tabela feeds."""
    op.drop_column("feeds", "http_last_modified")
    op.drop_column("feeds", "http_etag")
