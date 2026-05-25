"""Add article_categories many-to-many table

Revision ID: 004_article_categories
Revises: 003_add_is_open_access
Create Date: 2025-12-27 22:11:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '004_article_categories'
down_revision: Union[str, None] = '003_add_is_open_access'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabela article_categories para relacionamento many-to-many."""

    # Verificar se a tabela já existe (pode ter sido criada automaticamente pelo SQLAlchemy)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if 'article_categories' not in tables:
        # Criar tabela article_categories
        op.create_table(
            'article_categories',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('article_id', sa.Integer(), nullable=False),
            sa.Column('category_id', sa.Integer(), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('auto_created', sa.Boolean(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('article_id', 'category_id', name='uq_article_category')
        )

    # Verificar e criar índices se não existirem
    indexes = inspector.get_indexes('article_categories') if 'article_categories' in tables else []
    index_names = [idx['name'] for idx in indexes]

    if 'ix_article_categories_article_id' not in index_names:
        op.create_index('ix_article_categories_article_id', 'article_categories', ['article_id'])

    if 'ix_article_categories_category_id' not in index_names:
        op.create_index('ix_article_categories_category_id', 'article_categories', ['category_id'])


def downgrade() -> None:
    """Remove tabela article_categories."""
    op.drop_index('ix_article_categories_category_id', table_name='article_categories')
    op.drop_index('ix_article_categories_article_id', table_name='article_categories')
    op.drop_table('article_categories')
