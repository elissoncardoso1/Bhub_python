"""
Serviço de cache de traduções.
Gerencia o cache de traduções para evitar chamadas repetidas à API.
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.models.translation_cache import TranslationCache


def normalize_text(text: str) -> str:
    """
    Normaliza texto para consistência no cache.
    
    Args:
        text: Texto a normalizar
        
    Returns:
        Texto normalizado
    """
    # Remove espaços em branco no início e fim
    text = text.strip()
    
    # Remove espaços duplicados
    text = re.sub(r'\s+', ' ', text)
    
    # Mantém case-sensitive para preservar termos técnicos
    # Mas remove espaços extras e normaliza quebras de linha
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)
    
    return text


def generate_cache_key(
    text: str,
    source_lang: str,
    target_lang: str,
    model_version: str = "deepseek-chat",
) -> str:
    """
    Gera chave de cache única baseada no texto e parâmetros.
    
    Args:
        text: Texto a traduzir
        source_lang: Idioma de origem
        target_lang: Idioma de destino
        model_version: Versão do modelo usado
        
    Returns:
        Hash SHA256 em hexadecimal
    """
    normalized = normalize_text(text)
    
    # Constrói string única
    key_data = f"{source_lang}|{target_lang}|{normalized}|{model_version}"
    
    # Gera hash SHA256
    hash_obj = hashlib.sha256(key_data.encode('utf-8'))
    return hash_obj.hexdigest()


class TranslationCacheService:
    """Serviço para gerenciar cache de traduções."""
    
    @staticmethod
    async def get_cached_translation(
        session: AsyncSession,
        cache_key: str,
    ) -> TranslationCache | None:
        """
        Busca tradução no cache.
        
        Args:
            session: Sessão do banco de dados
            cache_key: Chave de cache (hash)
            
        Returns:
            TranslationCache se encontrado, None caso contrário
        """
        stmt = select(TranslationCache).where(
            TranslationCache.content_hash == cache_key
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_access_time(
        session: AsyncSession,
        cache_key: str,
    ) -> None:
        """
        Atualiza timestamp de último acesso.
        
        Args:
            session: Sessão do banco de dados
            cache_key: Chave de cache
        """
        stmt = (
            update(TranslationCache)
            .where(TranslationCache.content_hash == cache_key)
            .values(last_accessed_at=datetime.utcnow())
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def save_translation(
        session: AsyncSession,
        cache_key: str,
        original_text: str,
        translated_text: str,
        source_language: str,
        target_language: str,
        model: str = "deepseek-chat",
        provider: str | None = None,
    ) -> TranslationCache:
        """
        Salva tradução no cache.
        
        Args:
            session: Sessão do banco de dados
            cache_key: Chave de cache
            original_text: Texto original
            translated_text: Texto traduzido
            source_language: Idioma de origem
            target_language: Idioma de destino
            model: Modelo usado
            provider: Provedor de IA usado
            
        Returns:
            TranslationCache criado
        """
        translation_cache = TranslationCache(
            content_hash=cache_key,
            original_text=original_text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            model=model,
            provider=provider,
            last_accessed_at=datetime.utcnow(),
        )
        
        session.add(translation_cache)
        await session.commit()
        await session.refresh(translation_cache)
        
        log.info(
            f"Tradução salva no cache: {cache_key[:8]}... "
            f"({source_language} -> {target_language})"
        )
        
        return translation_cache
    
    @staticmethod
    async def clean_old_translations(
        session: AsyncSession,
        days: int = 30,
    ) -> int:
        """
        Remove traduções não acessadas há mais de X dias.
        
        Args:
            session: Sessão do banco de dados
            days: Número de dias sem acesso para considerar obsoleto
            
        Returns:
            Número de traduções removidas
        """
        from sqlalchemy import delete
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = delete(TranslationCache).where(
            TranslationCache.last_accessed_at < cutoff_date
        )
        
        result = await session.execute(stmt)
        await session.commit()
        
        count = result.rowcount
        if count > 0:
            log.info(f"Removidas {count} traduções antigas do cache")
        
        return count
    
    @staticmethod
    async def get_cache_stats(session: AsyncSession) -> dict:
        """
        Retorna estatísticas do cache.
        
        Args:
            session: Sessão do banco de dados
            
        Returns:
            Dicionário com estatísticas
        """
        from sqlalchemy import func
        
        # Total de traduções
        total_stmt = select(func.count(TranslationCache.id))
        total_result = await session.execute(total_stmt)
        total = total_result.scalar() or 0
        
        # Traduções por idioma
        lang_stmt = (
            select(
                TranslationCache.source_language,
                TranslationCache.target_language,
                func.count(TranslationCache.id).label("count"),
            )
            .group_by(
                TranslationCache.source_language,
                TranslationCache.target_language,
            )
        )
        lang_result = await session.execute(lang_stmt)
        by_language = [
            {
                "source": row.source_language,
                "target": row.target_language,
                "count": row.count,
            }
            for row in lang_result
        ]
        
        # Traduções mais antigas
        oldest_stmt = (
            select(TranslationCache)
            .order_by(TranslationCache.last_accessed_at.asc())
            .limit(1)
        )
        oldest_result = await session.execute(oldest_stmt)
        oldest = oldest_result.scalar_one_or_none()
        
        return {
            "total": total,
            "by_language": by_language,
            "oldest_access": oldest.last_accessed_at.isoformat() if oldest else None,
        }

