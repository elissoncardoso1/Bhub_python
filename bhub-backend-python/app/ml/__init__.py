"""
Módulo de Machine Learning.
"""

# Importar ImpactRatingService sempre (não tem dependências pesadas)
from app.ml.impact_rating import ImpactRatingService

# Importar EmbeddingClassifier apenas se sentence_transformers estiver disponível
try:
    from app.ml.embedding_classifier import (
        EmbeddingClassifier,
        HeuristicClassifier,
        get_classifier,
    )
    _EMBEDDING_AVAILABLE = True
except ImportError:
    # Se sentence_transformers não estiver instalado, criar stubs
    EmbeddingClassifier = None
    HeuristicClassifier = None
    get_classifier = None
    _EMBEDDING_AVAILABLE = False

__all__ = [
    "EmbeddingClassifier",
    "HeuristicClassifier",
    "get_classifier",
    "ImpactRatingService",
]
