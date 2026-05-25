"""
Módulo de integração com serviços de IA externa.
"""

from app.ai.manager import (
    AIManager,
    AIProvider,
    BaseAIService,
    DeepSeekService,
    HuggingFaceService,
    OpenRouterService,
    get_ai_manager,
)

# Import condicional para evitar erro se dependências não estiverem instaladas
try:
    from app.ai.local_llm_service import LocalLLMService
except ImportError:
    LocalLLMService = None  # type: ignore

__all__ = [
    "AIManager",
    "AIProvider",
    "BaseAIService",
    "DeepSeekService",
    "OpenRouterService",
    "HuggingFaceService",
    "LocalLLMService",
    "get_ai_manager",
]
