"""Valida ISSNs no Crossref antes de cadastrá-los como fonte de um periódico.

Uso:

    python -m scripts.validate_journal_issn 1938-3703 2196-8934
    python -m scripts.validate_journal_issn --all          # candidatos do ADR-0007

Um ISSN errado (dígito trocado, ou o impresso no lugar do eletrônico) produz um
feed silenciosamente vazio — o modo de falha que o ADR-0006 combate. Este script
existe para que o erro apareça na curadoria, não meses depois em produção.

Sem argumentos, o exit code é 1 quando algum ISSN falha, para uso em CI.
"""

import argparse
import asyncio
import sys

from app.services.crossref_source import CrossrefSource

# Candidatos avaliados no ADR-0007. Os "existentes" são os que o script de
# seed já cadastra; os demais são ampliação sugerida, ainda não cadastrada.
CANDIDATOS = {
    # Já cadastrados / em migração
    "1938-3703": "JABA",
    "1938-3711": "JEAB",
    "1540-8604": "JOBM",
    "2196-8934": "Behavior Analysis in Practice",
    "2520-8977": "Perspectives on Behavior Science",
    "2196-8926": "The Analysis of Verbal Behavior",
    "2376-6786": "Behavior and Social Issues",
    # Ampliação — América Latina
    "2526-6551": "REBAC",
    "1982-3541": "RBTCC",
    "0188-8145": "Acta Comportamentalia",
    "0185-4534": "Revista Mexicana de Análisis de la Conducta",
    # Ampliação — internacionais
    "1072-0847": "Behavioral Interventions",
    "0145-4455": "Behavior Modification",
    "0033-2933": "The Psychological Record",
    "1053-0819": "Journal of Behavioral Education",
    "0748-8491": "Education and Treatment of Children",
    "1502-1149": "European Journal of Behavior Analysis",
    "2372-9414": "Behavior Analysis: Research and Practice",
    "0376-6357": "Behavioural Processes",
    "0005-7894": "Behavior Therapy",
    "2212-1447": "Journal of Contextual Behavioral Science",
}


async def validate(issns: list[str]) -> bool:
    """Valida cada ISSN. Retorna True se todos existirem no Crossref."""
    source = CrossrefSource()
    all_ok = True
    try:
        for issn in issns:
            expected = CANDIDATOS.get(issn)
            exists, result = await source.validate_issn(issn)
            if not exists:
                all_ok = False
                print(f"FALHA  {issn:<12} {expected or '':<38} {result}")
                continue

            label = f"(esperado: {expected})" if expected else ""
            print(f"OK     {issn:<12} {result or '':<45} {label}")
    finally:
        await source.close()

    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issns", nargs="*", help="ISSNs a validar")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Valida todos os candidatos do ADR-0007",
    )
    args = parser.parse_args()

    issns = list(CANDIDATOS) if args.all else args.issns
    if not issns:
        parser.error("informe ao menos um ISSN ou use --all")

    all_ok = asyncio.run(validate(issns))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
