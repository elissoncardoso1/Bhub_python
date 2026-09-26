"""Add journal_source and issn columns to feeds

Revision ID: 010_feed_journal_source
Revises: 009_feed_http_cache
Create Date: 2026-09-25 12:00:00.000000

Suporte à ingestão de periódicos científicos pela API do Crossref (ADR-0007).

Duas colunas:
- ``journal_source``: roteia o sync entre o caminho RSS histórico e o Crossref.
  Entra com server_default='RSS' para não invalidar as 40 linhas existentes
  (todas ingerem por RSS hoje).
- ``issn``: chave de consulta no Crossref (``/journals/{issn}/works``).

O valor 'RSS' é escrito no enum com maiúsculas porque o ``Enum(FeedJournalSource)``
do SQLAlchemy persiste o **nome** do membro, seguindo ``feedtype``/``syncfrequency``.

O índice em ``issn`` cobre a consulta de diagnóstico "quais periódicos já migraram":
``WHERE journal_source='CROSSREF' AND issn IS NOT NULL``. Não é único de propósito —
dois feeds podem legitimamente apontar para o mesmo ISSN durante uma transição.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_feed_journal_source"
down_revision: str | None = "009_feed_http_cache"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

JOURNAL_SOURCE_VALUES = ("RSS", "CROSSREF")


def upgrade() -> None:
    """Adiciona a via de ingestão e o ISSN à tabela feeds."""
    journal_source = postgresql.ENUM(
        *JOURNAL_SOURCE_VALUES, name="feedjournalsource", create_type=False
    )
    journal_source.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "feeds",
        sa.Column(
            "journal_source",
            journal_source,
            nullable=False,
            server_default="RSS",
        ),
    )
    op.add_column("feeds", sa.Column("issn", sa.String(12), nullable=True))
    op.create_index("ix_feeds_issn", "feeds", ["issn"], unique=False)
    # Marcador de desativação automática por erro, que habilita a reativação
    # pela sonda de recuperação sem risco de reativar o que a curadoria desligou.
    op.add_column(
        "feeds",
        sa.Column(
            "deactivated_by_errors",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Remove a via de ingestão e o ISSN da tabela feeds."""
    op.drop_column("feeds", "deactivated_by_errors")
    op.drop_index("ix_feeds_issn", table_name="feeds")
    op.drop_column("feeds", "issn")
    op.drop_column("feeds", "journal_source")

    postgresql.ENUM(name="feedjournalsource").drop(op.get_bind(), checkfirst=True)
