"""
Script para configurar e validar o LLM local (Phi-3 Mini).
Faz download do modelo, valida instalação e testa classificação básica.
"""

import asyncio
import os
import sys
from pathlib import Path

# Adicionar raiz no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.local_llm_service import LocalLLMService
from app.ai.model_manager import get_model_manager
from app.config import settings
from app.core.logging import log


async def test_classification():
    """Testa classificação básica."""
    print("\n--- Testando Classificação ---")

    service = LocalLLMService()

    if not await service.is_available():
        print("❌ Serviço LLM local não está disponível")
        return False

    # Teste com artigo clínico
    test_text = """
    Title: Behavioral Intervention for Autism Spectrum Disorder in Children
    Abstract: This study evaluates the effectiveness of applied behavior analysis
    interventions for children with autism spectrum disorder. The intervention
    included discrete trial training and natural environment teaching strategies.
    """

    print(f"Testando classificação com texto de exemplo...")
    print(f"Texto: {test_text[:100]}...")

    try:
        category, confidence = await service.classify(test_text)
        print(f"✅ Classificação: {category} (confiança: {confidence:.2f})")

        if category in ["clinica", "educacao", "organizacional", "pesquisa", "outros"]:
            print("✅ Categoria válida")
            return True
        else:
            print(f"⚠️  Categoria inválida: {category}")
            return False
    except Exception as e:
        print(f"❌ Erro na classificação: {e}")
        return False


async def test_translation():
    """Testa tradução básica."""
    print("\n--- Testando Tradução ---")

    service = LocalLLMService()

    if not await service.is_available():
        print("❌ Serviço LLM local não está disponível")
        return False

    test_text = "Applied Behavior Analysis is a scientific approach to understanding behavior."

    print(f"Texto original: {test_text}")

    try:
        translated = await service.translate(test_text)
        print(f"✅ Tradução: {translated}")

        if len(translated) > 10:
            print("✅ Tradução parece válida")
            return True
        else:
            print("⚠️  Tradução muito curta")
            return False
    except Exception as e:
        print(f"❌ Erro na tradução: {e}")
        return False


def check_dependencies():
    """Verifica se as dependências estão instaladas."""
    print("--- Verificando Dependências ---")

    try:
        import llama_cpp
        print("✅ llama-cpp-python instalado")
    except ImportError:
        print("❌ llama-cpp-python não instalado")
        print("   Execute: pip install llama-cpp-python")
        return False

    try:
        import huggingface_hub
        print("✅ huggingface-hub instalado")
    except ImportError:
        print("❌ huggingface-hub não instalado")
        print("   Execute: pip install huggingface-hub")
        return False

    return True


def check_config():
    """Verifica configuração."""
    print("\n--- Verificando Configuração ---")

    if not settings.local_llm_enabled:
        print("⚠️  LOCAL_LLM_ENABLED está desabilitado")
        print("   Configure LOCAL_LLM_ENABLED=true no .env")
        return False

    print(f"✅ LOCAL_LLM_ENABLED: {settings.local_llm_enabled}")
    print(f"   Modelo: {settings.local_llm_model_name}")
    print(f"   Threads: {settings.local_llm_n_threads}")
    print(f"   Contexto: {settings.local_llm_n_ctx}")

    if settings.local_llm_model_path:
        print(f"   Caminho customizado: {settings.local_llm_model_path}")

    return True


def download_model():
    """Faz download do modelo."""
    print("\n--- Download do Modelo ---")

    model_manager = get_model_manager()
    model_path = model_manager.get_model_path()

    if model_path and model_path.exists():
        print(f"✅ Modelo já existe: {model_path}")
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"   Tamanho: {size_mb:.2f} MB")

        if model_manager.verify_model(model_path):
            print("✅ Modelo verificado com sucesso")
            return True
        else:
            print("⚠️  Modelo não passou na verificação")
            return False
    else:
        print("📥 Modelo não encontrado. Iniciando download...")
        print("   Isso pode levar alguns minutos (~2.3 GB)...")

        downloaded_path = model_manager.download_model()

        if downloaded_path and downloaded_path.exists():
            print(f"✅ Modelo baixado com sucesso: {downloaded_path}")
            size_mb = downloaded_path.stat().st_size / (1024 * 1024)
            print(f"   Tamanho: {size_mb:.2f} MB")

            if model_manager.verify_model(downloaded_path):
                print("✅ Modelo verificado com sucesso")
                return True
            else:
                print("⚠️  Modelo não passou na verificação")
                return False
        else:
            print("❌ Falha ao baixar modelo")
            return False


async def main():
    """Função principal."""
    print("=" * 60)
    print("Setup do LLM Local (Phi-3 Mini)")
    print("=" * 60)

    # Verificar dependências
    if not check_dependencies():
        print("\n❌ Instale as dependências antes de continuar")
        return

    # Verificar configuração
    if not check_config():
        print("\n⚠️  Configure as variáveis de ambiente antes de continuar")
        print("   Adicione ao .env:")
        print("   LOCAL_LLM_ENABLED=true")
        print("   LOCAL_LLM_MODEL_NAME=Phi-3-mini-4k-instruct")
        return

    # Download do modelo
    if not download_model():
        print("\n❌ Falha no download/validação do modelo")
        return

    # Testes
    print("\n" + "=" * 60)
    print("Executando Testes")
    print("=" * 60)

    classification_ok = await test_classification()
    translation_ok = await test_translation()

    # Resumo
    print("\n" + "=" * 60)
    print("Resumo")
    print("=" * 60)

    if classification_ok and translation_ok:
        print("✅ Todos os testes passaram!")
        print("\nO LLM local está pronto para uso.")
        print("Ele será usado automaticamente quando LOCAL_LLM_ENABLED=true")
    else:
        print("⚠️  Alguns testes falharam")
        if not classification_ok:
            print("   - Classificação falhou")
        if not translation_ok:
            print("   - Tradução falhou")
        print("\nVerifique os logs para mais detalhes.")


if __name__ == "__main__":
    asyncio.run(main())
