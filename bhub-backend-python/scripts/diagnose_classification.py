"""
Script de diagnóstico para identificar onde a classificação está travando.
"""

import asyncio
import sys
from pathlib import Path

print("1. Iniciando diagnóstico...")
sys.path.insert(0, ".")

print("2. Importando módulos básicos...")
from app.core.logging import setup_logging, log
print("   ✓ Logging importado")

print("3. Inicializando logging...")
setup_logging()
print("   ✓ Logging inicializado")

print("4. Importando database...")
from app.database import init_db, get_session_context
print("   ✓ Database importado")

print("5. Inicializando banco de dados...")
try:
    asyncio.run(init_db())
    print("   ✓ Banco inicializado")
except Exception as e:
    print(f"   ✗ Erro ao inicializar banco: {e}")
    sys.exit(1)

print("6. Importando AI Manager...")
try:
    from app.ai import get_ai_manager
    print("   ✓ AI Manager importado")
except Exception as e:
    print(f"   ✗ Erro ao importar AI Manager: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("7. Criando AI Manager...")
try:
    ai_manager = get_ai_manager()
    print("   ✓ AI Manager criado")
except Exception as e:
    print(f"   ✗ Erro ao criar AI Manager: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("8. Configurando provedores...")
try:
    ai_manager._setup_providers()
    print(f"   ✓ Provedores configurados: {list(ai_manager.providers.keys())}")
except Exception as e:
    print(f"   ✗ Erro ao configurar provedores: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("9. Importando ClassificationService...")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "classification_service",
        Path(__file__).parent.parent / "app" / "services" / "classification_service.py"
    )
    classification_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(classification_module)
    ClassificationService = classification_module.ClassificationService
    print("   ✓ ClassificationService importado")
except Exception as e:
    print(f"   ✗ Erro ao importar ClassificationService: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("10. Testando classificação simples...")
async def test():
    async with get_session_context() as db:
        from sqlalchemy import select
        from app.models import Article

        result = await db.execute(select(Article).limit(1))
        article = result.scalar_one_or_none()

        if not article:
            print("   ✗ Nenhum artigo encontrado")
            return

        print(f"   ✓ Artigo encontrado: {article.title[:50]}...")

        text = f"{article.title} {article.abstract or ''}"
        print(f"   ✓ Texto preparado ({len(text)} caracteres)")

        print("   -> Chamando classify_with_multiple_categories...")
        try:
            categories = await ClassificationService.classify_with_multiple_categories(
                db=db,
                text=text,
                ai_manager=ai_manager,
                min_confidence=0.3,
            )
            print(f"   ✓ Classificação concluída: {categories}")
        except Exception as e:
            print(f"   ✗ Erro na classificação: {e}")
            import traceback
            traceback.print_exc()

try:
    asyncio.run(test())
    print("\n✓ Diagnóstico concluído com sucesso!")
except Exception as e:
    print(f"\n✗ Erro no teste: {e}")
    import traceback
    traceback.print_exc()
