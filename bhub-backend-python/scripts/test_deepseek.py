import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, ".")
load_dotenv()

# Force settings reload
from app.config import settings
settings.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

from app.ai import get_ai_manager, AIProvider
from app.core import logging

logging.setup_logging()
log = logging.log

async def test_deepseek():
    print("-" * 50)
    print("Testando integração com DeepSeek API...")
    print("-" * 50)

    manager = get_ai_manager()
    
    # Force setup again to ensure key is picked up
    manager._setup_providers()

    if AIProvider.DEEPSEEK not in manager.providers:
        print("❌ Erro: DeepSeek Provider não foi inicializado. Verifique a API Key.")
        return

    print("✅ DeepSeek Provider inicializado.")
    provider = manager.providers[AIProvider.DEEPSEEK]
    
    # Test article
    title = "The Effects of Precision Teaching on Math Skills in Information Technology Students"
    abstract = """
    This study evaluated the effects of Precision Teaching (PT) on the mathematics skills of undergraduate students in an Information Technology course. 
    Using a multiple baseline design across behaviors, students received daily practice sessions with timed charts. 
    Results showed significant improvement in fluency and accuracy of math facts calculation. 
    The findings suggest that PT can be an effective strategy for higher education contexts.
    """
    
    full_text = f"{title}\n{abstract}"
    
    print("\nEnviando request de classificação...")
    try:
        category, confidence = await provider.classify(full_text)
        print(f"\nResultado:")
        print(f"  Categoria: {category}")
        print(f"  Confiança: {confidence}")
        
        if category in ["educacao", "pesquisa"]:
            print("\n✅ Teste passou! Classificação faz sentido.")
        else:
            print(f"\n⚠️ Aviso: Classificação '{category}' foi inesperada, mas a API respondeu.")
            
    except Exception as e:
        print(f"\n❌ Erro na chamada da API: {e}")

if __name__ == "__main__":
    asyncio.run(test_deepseek())
