"""Smoke-test manual do adaptador Crossref (usa a API real).

Não é teste automatizado: depende de rede. Uso:

    docker run --rm -v "$PWD:/app" -w /app --entrypoint python \
      bhub-backend-python-backend:latest scripts/smoke_crossref.py
"""

import asyncio
import json
import sys


async def main() -> int:
    from app.services.crossref_source import CrossrefSource

    source = CrossrefSource()
    try:
        print("=== validate_issn ===")
        for issn in ("1938-3703", "2196-8934", "9999-9999"):
            ok, info = await source.validate_issn(issn)
            print(f"  {issn}: ok={ok} -> {info}")

        print("\n=== fetch_works (BAP) ===")
        result = await source.fetch_works("2196-8934", last_successful_sync_at=None)
        print(f"  status={result.status} error={result.error}")
        if result.status.value != "ok":
            return 1

        entries = json.loads(result.text)["entries"]
        print(f"  entries={len(entries)}")
        for entry in entries[:3]:
            print("  ---")
            print(f"  id       : {entry['id']}")
            print(f"  title    : {entry['title'][:70]}")
            print(f"  published: {entry['published']}")
            print(f"  authors  : {[a['name'] for a in entry['authors']][:3]}")
            print(f"  journal  : {entry['journal']}")
            print(f"  lang     : {entry['language']}")
            print(f"  link     : {entry['link']}")
            print(f"  summary  : {(entry['summary'] or '')[:100]}")

        print("\n=== work_to_entry: entradas degeneradas ===")
        from app.services.crossref_source import work_to_entry

        cases = {
            "sem DOI": {"title": ["T"], "DOI": None},
            "sem titulo": {"title": [], "DOI": "10.1/x"},
            "data so ano": {"title": ["T"], "DOI": "10.1/y", "published": {"date-parts": [[2015]]}},
            "data ano-mes": {
                "title": ["T"],
                "DOI": "10.1/z",
                "published": {"date-parts": [[2026, 8]]},
            },
            "doi maiusculo": {"title": ["T"], "DOI": "10.1002/JABA.1"},
            "autor so name": {"title": ["T"], "DOI": "10.1/a", "author": [{"name": "Grupo X"}]},
        }
        for label, message in cases.items():
            entry = work_to_entry(message)
            if entry is None:
                print(f"  {label:<16} -> None (descartado)")
            else:
                print(
                    f"  {label:<16} -> id={entry['id']} date={entry['published']} "
                    f"authors={entry['authors']}"
                )
    finally:
        await source.close()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
