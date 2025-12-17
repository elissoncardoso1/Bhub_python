"""
Sistema de avaliação de impacto de artigos.
"""

import re

from app.core.logging import log


class ImpactRatingService:
    """
    Serviço para avaliar impacto de artigos científicos.
    Score de 1-10 baseado em múltiplos fatores.
    """

    # Palavras que indicam alto impacto
    HIGH_IMPACT_KEYWORDS = [
        # Metodológicos
        "meta-analysis", "meta-análise", "systematic review", "revisão sistemática",
        "randomized", "randomizado", "controlled trial", "ensaio controlado",
        "longitudinal", "multicenter", "multicêntrico",
        # Resultados
        "breakthrough", "novel", "innovative", "inovador",
        "significant", "significativo", "effective", "eficaz",
        "first", "primeiro", "new approach", "nova abordagem",
        # Escala
        "large-scale", "nationwide", "international", "internacional",
        "population", "população",
    ]

    # Palavras que indicam menor impacto
    LOW_IMPACT_KEYWORDS = [
        "preliminary", "preliminar", "pilot", "piloto",
        "case study", "estudo de caso", "single case", "caso único",
        "exploratory", "exploratório", "descriptive", "descritivo",
        "commentary", "comentário", "letter", "carta",
        "erratum", "corrigendum",
    ]

    # Periódicos de alto impacto em ABA
    HIGH_IMPACT_JOURNALS = [
        "journal of applied behavior analysis",
        "journal of the experimental analysis of behavior",
        "behavior analysis",
        "behavioral interventions",
        "research in autism spectrum disorders",
        "journal of autism and developmental disorders",
    ]

    @classmethod
    async def calculate_impact(
        cls,
        title: str,
        abstract: str | None = None,
        keywords: str | None = None,
        journal_name: str | None = None,
        has_doi: bool = False,
        use_ai: bool = True,
    ) -> float:
        """
        Calcula score de impacto do artigo.
        
        Args:
            title: Título do artigo
            abstract: Abstract do artigo
            keywords: Palavras-chave
            journal_name: Nome do periódico
            has_doi: Se tem DOI
            use_ai: Se deve tentar usar IA para análise mais sofisticada
        
        Returns:
            Score de 1.0 a 10.0
        """
        score = 5.0  # Score base

        # Combinar texto para análise
        text = " ".join(filter(None, [title, abstract, keywords])).lower()

        if not text:
            return score

        # Tentar usar IA para análise mais sofisticada (opcional)
        ai_boost = 0.0
        if use_ai:
            try:
                from app.ai import get_ai_manager
                ai_manager = get_ai_manager()
                
                # Se IA externa disponível, usar para análise de impacto
                if any(p in ai_manager.providers for p in ["deepseek", "openrouter"]):
                    # Análise básica via IA pode melhorar o score
                    # Por enquanto, usamos análise heurística + IA como validação
                    pass  # Implementação futura: prompt específico para análise de impacto
            except Exception as e:
                log.debug(f"IA não disponível para análise de impacto: {e}")

        try:
            # Fator 1: Keywords de alto impacto (+0.5 cada, máx +2.0)
            high_impact_count = sum(
                1 for kw in cls.HIGH_IMPACT_KEYWORDS
                if kw.lower() in text
            )
            score += min(high_impact_count * 0.5, 2.0)

            # Fator 2: Keywords de baixo impacto (-0.3 cada, máx -1.5)
            low_impact_count = sum(
                1 for kw in cls.LOW_IMPACT_KEYWORDS
                if kw.lower() in text
            )
            score -= min(low_impact_count * 0.3, 1.5)

            # Fator 3: Periódico de alto impacto (+1.5)
            if journal_name:
                journal_lower = journal_name.lower()
                if any(j in journal_lower for j in cls.HIGH_IMPACT_JOURNALS):
                    score += 1.5

            # Fator 4: Tem DOI (+0.5)
            if has_doi:
                score += 0.5

            # Fator 5: Tamanho do abstract (abstract detalhado = mais completo)
            if abstract:
                if len(abstract) > 1000:
                    score += 0.5
                elif len(abstract) > 500:
                    score += 0.25

            # Fator 6: Presença de dados quantitativos no abstract
            if abstract:
                # Procurar números, percentuais, estatísticas
                if re.search(r'\d+%|\bp\s*[<>=]\s*\d|n\s*=\s*\d+', abstract, re.IGNORECASE):
                    score += 0.5

            # Fator 7: Keywords definidas
            if keywords and len(keywords.split(",")) >= 3:
                score += 0.25

            # Garantir range 1-10
            score = max(1.0, min(10.0, score))

            log.debug(f"Impact score calculado: {score:.2f}")
            return round(score, 2)

        except Exception as e:
            log.error(f"Erro ao calcular impacto: {e}")
            return 5.0

    @classmethod
    async def calculate_impact_batch(
        cls,
        articles: list[dict],
    ) -> list[float]:
        """
        Calcula impacto para múltiplos artigos.
        
        Args:
            articles: Lista de dicts com title, abstract, keywords, journal_name, has_doi
        """
        return [
            await cls.calculate_impact(
                title=a.get("title", ""),
                abstract=a.get("abstract"),
                keywords=a.get("keywords"),
                journal_name=a.get("journal_name"),
                has_doi=bool(a.get("doi")),
            )
            for a in articles
        ]
