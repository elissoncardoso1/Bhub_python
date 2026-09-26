"""Migra os feeds de periódicos em produção para a ingestão via Crossref.

Idempotente e seguro para rodar mais de uma vez. Faz **apenas** a conversão dos
registros — nenhuma requisição externa, nenhum sync, nenhuma chamada à API do
Crossref. A validação de ISSN é passo separado e deliberado
(``scripts/validate_journal_issn.py``), para que a VPS não dependa de rede
externa num passo de mudança de estado.

Uso (dry-run por padrão — só imprime o que faria):

    python -m scripts.migrate_journal_feeds_to_crossref
    python -m scripts.migrate_journal_feeds_to_crossref --apply

Antes de rodar em produção: backup do banco (``scripts/backup_db.py`` ou
``scripts/vps/backup.sh``).
"""

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.database import get_session_context
from app.models import Feed, FeedJournalSource

# Periódicos cujo RSS está bloqueado pela editora e que passam a usar o
# Crossref. ISSNs validados ao vivo em 2026-09-25 (ver ADR-0007).
CROSSREF_MIGRATION = {
    "JABA": "1938-3703",
    "JEAB": "1938-3711",
    "JOBM": "1540-8604",
    "BAP": "2196-8934",
    "Perspectives on Behavior Science": "2520-8977",
    "The Analysis of Verbal Behavior": "2196-8926",
    "Behavior and Social Issues": "2376-6786",
}

# Periódicos que saem da rotação por não publicarem mais.
DEACTIVATE = ["OBM Network News"]


def _crossref_feed_url(issn: str) -> str:
    return f"https://api.crossref.org/journals/{issn}/works"


async def migrate(apply: bool) -> int:
    async with get_session_context() as session:
        print(f"{'APLICANDO' if apply else 'DRY-RUN'} — migração para Crossref\n")
        print(f"{'ID':<5} {'PERIÓDICO':<34} {'ISSN':<12} {'AÇÃO':<28} CAMPOS")

        changed = 0
        missing: list[str] = []

        for name, issn in CROSSREF_MIGRATION.items():
            result = await session.execute(select(Feed).where(Feed.name == name))
            feed = result.scalar_one_or_none()

            if feed is None:
                missing.append(name)
                print(f"{'-':<5} {name:<34} {issn:<12} {'NÃO ENCONTRADO':<28}")
                continue

            fields: list[str] = []
            new_url = _crossref_feed_url(issn)

            if feed.journal_source is not FeedJournalSource.CROSSREF:
                feed.journal_source = FeedJournalSource.CROSSREF
                fields.append("journal_source")
            if feed.issn != issn:
                feed.issn = issn
                fields.append("issn")
            if feed.feed_url != new_url:
                feed.feed_url = new_url
                fields.append("feed_url")
            if feed.http_etag or feed.http_last_modified:
                feed.http_etag = None
                feed.http_last_modified = None
                fields.append("http_cache")
            # O error_count acumulado é da fonte antiga (RSS bloqueado) e não
            # descreve a nova. Zerar evita que o feed nasça desativado.
            if feed.error_count:
                feed.error_count = 0
                feed.last_error = None
                fields.append("error_count")

            already = feed.journal_source is FeedJournalSource.CROSSREF and not fields
            if already:
                print(f"{feed.id:<5} {name:<34} {issn:<12} {'JÁ MIGRADO':<28}")
                continue

            changed += 1
            print(
                f"{feed.id:<5} {name:<34} {issn:<12} {'migrar p/ Crossref':<28} {', '.join(fields)}"
            )

        for name in DEACTIVATE:
            result = await session.execute(select(Feed).where(Feed.name == name))
            feed = result.scalar_one_or_none()
            if feed is None:
                missing.append(name)
                print(f"{'-':<5} {name:<34} {'':<12} {'NÃO ENCONTRADO':<28}")
                continue
            if not feed.is_active:
                print(f"{feed.id:<5} {name:<34} {'':<12} {'JÁ INATIVO':<28}")
                continue
            feed.is_active = False
            changed += 1
            print(f"{feed.id:<5} {name:<34} {'':<12} {'desativar':<28} is_active")

        if apply and changed:
            await session.commit()
            print(f"\nCOMMIT: {changed} feeds alterados.")
        elif changed:
            await session.rollback()
            print(f"\nROLLBACK (dry-run): {changed} feeds seriam alterados. Use --apply.")

        if missing:
            print(f"\nATENÇÃO: não encontrados — {', '.join(missing)}")
            return 1

        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica as alterações (sem isso, apenas simula e faz rollback)",
    )
    args = parser.parse_args()
    return asyncio.run(migrate(apply=args.apply))


if __name__ == "__main__":
    sys.exit(main())
