"""
Sistema de lock distribuído para prevenir execução duplicada de jobs.
"""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.database import get_session_context
from app.models.scheduler_lock import SchedulerLock

# ID único desta instância
INSTANCE_ID = os.getenv("SCHEDULER_INSTANCE_ID", str(uuid.uuid4()))

# TTL padrão para locks (30 minutos)
DEFAULT_LOCK_TTL = timedelta(minutes=30)

# Intervalo de heartbeat (5 minutos)
HEARTBEAT_INTERVAL = timedelta(minutes=5)


async def acquire_lock(
    lock_name: str,
    ttl: timedelta = DEFAULT_LOCK_TTL,
    instance_id: str | None = None,
) -> bool:
    """
    Tenta adquirir um lock distribuído.

    Args:
        lock_name: Nome do lock (ex: "sync_feeds")
        ttl: Tempo de vida do lock
        instance_id: ID da instância (default: INSTANCE_ID global)

    Returns:
        True se o lock foi adquirido, False caso contrário
    """
    if instance_id is None:
        instance_id = INSTANCE_ID

    now = datetime.utcnow()
    expires_at = now + ttl

    async with get_session_context() as db:
        try:
            # Limpar locks expirados primeiro
            await cleanup_expired_locks(db)

            # Tentar adquirir lock
            # Estratégia: INSERT com ON CONFLICT (SQLite) ou SELECT FOR UPDATE (PostgreSQL)
            # Para SQLite, usamos INSERT OR IGNORE

            # Verificar se já existe lock ativo
            result = await db.execute(
                select(SchedulerLock).where(
                    SchedulerLock.lock_name == lock_name,
                    SchedulerLock.expires_at > now,
                )
            )
            existing_lock = result.scalar_one_or_none()

            if existing_lock:
                # Lock já existe e não expirou
                # Se for da mesma instância, atualizar heartbeat
                if existing_lock.instance_id == instance_id:
                    existing_lock.last_heartbeat = now
                    existing_lock.expires_at = expires_at
                    await db.commit()
                    log.debug(f"Lock {lock_name} renovado por {instance_id}")
                    return True
                else:
                    # Outra instância possui o lock
                    log.debug(f"Lock {lock_name} já adquirido por {existing_lock.instance_id}")
                    return False

            # Criar novo lock
            lock = SchedulerLock(
                lock_name=lock_name,
                instance_id=instance_id,
                acquired_at=now,
                expires_at=expires_at,
                last_heartbeat=now,
            )
            db.add(lock)
            await db.commit()

            log.info(f"Lock {lock_name} adquirido por {instance_id}")
            return True

        except Exception as e:
            await db.rollback()
            log.error(f"Erro ao adquirir lock {lock_name}: {e}")
            return False


async def release_lock(lock_name: str, instance_id: str | None = None) -> bool:
    """
    Libera um lock distribuído.

    Args:
        lock_name: Nome do lock
        instance_id: ID da instância (default: INSTANCE_ID global)

    Returns:
        True se o lock foi liberado, False caso contrário
    """
    if instance_id is None:
        instance_id = INSTANCE_ID

    async with get_session_context() as db:
        try:
            result = await db.execute(
                select(SchedulerLock).where(
                    SchedulerLock.lock_name == lock_name,
                    SchedulerLock.instance_id == instance_id,
                )
            )
            lock = result.scalar_one_or_none()

            if lock:
                await db.execute(
                    sql_delete(SchedulerLock).where(
                        SchedulerLock.id == lock.id
                    )
                )
                await db.commit()
                log.info(f"Lock {lock_name} liberado por {instance_id}")
                return True
            else:
                log.warning(f"Lock {lock_name} não encontrado para {instance_id}")
                return False

        except Exception as e:
            await db.rollback()
            log.error(f"Erro ao liberar lock {lock_name}: {e}")
            return False


async def cleanup_expired_locks(db: AsyncSession) -> int:
    """
    Remove locks expirados do banco de dados.

    Returns:
        Número de locks removidos
    """
    try:
        now = datetime.utcnow()
        result = await db.execute(
            sql_delete(SchedulerLock).where(SchedulerLock.expires_at < now)
        )
        await db.commit()
        count = result.rowcount
        if count > 0:
            log.debug(f"Removidos {count} locks expirados")
        return count
    except Exception as e:
        await db.rollback()
        log.error(f"Erro ao limpar locks expirados: {e}")
        return 0


@asynccontextmanager
async def distributed_lock(lock_name: str, ttl: timedelta = DEFAULT_LOCK_TTL):
    """
    Context manager para usar lock distribuído.

    Usage:
        async with distributed_lock("sync_feeds"):
            # Código que precisa de lock exclusivo
            await sync_all_feeds_job()
    """
    acquired = await acquire_lock(lock_name, ttl)

    if not acquired:
        raise RuntimeError(f"Não foi possível adquirir lock {lock_name}")

    try:
        yield
    finally:
        await release_lock(lock_name)
