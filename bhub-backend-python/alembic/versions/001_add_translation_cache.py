"""Add translation cache table

Revision ID: 001_translation_cache
Revises: 
Create Date: 2025-12-15 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '001_translation_cache'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabela de cache de traduções."""
    # SQLite não tem tipo UUID nativo, então usamos String(36) para armazenar UUID como string
    op.create_table(
        'translations_cache',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('content_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('source_language', sa.String(10), nullable=False),
        sa.Column('target_language', sa.String(10), nullable=False),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('translated_text', sa.Text(), nullable=False),
        sa.Column('model', sa.String(50), nullable=False, server_default='deepseek-chat'),
        sa.Column('provider', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Criar índices
    op.create_index('idx_content_hash', 'translations_cache', ['content_hash'])
    op.create_index('idx_last_accessed', 'translations_cache', ['last_accessed_at'])
    op.create_index('idx_source_target', 'translations_cache', ['source_language', 'target_language'])


def downgrade() -> None:
    """Remove tabela de cache de traduções."""
    op.drop_index('idx_source_target', table_name='translations_cache')
    op.drop_index('idx_last_accessed', table_name='translations_cache')
    op.drop_index('idx_content_hash', table_name='translations_cache')
    op.drop_table('translations_cache')

