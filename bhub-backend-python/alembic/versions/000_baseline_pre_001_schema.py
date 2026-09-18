"""Baseline do schema anterior a 001 — a cadeia não criava estas tabelas

Revision ID: 000_baseline
Revises:
Create Date: 2026-09-17 00:00:00.000000

Motivo (Task 12 / T4.1 ``Alembic zero -> head``): a cadeia ia de
``001_translation_cache`` (``down_revision = None``) até ``009_feed_http_cache`` e
ASSUMIA um schema pré-existente — nenhuma migração criava ``articles``, ``users``,
``feeds``, ``categories``, ``authors`` e companhia. Por isso
``alembic upgrade head`` num banco VAZIO falhava em ``003_add_is_open_access`` com
``UndefinedTableError: relation "articles" does not exist``, e num banco criado por
``Base.metadata.create_all`` falhava já na ``001`` com
``DuplicateTableError: relation "translations_cache" already exists``. Esta baseline
cria exatamente as 9 tabelas que existiam antes da 001.

Ficam FORA daqui de propósito, porque as migrações posteriores as criam com
``op.add_column`` SEM guard (recriá-las aqui quebraria a cadeia):
  - ``articles.is_open_access`` e o índice ``ix_articles_is_open_access`` -> 003
  - ``feeds.http_etag`` / ``feeds.http_last_modified`` -> 009
Também fora: ``articles.search_vector`` (-> 008) e ``idx_articles_title_trgm``, que
usa a operator class ``gin_trgm_ops`` — a extensão ``pg_trgm`` só é criada na 008,
logo criar esse índice aqui falharia.

NOTA DE OPERAÇÃO (para um banco que JÁ existe): um banco cujo schema foi criado por
``Base.metadata.create_all`` (o caminho que a produção percorre hoje, porque
``scripts/vps/deploy.sh`` engole o erro do alembic) tem as tabelas mas NÃO tem
``alembic_version``. O remédio NÃO é ``alembic stamp 000_baseline``: esse banco já
contém as tabelas de 001-009, então o ``upgrade head`` seguinte tenta recriá-las e
falha na 001 com ``DuplicateTableError: relation "translations_cache" already exists``,
deixando ``alembic_version`` travado em ``000_baseline``. Sem stamp algum o
``upgrade head`` falha antes, aqui dentro desta baseline, com
``DuplicateTableError: relation "authors" already exists``. O comando correto é
``alembic stamp head`` seguido de ``alembic upgrade head``, e ele só deve ser aplicado
DEPOIS de verificar que o schema existente corresponde de fato ao head esperado — o
schema de ``create_all`` carrega drift conhecido em relação à cadeia. Nas duas
variantes erradas acima o erro é SILENCIOSO em produção: ``deploy.sh`` e ``update.sh``
convertem o rc≠0 em ``warning`` e o deploy segue, então um remédio errado parece
aplicado enquanto o banco continua sem ``alembic_version``.
"""

from typing import Sequence, Union

import fastapi_users_db_sqlalchemy.generics  # tipo GUID() da coluna users.id
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria as 9 tabelas que existiam antes da migração 001."""
    op.create_table(
        "authors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("orcid", sa.String(length=50), nullable=True),
        sa.Column("affiliation", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("article_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("orcid"),
    )
    op.create_index(op.f("ix_authors_name"), "authors", ["name"], unique=False)
    op.create_index(op.f("ix_authors_normalized_name"), "authors", ["normalized_name"], unique=True)
    op.create_table(
        "banners",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("link_url", sa.String(length=500), nullable=True),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column(
            "position",
            sa.Enum("HEADER", "SIDEBAR", "BETWEEN_ARTICLES", "FOOTER", name="bannerposition"),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_banners_is_active"), "banners", ["is_active"], unique=False)
    op.create_index(op.f("ix_banners_position"), "banners", ["position"], unique=False)
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=True)
    op.create_table(
        "contact_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("UNREAD", "READ", "REPLIED", "ARCHIVED", name="messagestatus"),
            nullable=False,
        ),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reply_message", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contact_messages_email"), "contact_messages", ["email"], unique=False)
    op.create_index(
        op.f("ix_contact_messages_status"), "contact_messages", ["status"], unique=False
    )
    op.create_table(
        "feeds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("journal_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("feed_url", sa.String(length=500), nullable=False),
        sa.Column(
            "feed_type",
            sa.Enum("RSS", "ATOM", "SCRAPING", "PDF", "INTERNAL", name="feedtype"),
            nullable=False,
        ),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "sync_frequency",
            sa.Enum("HOURLY", "DAILY", "WEEKLY", "MANUAL", name="syncfrequency"),
            nullable=False,
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("max_errors", sa.Integer(), nullable=False),
        sa.Column("total_articles", sa.Integer(), nullable=False),
        sa.Column("articles_last_sync", sa.Integer(), nullable=False),
        sa.Column("custom_headers", sa.Text(), nullable=True),
        sa.Column("scraping_selectors", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_url"),
    )
    op.create_index(op.f("ix_feeds_is_active"), "feeds", ["is_active"], unique=False)
    op.create_table(
        "users",
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.Enum("USER", "ADMIN", name="userrole"), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", fastapi_users_db_sqlalchemy.generics.GUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("doi", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("title_translated", sa.String(length=500), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("abstract_translated", sa.Text(), nullable=True),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("original_url", sa.String(length=500), nullable=True),
        sa.Column("pdf_url", sa.String(length=500), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("journal_name", sa.String(length=255), nullable=True),
        sa.Column("volume", sa.String(length=50), nullable=True),
        sa.Column("issue", sa.String(length=50), nullable=True),
        sa.Column("pages", sa.String(length=50), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("impact_score", sa.Float(), nullable=False),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("highlighted", sa.Boolean(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("RSS", "SCRAPING", "PDF", "MANUAL", name="sourcetype"),
            nullable=False,
        ),
        sa.Column("feed_id", sa.Integer(), nullable=True),
        sa.Column("pdf_file_path", sa.String(length=500), nullable=True),
        sa.Column("pdf_file_size", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("translation_cache", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["feed_id"],
            ["feeds.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_articles_category_date", "articles", ["category_id", "publication_date"], unique=False
    )
    op.create_index(op.f("ix_articles_category_id"), "articles", ["category_id"], unique=False)
    op.create_index(op.f("ix_articles_doi"), "articles", ["doi"], unique=True)
    op.create_index(op.f("ix_articles_external_id"), "articles", ["external_id"], unique=True)
    op.create_index(
        "ix_articles_feed_date", "articles", ["feed_id", "publication_date"], unique=False
    )
    op.create_index(op.f("ix_articles_feed_id"), "articles", ["feed_id"], unique=False)
    op.create_index(op.f("ix_articles_highlighted"), "articles", ["highlighted"], unique=False)
    op.create_index(
        "ix_articles_highlighted_date",
        "articles",
        ["highlighted", "publication_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_articles_publication_date"), "articles", ["publication_date"], unique=False
    )
    op.create_table(
        "article_authors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", "author_id", name="uq_article_author"),
    )
    op.create_table(
        "pdf_metadata",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("thumbnail_path", sa.String(length=500), nullable=True),
        sa.Column("pdf_info", sa.Text(), nullable=True),
        sa.Column(
            "processing_status",
            sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="processingstatus"),
            nullable=False,
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id"),
        sa.UniqueConstraint("file_hash"),
    )


def downgrade() -> None:
    """Remove as tabelas da baseline e as enumerações que elas criaram."""
    op.drop_table("pdf_metadata")
    op.drop_table("article_authors")
    op.drop_table("articles")
    op.drop_table("users")
    op.drop_table("feeds")
    op.drop_table("contact_messages")
    op.drop_table("categories")
    op.drop_table("banners")
    op.drop_table("authors")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS bannerposition")
    op.execute("DROP TYPE IF EXISTS processingstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS messagestatus")
    op.execute("DROP TYPE IF EXISTS feedtype")
    op.execute("DROP TYPE IF EXISTS syncfrequency")
