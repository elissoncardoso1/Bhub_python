"""Add is_open_access field to articles

Revision ID: 003_add_is_open_access
Revises: 002_analytics_tables
Create Date: 2025-12-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '003_add_is_open_access'
down_revision: Union[str, None] = '002_analytics_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona campo is_open_access à tabela articles."""

    # Adicionar coluna is_open_access
    op.add_column(
        'articles',
        sa.Column('is_open_access', sa.Boolean(), nullable=False, server_default='0')
    )

    # Criar índice para busca/filtro por open access
    op.create_index('ix_articles_is_open_access', 'articles', ['is_open_access'])


def downgrade() -> None:
    """Remove campo is_open_access da tabela articles."""
    op.drop_index('ix_articles_is_open_access', table_name='articles')
    op.drop_column('articles', 'is_open_access')
