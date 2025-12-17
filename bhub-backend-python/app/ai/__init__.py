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

__all__ = [
    "AIManager",
    "AIProvider",
    "BaseAIService",
    "DeepSeekService",
    "OpenRouterService",
    "HuggingFaceService",
    "get_ai_manager",
]
