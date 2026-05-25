"""
Gerenciador de provedores de IA externa.
"""

import time
from abc import ABC, abstractmethod
from enum import Enum

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logging import log

# Constantes
CONTENT_TYPE_JSON = "application/json"


class AIProvider(str, Enum):
    """Provedores de IA disponíveis."""
    LOCAL_LLM = "local_llm"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"


class AIManager:
    """
    Gerenciador central de provedores de IA.
    Implementa fallback automático entre provedores.
    """

    def __init__(self):
        self.providers: dict[AIProvider, BaseAIService] = {}
        self._setup_providers()

    def _setup_providers(self):
        """Configura provedores disponíveis."""
        # Local LLM (prioridade máxima)
        if settings.local_llm_enabled:
            try:
                from app.ai.local_llm_service import LocalLLMService
                self.providers[AIProvider.LOCAL_LLM] = LocalLLMService()
                log.info("Local LLM configurado")
            except ImportError as e:
                log.warning(f"Local LLM não disponível (dependências faltando): {e}")
            except Exception as e:
                log.warning(f"Erro ao configurar Local LLM: {e}")

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
            AIProvider.DEEPSEEK,    # Prioridade máxima: API externa (mais rápida)
            AIProvider.LOCAL_LLM,   # Fallback: LLM local (sem custos)
            AIProvider.OPENROUTER,
            AIProvider.HUGGINGFACE,
        ]

        for provider_type in providers_order:
            if provider_type not in self.providers:
                continue

            provider = self.providers[provider_type]
            start = time.monotonic()
            try:
                if not await provider.is_available():
                    continue

                category, confidence = await provider.classify(text)
                from app.core.telemetry import record_ai_latency

                record_ai_latency(
                    (time.monotonic() - start) * 1000,
                    provider_type.value,
                )
                return (category, confidence, provider_type)

            except Exception as e:
                from app.core.telemetry import record_ai_fallback

                record_ai_fallback(provider_type.value)
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
            AIProvider.DEEPSEEK,    # Prioridade máxima: API externa (mais rápida)
            AIProvider.LOCAL_LLM,   # Fallback: LLM local (sem custos)
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
Atue como um classificador especialista em Análise do Comportamento (ABA).
Analise o título e resumo. Classifique PRECISAMENTE na categoria mais adequada:

CATEGORIAS (em ordem de especificidade - prefira categorias mais específicas):

1. autismo: Artigos sobre Transtorno do Espectro Autista (TEA), vivências de autistas, intervenções ABA para autismo, diagnóstico de autismo, inclusão de autistas, experiências de pessoas no espectro. Use esta categoria quando o foco principal for autismo.

2. noticias: Notícias, relatos pessoais, vivências, podcasts, entrevistas, eventos, comunicados, divulgação. NÃO é pesquisa científica nem intervenção clínica direta.

3. comportamento-verbal: Artigos sobre linguagem, tato, mando, intraverbal, ecoico, autoclítico, RFT (Relational Frame Theory), comunicação.

4. behaviorismo-radical: Filosofia, teoria, fundamentos do Behaviorismo Radical, Skinner, epistemologia, seleção por consequências, eventos privados.

5. educacao: Ensino, escolas, professor, aluno, aprendizagem, instrução, currículo, sala de aula, formação acadêmica.

6. organizacional: OBM, empresas, trabalho, gestão, liderança, produtividade, desempenho, segurança no trabalho.

7. pesquisa: Estudos experimentais, pesquisa básica, metodologia, laboratório, dados, análise estatística, revisão sistemática.

8. clinica: Intervenção terapêutica direta, tratamento de transtornos (exceto autismo que tem categoria própria), atendimento clínico, caso clínico, psicoterapia comportamental.

9. outros: APENAS se não se encaixar em nenhuma das categorias acima.

REGRAS IMPORTANTES:
- Se o artigo fala sobre VIVÊNCIAS de pessoas autistas, experiências pessoais ou podcasts sobre autismo → use "autismo" ou "noticias", NÃO "clinica"
- Se é um podcast, entrevista, relato pessoal ou notícia → use "noticias"
- Se o foco é TEA/autismo → use "autismo"
- "clinica" é para intervenção terapêutica direta de transtornos OUTROS que autismo
- Analise o CONTEÚDO real, não apenas palavras-chave

Retorne JSON: {{"category": "slug", "confidence": 0.0_a_1.0}}

Título: {title}
Resumo: {abstract}
"""

    TRANSLATE_PROMPT = """Traduza o seguinte texto do inglês para o português brasileiro de forma profissional e acadêmica.
Mantenha termos técnicos de Análise do Comportamento quando apropriado.

IMPORTANTE: Retorne APENAS o texto traduzido, sem nenhum prefixo como "Tradução:", sem formatação markdown, sem asteriscos, sem aspas ao redor. Apenas o texto puro traduzido.

Texto: {text}

"""

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
                    "Content-Type": CONTENT_TYPE_JSON,
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

                valid_categories = [
                    "clinica", "educacao", "organizacional", "pesquisa",
                    "autismo", "behaviorismo-radical", "comportamento-verbal",
                    "noticias", "outros"
                ]
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
                    "Content-Type": CONTENT_TYPE_JSON,
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
                    "Content-Type": CONTENT_TYPE_JSON,
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
                    "Content-Type": CONTENT_TYPE_JSON,
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
