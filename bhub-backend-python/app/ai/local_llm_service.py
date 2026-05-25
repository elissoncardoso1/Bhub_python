"""
Serviço de IA usando LLM local via llama.cpp.
Implementa classificação e tradução usando modelos GGUF rodando em CPU.
"""

import asyncio
import json
import threading
from pathlib import Path

from llama_cpp import Llama
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.manager import AIProvider, BaseAIService
from app.ai.model_manager import get_model_manager
from app.config import settings
from app.core.logging import log

# Lock para thread-safety no carregamento do modelo
_model_lock = threading.Lock()
_llm_instance: Llama | None = None


class LocalLLMService(BaseAIService):
    """Serviço de IA usando LLM local via llama.cpp."""

    provider = AIProvider.LOCAL_LLM

    CLASSIFY_PROMPT = """<|system|>
Você é um classificador especialista em Análise do Comportamento (ABA).
Analise o título e resumo fornecidos. Classifique o artigo em UMA ou MAIS categorias.

CATEGORIAS DISPONÍVEIS (em ordem de especificidade - prefira categorias mais específicas):

1. autismo: Artigos sobre Transtorno do Espectro Autista (TEA), vivências de autistas, experiências de pessoas no espectro, intervenções ABA para autismo, diagnóstico de autismo, inclusão de autistas. USE ESTA CATEGORIA quando o foco principal for autismo, mesmo que seja um relato pessoal ou notícia.

2. noticias: Notícias, relatos pessoais, vivências, podcasts, entrevistas, eventos, comunicados, divulgação. NÃO é pesquisa científica nem intervenção clínica direta.

3. comportamento-verbal: Artigos sobre linguagem, tato, mando, intraverbal, ecoico, autoclítico, RFT (Relational Frame Theory), comunicação, Skinner Verbal Behavior.

4. behaviorismo-radical: Filosofia, teoria, fundamentos do Behaviorismo Radical, Skinner, epistemologia, seleção por consequências, eventos privados, ontogenia, filogenia.

5. educacao: Ensino, escolas, professor, aluno, aprendizagem, instrução, currículo, sala de aula, formação acadêmica, habilidades acadêmicas.

6. organizacional: OBM, empresas, trabalho, gestão, liderança, produtividade, desempenho, segurança no trabalho, recursos humanos.

7. pesquisa: Estudos experimentais, pesquisa básica, metodologia, laboratório, dados, análise estatística, revisão sistemática, experimentos controlados.

8. clinica: Intervenção terapêutica direta, tratamento de transtornos (EXCETO autismo que tem categoria própria), atendimento clínico, caso clínico, psicoterapia comportamental, consultório.

9. outros: APENAS se não se encaixar em nenhuma das categorias acima.

REGRAS CRÍTICAS:
- Se o artigo fala sobre VIVÊNCIAS de pessoas autistas → use "autismo" + "noticias"
- Se é um podcast, entrevista ou relato pessoal sobre autismo → use "autismo" + "noticias", NÃO "clinica"
- Se o foco principal é TEA/autismo → use "autismo" como categoria principal
- "clinica" é para intervenção terapêutica de transtornos OUTROS que autismo
- Analise o CONTEÚDO real, não apenas palavras-chave isoladas

FORMATO DE RESPOSTA:
Retorne APENAS um JSON válido no formato:
{{"categories": [{{"slug": "categoria1", "confidence": 0.0_a_1.0}}, {{"slug": "categoria2", "confidence": 0.0_a_1.0}}], "suggested_category": null}}

<|user|>
Título: {title}
Resumo: {abstract}
<|assistant|>
"""

    TRANSLATE_PROMPT = """<|system|>
Você é um tradutor profissional especializado em textos acadêmicos de Análise do Comportamento.
Traduza o texto do inglês para o português brasileiro de forma profissional e acadêmica.
Mantenha termos técnicos de Análise do Comportamento quando apropriado.

IMPORTANTE: Retorne APENAS o texto traduzido, sem nenhum prefixo como "Tradução:", sem formatação markdown, sem asteriscos, sem aspas ao redor. Apenas o texto puro traduzido.

<|user|>
Texto: {text}
<|assistant|>
"""

    def __init__(self):
        """Inicializa o serviço de LLM local."""
        self._model_path: Path | None = None
        self._initialized = False

    async def is_available(self) -> bool:
        """Verifica se o serviço está disponível."""
        if not settings.local_llm_enabled:
            return False

        try:
            # Verificar se modelo pode ser carregado
            model_path = self._get_model_path()
            if model_path is None:
                return False

            # Verificar se arquivo existe e é válido
            model_manager = get_model_manager()
            if not model_manager.verify_model(model_path):
                return False

            return True
        except Exception as e:
            log.debug(f"LocalLLM não disponível: {e}")
            return False

    def _get_model_path(self) -> Path | None:
        """Obtém o caminho do modelo."""
        if self._model_path is None:
            model_manager = get_model_manager()
            self._model_path = model_manager.get_model_path()
        return self._model_path

    def _get_llm(self) -> Llama | None:
        """Obtém instância do LLM (singleton, thread-safe)."""
        global _llm_instance

        if _llm_instance is not None:
            return _llm_instance

        with _model_lock:
            # Double-check após adquirir lock
            if _llm_instance is not None:
                return _llm_instance

            try:
                model_path = self._get_model_path()
                if model_path is None:
                    log.error("Caminho do modelo não encontrado")
                    return None

                if not model_path.exists():
                    log.error(f"Arquivo do modelo não existe: {model_path}")
                    return None

                log.info(f"Carregando modelo LLM: {model_path}")

                _llm_instance = Llama(
                    model_path=str(model_path),
                    n_ctx=settings.local_llm_n_ctx,
                    n_threads=settings.local_llm_n_threads if settings.local_llm_n_threads > 0 else None,
                    n_gpu_layers=settings.local_llm_n_gpu_layers,
                    verbose=False,
                )

                log.info("Modelo LLM carregado com sucesso")
                return _llm_instance

            except Exception as e:
                log.error(f"Erro ao carregar modelo LLM: {e}")
                return None

    def _sync_generate(self, llm, prompt: str) -> dict:
        """
        Executa a geração de texto de forma síncrona.
        Esta função é chamada em uma thread separada para não bloquear o event loop.
        """
        return llm(
            prompt,
            max_tokens=settings.local_llm_max_tokens,
            temperature=settings.local_llm_temperature,
            stop=["<|user|>", "<|system|>", "\n\n"],
            echo=False,
        )

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def classify(self, text: str) -> tuple[str, float]:
        """
        Classifica texto usando LLM local.

        Args:
            text: Texto para classificar (título + abstract)

        Returns:
            Tupla (categoria, confiança)
        """
        llm = self._get_llm()
        if llm is None:
            log.warning("LLM não disponível para classificação")
            return ("outros", 0.0)

        try:
            # Preparar texto (título + abstract)
            title = text[:500] if len(text) > 500 else text
            abstract = text[500:2000] if len(text) > 500 else ""

            prompt = self.CLASSIFY_PROMPT.format(title=title, abstract=abstract)

            # Gerar resposta em thread separada para não bloquear o event loop
            response = await asyncio.wait_for(
                asyncio.to_thread(self._sync_generate, llm, prompt),
                timeout=60.0  # Timeout de 60 segundos
            )

            # Extrair conteúdo da resposta
            if not response or "choices" not in response or len(response["choices"]) == 0:
                log.warning("Resposta vazia do LLM")
                return ("outros", 0.0)

            content = response["choices"][0]["text"].strip()

            # Limpar conteúdo (remover markdown se presente)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parsear JSON
            try:
                result_json = json.loads(content)

                # Suporte ao novo formato com múltiplas categorias
                if "categories" in result_json:
                    # Novo formato: múltiplas categorias
                    categories_list = result_json.get("categories", [])
                    if categories_list:
                        # Retornar a primeira categoria (mais confiável) para compatibilidade
                        first_cat = categories_list[0]
                        category = first_cat.get("slug", "outros").lower()
                        confidence = float(first_cat.get("confidence", 0.5))
                    else:
                        category = "outros"
                        confidence = 0.0
                else:
                    # Formato antigo: categoria única
                    category = result_json.get("category", "outros").lower()
                    confidence = float(result_json.get("confidence", 0.5))

                # Validar categoria
                valid_categories = [
                    "clinica",
                    "educacao",
                    "organizacional",
                    "pesquisa",
                    "autismo",
                    "behaviorismo-radical",
                    "comportamento-verbal",
                    "noticias",
                    "outros",
                ]
                if category in valid_categories:
                    log.debug(f"Classificação LLM local: {category} (conf: {confidence:.2f})")
                    return (category, confidence)

                # Fallback: procurar categoria no texto
                for cat in valid_categories:
                    if cat in category:
                        log.debug(f"Classificação LLM local (fallback): {cat} (conf: {confidence:.2f})")
                        return (cat, confidence)

                log.warning(f"Categoria inválida retornada: {category}")
                return ("outros", confidence)

            except json.JSONDecodeError as e:
                log.warning(f"Erro ao parsear JSON do LLM: {e}. Content: {content}")
                # Tentar extrair categoria do texto
                content_lower = content.lower()
                for cat in ["clinica", "educacao", "organizacional", "pesquisa"]:
                    if cat in content_lower:
                        return (cat, 0.6)
                return ("outros", 0.0)

        except TimeoutError:
            log.warning("Timeout na classificação com LLM local (60s)")
            return ("outros", 0.0)
        except Exception as e:
            log.error(f"Erro na classificação com LLM local: {e}")
            return ("outros", 0.0)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def classify_multiple(self, text: str) -> list[tuple[str, float]]:
        """
        Classifica texto retornando múltiplas categorias com suas confianças.

        Args:
            text: Texto para classificar (título + abstract)

        Returns:
            Lista de tuplas (categoria_slug, confiança)
        """
        llm = self._get_llm()
        if llm is None:
            log.warning("LLM não disponível para classificação múltipla")
            return [("outros", 0.0)]

        # Categorias válidas (definido fora do try para uso no except)
        valid_categories = [
            "clinica", "educacao", "organizacional", "pesquisa",
            "autismo", "behaviorismo-radical", "comportamento-verbal",
            "noticias", "outros",
        ]

        try:
            # Preparar texto (título + abstract)
            title = text[:500] if len(text) > 500 else text
            abstract = text[500:2000] if len(text) > 500 else ""

            prompt = self.CLASSIFY_PROMPT.format(title=title, abstract=abstract)

            # Gerar resposta em thread separada para não bloquear o event loop
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    llm,
                    prompt,
                    max_tokens=settings.local_llm_max_tokens * 2,  # Mais tokens para múltiplas categorias
                    temperature=settings.local_llm_temperature,
                    stop=["<|user|>", "<|system|>", "\n\n"],
                    echo=False,
                ),
                timeout=90.0  # Timeout de 90 segundos
            )

            # Extrair conteúdo da resposta
            if not response or "choices" not in response or len(response["choices"]) == 0:
                log.warning("Resposta vazia do LLM")
                return [("outros", 0.0)]

            content = response["choices"][0]["text"].strip()

            # Limpar conteúdo (remover markdown se presente)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parsear JSON
            try:
                result_json = json.loads(content)

                categories_result = []

                # Processar múltiplas categorias
                if "categories" in result_json:
                    for cat_data in result_json.get("categories", []):
                        slug = cat_data.get("slug", "").lower()
                        confidence = float(cat_data.get("confidence", 0.5))

                        if slug in valid_categories:
                            categories_result.append((slug, confidence))

                # Se não encontrou categorias no novo formato, tentar formato antigo
                if not categories_result:
                    category = result_json.get("category", "outros").lower()
                    confidence = float(result_json.get("confidence", 0.5))
                    if category in valid_categories:
                        categories_result.append((category, confidence))

                # Se ainda não encontrou, usar "outros"
                if not categories_result:
                    categories_result.append(("outros", 0.5))

                # Processar categoria sugerida (se houver)
                suggested = result_json.get("suggested_category")
                if suggested and suggested.get("slug"):
                    suggested_slug = suggested.get("slug", "").lower()
                    suggested_confidence = float(suggested.get("confidence", 0.7))
                    categories_result.append((suggested_slug, suggested_confidence))
                    log.info(f"Categoria sugerida pelo LLM: {suggested.get('name')} ({suggested_slug})")

                log.debug(f"Classificação múltipla LLM local: {len(categories_result)} categorias")
                return categories_result

            except json.JSONDecodeError as e:
                log.warning(f"Erro ao parsear JSON do LLM: {e}. Content: {content}")
                # Fallback: tentar extrair categoria do texto
                content_lower = content.lower()
                for cat in valid_categories:
                    if cat in content_lower:
                        return [(cat, 0.6)]
                return [("outros", 0.0)]

        except TimeoutError:
            log.warning("Timeout na classificação múltipla com LLM local (90s)")
            return [("outros", 0.0)]
        except Exception as e:
            log.error(f"Erro na classificação múltipla com LLM local: {e}")
            return [("outros", 0.0)]

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def translate(self, text: str, target_lang: str = "pt") -> str:
        """
        Traduz texto usando LLM local.

        Args:
            text: Texto para traduzir
            target_lang: Idioma alvo (padrão: pt)

        Returns:
            Texto traduzido
        """
        if target_lang != "pt":
            log.warning(f"Tradução para {target_lang} não suportada, usando português")
            target_lang = "pt"

        llm = self._get_llm()
        if llm is None:
            log.warning("LLM não disponível para tradução")
            return text

        try:
            prompt = self.TRANSLATE_PROMPT.format(text=text)

            # Gerar resposta em thread separada para não bloquear o event loop
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    llm,
                    prompt,
                    max_tokens=len(text) * 2,  # Espaço suficiente para tradução
                    temperature=0.3,
                    stop=["<|user|>", "<|system|>", "\n\n"],
                    echo=False,
                ),
                timeout=120.0  # Timeout de 120 segundos para textos longos
            )

            # Extrair conteúdo
            if not response or "choices" not in response or len(response["choices"]) == 0:
                log.warning("Resposta vazia do LLM na tradução")
                return text

            translated = response["choices"][0]["text"].strip()

            # Limpar resposta (remover aspas, markdown, etc.)
            translated = translated.strip('"').strip("'").strip()
            if translated.startswith("Tradução:"):
                translated = translated.replace("Tradução:", "").strip()

            return translated

        except TimeoutError:
            log.warning("Timeout na tradução com LLM local (120s)")
            return text
        except Exception as e:
            log.error(f"Erro na tradução com LLM local: {e}")
            return text
