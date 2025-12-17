"""Add analytics tables

Revision ID: 002_analytics_tables
Revises: 001_translation_cache
Create Date: 2025-12-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '002_analytics_tables'
down_revision: Union[str, None] = '001_translation_cache'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabelas de analytics."""
    
    # Tabela de eventos de analytics
    op.create_table(
        'analytics_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_name', sa.String(255), nullable=False),
        sa.Column('properties', sa.Text(), nullable=True),
        sa.Column('page_path', sa.String(500), nullable=True),
        sa.Column('referrer', sa.String(500), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Tabela de sessões de analytics
    op.create_table(
        'analytics_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(255), nullable=False, unique=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        sa.Column('country', sa.String(2), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('page_views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('events_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Tabela de métricas agregadas
    op.create_table(
        'analytics_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('metric_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('total_visitors', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_sessions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_page_views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unique_visitors', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('article_views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('article_downloads', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('searches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_session_duration', sa.Float(), nullable=True),
        sa.Column('bounce_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Criar índices
    op.create_index('ix_analytics_events_session_id', 'analytics_events', ['session_id'])
    op.create_index('ix_analytics_events_user_id', 'analytics_events', ['user_id'])
    op.create_index('ix_analytics_events_event_type', 'analytics_events', ['event_type'])
    op.create_index('ix_analytics_events_timestamp', 'analytics_events', ['timestamp'])
    op.create_index('ix_analytics_events_type_timestamp', 'analytics_events', ['event_type', 'timestamp'])
    op.create_index('ix_analytics_events_session_timestamp', 'analytics_events', ['session_id', 'timestamp'])
    
    op.create_index('ix_analytics_sessions_session_id', 'analytics_sessions', ['session_id'])
    op.create_index('ix_analytics_sessions_user_id', 'analytics_sessions', ['user_id'])
    op.create_index('ix_analytics_sessions_status', 'analytics_sessions', ['status'])
    op.create_index('ix_analytics_sessions_started_at', 'analytics_sessions', ['started_at'])
    
    op.create_index('ix_analytics_metrics_metric_date', 'analytics_metrics', ['metric_date'])
    op.create_index('ix_analytics_metrics_period_type', 'analytics_metrics', ['period_type'])
    op.create_index('ix_analytics_metrics_date_period', 'analytics_metrics', ['metric_date', 'period_type'])


def downgrade() -> None:
    """Remove tabelas de analytics."""
    op.drop_index('ix_analytics_metrics_date_period', table_name='analytics_metrics')
    op.drop_index('ix_analytics_metrics_period_type', table_name='analytics_metrics')
    op.drop_index('ix_analytics_metrics_metric_date', table_name='analytics_metrics')
    
    op.drop_index('ix_analytics_sessions_started_at', table_name='analytics_sessions')
    op.drop_index('ix_analytics_sessions_status', table_name='analytics_sessions')
    op.drop_index('ix_analytics_sessions_user_id', table_name='analytics_sessions')
    op.drop_index('ix_analytics_sessions_session_id', table_name='analytics_sessions')
    
    op.drop_index('ix_analytics_events_session_timestamp', table_name='analytics_events')
    op.drop_index('ix_analytics_events_type_timestamp', table_name='analytics_events')
    op.drop_index('ix_analytics_events_timestamp', table_name='analytics_events')
    op.drop_index('ix_analytics_events_event_type', table_name='analytics_events')
    op.drop_index('ix_analytics_events_user_id', table_name='analytics_events')
    op.drop_index('ix_analytics_events_session_id', table_name='analytics_events')
    
    op.drop_table('analytics_metrics')
    op.drop_table('analytics_sessions')
    op.drop_table('analytics_events')

