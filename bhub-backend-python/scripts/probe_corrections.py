"""Verifica o formato real dos títulos de correção/retratação no Crossref.

Uso pontual, quando se suspeita que o filtro ``_CORRECTION_TITLE_PATTERN``
(``app/services/crossref_source.py``) está desatualizado:

    docker run --rm -v "$PWD:/app" -w /app --entrypoint python \
      bhub-backend-python-backend:latest scripts/probe_corrections.py

Os títulos que este script imprime estão transcritos em
``tests/test_crossref_source.py``; se o formato mudar, o teste falha primeiro.
"""

import asyncio
import sys

import httpx

from app.config import settings

# Periódicos com correções conhecidas no corpus, para a amostra ser útil.
PERIODICOS = (
    ("2196-8934", "Behavior Analysis in Practice"),
    ("1938-3703", "Journal of Applied Behavior Analysis"),
    ("2520-8977", "Perspectives on Behavior Science"),
)


async def main() -> None:
    async with httpx.AsyncClient(
        timeout=30, headers={"User-Agent": settings.crossref_user_agent}
    ) as client:
        for issn, nome in PERIODICOS:
            response = await client.get(
                f"https://api.crossref.org/journals/{issn}/works",
                params={
                    "query.bibliographic": "correction",
                    "rows": 8,
                    "select": "DOI,title,type,published",
                    "mailto": settings.crossref_mailto,
                },
            )
            print(f"=== {nome} ({issn}) — HTTP {response.status_code} ===")
            if response.status_code != 200:
                print(f"      {response.text[:160]}")
                continue
            for item in response.json()["message"]["items"]:
                title = (item.get("title") or [""])[0]
                print(f"  [{item.get('type'):<16}] {title[:88]!r}")


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
