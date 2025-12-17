"""
Classificador de artigos usando embeddings.
"""

import json
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.core.logging import log


class EmbeddingClassifier:
    """
    Classificador de artigos usando sentence embeddings.
    Modelo: paraphrase-multilingual-MiniLM-L12-v2
    """

    _instance = None
    _model: SentenceTransformer | None = None
    _category_embeddings: dict[str, np.ndarray] = {}
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls) -> None:
        """Inicializa o modelo de embeddings."""
        if cls._initialized:
            return

        log.info("Inicializando modelo de embeddings...")

        try:
            cls._model = SentenceTransformer(settings.embedding_model)
            log.info(f"Modelo carregado: {settings.embedding_model}")
            cls._initialized = True
        except Exception as e:
            log.error(f"Erro ao carregar modelo: {e}")
            raise

    @classmethod
    def is_initialized(cls) -> bool:
        """Verifica se o modelo está inicializado."""
        return cls._initialized

    @classmethod
    async def load_category_embeddings(cls, categories: list[dict]) -> None:
        """
        Carrega embeddings das categorias.
        
        Args:
            categories: Lista de dicts com name, description, keywords
        """
        if not cls._initialized:
            await cls.initialize()

        log.info("Gerando embeddings das categorias...")

        for cat in categories:
            # Combinar descrição e keywords para gerar embedding
            text_parts = [cat["name"]]

            if cat.get("description"):
                text_parts.append(cat["description"])

            if cat.get("keywords"):
                text_parts.append(cat["keywords"])

            text = " ".join(text_parts)

            # Gerar embedding
            embedding = cls._model.encode(text, convert_to_numpy=True)
            cls._category_embeddings[cat["slug"]] = embedding

            log.debug(f"Embedding gerado para categoria: {cat['name']}")

        log.info(f"Embeddings carregados para {len(cls._category_embeddings)} categorias")

    @classmethod
    async def classify(
        cls,
        text: str,
        threshold: float = None,
    ) -> tuple[str, float]:
        """
        Classifica um texto em uma categoria.
        
        Args:
            text: Texto para classificar (título + abstract + keywords)
            threshold: Limiar mínimo de confiança
            
        Returns:
            Tupla (categoria_slug, confiança)
        """
        if not cls._initialized:
            await cls.initialize()

        if threshold is None:
            threshold = settings.classification_threshold

        if not cls._category_embeddings:
            log.warning("Nenhum embedding de categoria carregado")
            return ("outros", 0.0)

        if not text or len(text.strip()) < 10:
            return ("outros", 0.0)

        try:
            # Gerar embedding do texto
            text_embedding = cls._model.encode(text, convert_to_numpy=True)

            # Calcular similaridade com cada categoria
            similarities = {}
            for cat_slug, cat_embedding in cls._category_embeddings.items():
                similarity = cls._cosine_similarity(text_embedding, cat_embedding)
                similarities[cat_slug] = float(similarity)

            # Encontrar categoria com maior similaridade
            best_category = max(similarities, key=similarities.get)
            best_score = similarities[best_category]

            log.debug(f"Classificação: {best_category} (score: {best_score:.4f})")

            # Verificar threshold
            if best_score < threshold:
                log.debug(f"Score abaixo do threshold ({threshold}), usando 'outros'")
                return ("outros", best_score)

            return (best_category, best_score)

        except Exception as e:
            log.error(f"Erro na classificação: {e}")
            return ("outros", 0.0)

    @classmethod
    async def classify_batch(
        cls,
        texts: list[str],
        threshold: float = None,
    ) -> list[tuple[str, float]]:
        """
        Classifica múltiplos textos em batch.
        Mais eficiente que classificar um por um.
        """
        if not cls._initialized:
            await cls.initialize()

        if threshold is None:
            threshold = settings.classification_threshold

        if not cls._category_embeddings:
            return [("outros", 0.0) for _ in texts]

        try:
            # Gerar embeddings em batch
            embeddings = cls._model.encode(texts, convert_to_numpy=True)

            results = []
            for embedding in embeddings:
                # Calcular similaridade
                similarities = {}
                for cat_slug, cat_embedding in cls._category_embeddings.items():
                    similarity = cls._cosine_similarity(embedding, cat_embedding)
                    similarities[cat_slug] = float(similarity)

                best_category = max(similarities, key=similarities.get)
                best_score = similarities[best_category]

                if best_score < threshold:
                    results.append(("outros", best_score))
                else:
                    results.append((best_category, best_score))

            return results

        except Exception as e:
            log.error(f"Erro na classificação batch: {e}")
            return [("outros", 0.0) for _ in texts]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calcula similaridade de cosseno entre dois vetores."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    @classmethod
    def get_embedding(cls, text: str) -> np.ndarray | None:
        """Retorna embedding de um texto."""
        if not cls._initialized or not cls._model:
            return None
        return cls._model.encode(text, convert_to_numpy=True)

    @classmethod
    def get_status(cls) -> dict:
        """Retorna status do classificador."""
        return {
            "initialized": cls._initialized,
            "model": settings.embedding_model if cls._initialized else None,
            "categories_loaded": len(cls._category_embeddings),
        }


class HeuristicClassifier:
    """
    Classificador heurístico de fallback.
    Usa keywords simples quando o modelo ML não está disponível.
    """

    CATEGORY_KEYWORDS = {
        "clinica": [
            "clínica", "terapia", "tratamento", "intervenção", "paciente",
            "cliente", "sessão", "consultório", "atendimento", "transtorno",
            "diagnóstico", "avaliação clínica", "caso clínico", "psicoterapia",
            "clinical", "therapy", "treatment", "intervention", "patient",
        ],
        "educacao": [
            "educação", "ensino", "escola", "professor", "aluno",
            "aprendizagem", "instrução", "currículo", "sala de aula",
            "education", "teaching", "school", "student", "learning",
            "classroom", "curriculum", "teacher",
        ],
        "organizacional": [
            "organizacional", "empresa", "trabalho", "gestão", "liderança",
            "produtividade", "desempenho", "feedback", "treinamento corporativo",
            "organizational", "OBM", "workplace", "performance management",
            "leadership", "productivity",
        ],
        "pesquisa": [
            "pesquisa", "experimento", "metodologia", "dados", "análise",
            "resultados", "hipótese", "variável", "controle", "laboratório",
            "research", "experiment", "methodology", "data", "analysis",
            "hypothesis", "laboratory", "empirical",
        ],
    }

    @classmethod
    def classify(cls, text: str) -> tuple[str, float]:
        """
        Classifica texto usando heurística de keywords.
        
        Returns:
            Tupla (categoria_slug, confiança)
        """
        if not text:
            return ("outros", 0.0)

        text_lower = text.lower()

        scores = {}
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            scores[category] = score

        if max(scores.values()) == 0:
            return ("outros", 0.0)

        best_category = max(scores, key=scores.get)
        # Normalizar score (0-1)
        confidence = min(scores[best_category] / 5.0, 1.0)

        return (best_category, confidence)


# Função helper para obter classificador
async def get_classifier() -> EmbeddingClassifier:
    """Retorna instância do classificador inicializado."""
    classifier = EmbeddingClassifier()
    if not classifier.is_initialized():
        await classifier.initialize()
    return classifier
