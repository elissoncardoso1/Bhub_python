"""Fix analytics metric numeric types

Revision ID: 007_fix_analytics_metric_types
Revises: 006_refresh_tokens
Create Date: 2026-03-13 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007_fix_analytics_metric_types"
down_revision: Union[str, None] = "006_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Corrige tipos para armazenar precisao decimal."""
    with op.batch_alter_table("analytics_metrics") as batch_op:
        batch_op.alter_column(
            "avg_session_duration",
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "bounce_rate",
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Reverte tipos para Integer."""
    with op.batch_alter_table("analytics_metrics") as batch_op:
        batch_op.alter_column(
            "bounce_rate",
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "avg_session_duration",
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=True,
        )
