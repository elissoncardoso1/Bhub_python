"""
Gerenciador de provedores de IA externa.
"""

from abc import ABC, abstractmethod
from enum import Enum

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logging import log


class AIProvider(str, Enum):
    """Provedores de IA disponíveis."""
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"


class AIManager:
    """
    Gerenciador central de provedores de IA.
    Implementa fallback automático entre provedores.
    """
    
    def __init__(self):
        self.providers: dict[AIProvider, "BaseAIService"] = {}
        self._setup_providers()
    
    def _setup_providers(self):
        """Configura provedores disponíveis."""
        if settings.deepseek_api_key:
            self.providers[AIProvider.DEEPSEEK] = DeepSeekService()
            log.info("DeepSeek configurado")
        
        if settings.openrouter_api_key:
            self.providers[AIProvider.OPENROUTER] = OpenRouterService()
            log.info("OpenRouter configurado")
        
        if settings.huggingface_api_key:
            self.providers[AIProvider.HUGGINGFACE] = HuggingFaceService()
            log.info("HuggingFace configurado")
    
    async def classify(self, text: str) -> tuple[str, float, AIProvider | None]:
        """
        Classifica texto usando provedores em ordem de prioridade.
        
        Returns:
            Tupla (categoria, confiança, provider_usado)
        """
        providers_order = [
            AIProvider.DEEPSEEK,
            AIProvider.OPENROUTER,
            AIProvider.HUGGINGFACE,
        ]
        
        for provider_type in providers_order:
            if provider_type not in self.providers:
                continue
            
            provider = self.providers[provider_type]
            try:
                if not await provider.is_available():
                    continue
                
                category, confidence = await provider.classify(text)
                return (category, confidence, provider_type)
            
            except Exception as e:
                log.warning(f"Falha no {provider_type}: {e}")
                continue
        
        return ("outros", 0.0, None)
    
    async def translate(
        self,
        text: str,
        target_lang: str = "pt",
    ) -> tuple[str, AIProvider | None]:
        """
        Traduz texto usando provedores em ordem de prioridade.
        """
        providers_order = [
            AIProvider.DEEPSEEK,
            AIProvider.OPENROUTER,
        ]
        
        for provider_type in providers_order:
            if provider_type not in self.providers:
                continue
            
            provider = self.providers[provider_type]
            try:
                if not await provider.is_available():
                    continue
                
                translated = await provider.translate(text, target_lang)
                return (translated, provider_type)
            
            except Exception as e:
                log.warning(f"Falha na tradução com {provider_type}: {e}")
                continue
        
        return (text, None)
    
    def get_status(self) -> dict:
        """Retorna status de todos os provedores."""
        return {
            provider.value: {
                "configured": provider in self.providers,
            }
            for provider in AIProvider
        }


class BaseAIService(ABC):
    """Classe base para serviços de IA."""
    
    provider: AIProvider
    
    @abstractmethod
    async def classify(self, text: str) -> tuple[str, float]:
        pass
    
    @abstractmethod
    async def translate(self, text: str, target_lang: str = "pt") -> str:
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        pass


class DeepSeekService(BaseAIService):
    """Serviço de IA usando DeepSeek API."""
    
    provider = AIProvider.DEEPSEEK
    
    CLASSIFY_PROMPT = """
Você é um especialista em Análise do Comportamento (ABA/E.A.C.).
Analise o título e resumo do artigo abaixo e classifique-o em UMA das seguintes áreas:

1. clinica (Autismo, terapia ABA, intervenção precoce, saúde mental, redução de danos)
2. educacao (Ensino, aprendizagem, inclusão escolar, formação de professores, habilidades acadêmicas)
3. organizacional (OBM, gestão de desempenho, liderança, cultura organizacional, segurança no trabalho)
4. pesquisa (Pesquisa básica, experimental, análise conceitual, metodologia, filosofia)
5. outros (Se não pertencer claramente a nenhuma das acima)

Retorne APENAS um objeto JSON no formato: {{"category": "slug_da_categoria", "confidence": 0.0_a_1.0}}

Título: {title}
Resumo: {abstract}
"""

    TRANSLATE_PROMPT = """Traduza o seguinte texto do inglês para o português brasileiro de forma profissional e acadêmica. 
Mantenha termos técnicos de Análise do Comportamento quando apropriado.

Texto: {text}

Tradução:"""

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
    
    async def is_available(self) -> bool:
        return bool(self.api_key)
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def classify(self, text: str) -> tuple[str, float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "user", "content": self.CLASSIFY_PROMPT.format(
                            title=text[:500],
                            abstract=text[500:2000] if len(text) > 500 else "",
                        )}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100,
                    "response_format": {"type": "json_object"}
                },
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            try:
                import json
                result_json = json.loads(content)
                category = result_json.get("category", "outros").lower()
                confidence = float(result_json.get("confidence", 0.5))
                
                valid_categories = ["clinica", "educacao", "organizacional", "pesquisa", "outros"]
                if category in valid_categories:
                    return (category, confidence)
                
                # Fallback se a categoria retornada não for exata
                for cat in valid_categories:
                    if cat in category:
                        return (cat, confidence)
                        
                return ("outros", 0.5)
            except Exception as e:
                log.warning(f"Erro ao parsear resposta JSON do DeepSeek: {e}. Content: {content}")
                return ("outros", 0.0)
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def translate(self, text: str, target_lang: str = "pt") -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "user", "content": self.TRANSLATE_PROMPT.format(text=text)}
                    ],
                    "temperature": 0.3,
                    "max_tokens": len(text) * 2,
                },
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()


class OpenRouterService(BaseAIService):
    """Serviço de IA usando OpenRouter API."""
    
    provider = AIProvider.OPENROUTER
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
    
    async def is_available(self) -> bool:
        return bool(self.api_key)
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def classify(self, text: str) -> tuple[str, float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-3-haiku",
                    "messages": [
                        {"role": "user", "content": DeepSeekService.CLASSIFY_PROMPT.format(
                            title=text[:500],
                            abstract=text[500:2000] if len(text) > 500 else "",
                        )}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 50,
                },
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            try:
                import json
                # OpenRouter models might return markdown block ```json ... ```
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()
                    
                result_json = json.loads(content)
                category = result_json.get("category", "outros").lower()
                confidence = float(result_json.get("confidence", 0.5))
                
                valid_categories = ["clinica", "educacao", "organizacional", "pesquisa", "outros"]
                if category in valid_categories:
                    return (category, confidence)
                
                return ("outros", 0.5)
            except Exception as e:
                log.warning(f"Erro ao parsear resposta OpenRouter: {e}")
                return ("outros", 0.0)
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def translate(self, text: str, target_lang: str = "pt") -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-3-haiku",
                    "messages": [
                        {"role": "user", "content": DeepSeekService.TRANSLATE_PROMPT.format(text=text)}
                    ],
                    "temperature": 0.3,
                    "max_tokens": len(text) * 2,
                },
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()


class HuggingFaceService(BaseAIService):
    """Serviço de IA usando HuggingFace Inference API."""
    
    provider = AIProvider.HUGGINGFACE
    
    def __init__(self):
        self.api_key = settings.huggingface_api_key
        self.base_url = "https://api-inference.huggingface.co/models"
    
    async def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def classify(self, text: str) -> tuple[str, float]:
        # HuggingFace é usado principalmente como fallback
        # Usa modelo de classificação de texto
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/facebook/bart-large-mnli",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "inputs": text[:1000],
                    "parameters": {
                        "candidate_labels": [
                            "clinical psychology therapy",
                            "education teaching school",
                            "organizational business management",
                            "research experiment methodology",
                        ]
                    },
                },
            )
            response.raise_for_status()
            
            data = response.json()
            
            label_map = {
                "clinical psychology therapy": "clinica",
                "education teaching school": "educacao",
                "organizational business management": "organizacional",
                "research experiment methodology": "pesquisa",
            }
            
            if "labels" in data and "scores" in data:
                top_label = data["labels"][0]
                top_score = data["scores"][0]
                category = label_map.get(top_label, "outros")
                return (category, top_score)
            
            return ("outros", 0.5)
    
    async def translate(self, text: str, target_lang: str = "pt") -> str:
        # HuggingFace translation usando modelo Helsinki-NLP
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/Helsinki-NLP/opus-mt-en-pt",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"inputs": text},
            )
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("translation_text", text)
            
            return text


# Instância global
_ai_manager: AIManager | None = None


def get_ai_manager() -> AIManager:
    """Retorna instância do gerenciador de IA."""
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIManager()
    return _ai_manager
