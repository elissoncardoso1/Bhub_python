"""
Sistema de jobs agendados.
"""

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.core.logging import log
from app.core.scheduler_lock import distributed_lock
from app.database import get_session_context

scheduler = AsyncIOScheduler(timezone=pytz.timezone("America/Sao_Paulo"))


async def sync_all_feeds_job():
    """Job para sincronizar todos os feeds."""
    # Usar lock distribuído para prevenir execução duplicada
    lock_name = "sync_feeds"

    try:
        async with distributed_lock(lock_name):
            log.bind(feed_sync=True).info("Iniciando job de sincronização de feeds")

            async with get_session_context() as db:
                from app.services import FeedAggregatorService

                service = FeedAggregatorService(db)
                result = await service.sync_all_active_feeds()
                await service.close()

                log.bind(feed_sync=True).info(
                    f"Sincronização concluída: {result.successful}/{result.total_feeds} feeds, "
                    f"{result.new_articles} novos artigos"
                )
    except RuntimeError as e:
        # Lock não adquirido - outra instância está executando
        log.warning(f"Job {lock_name} não executado: {e}")
    except Exception as e:
        log.error(f"Erro no job de sincronização: {e}")


async def cleanup_old_logs_job():
    """Job para limpar logs antigos."""
    log.info("Executando limpeza de logs")
    # Implementar se necessário


def setup_scheduler():
    """Configura os jobs agendados."""
    if not settings.enable_scheduler:
        log.info("Scheduler desabilitado")
        return

    # Verificar modo do scheduler
    if settings.scheduler_mode == "off":
        log.info("Scheduler desabilitado (scheduler_mode=off)")
        return

    # Sincronização de feeds a cada hora
    scheduler.add_job(
        sync_all_feeds_job,
        CronTrigger(minute=0),  # A cada hora, no minuto 0
        id="sync_feeds",
        name="Sincronização de Feeds",
        replace_existing=True,
    )

    log.info(f"Jobs agendados configurados (mode={settings.scheduler_mode})")


def start_scheduler():
    """Inicia o scheduler."""
    if not settings.enable_scheduler:
        return

    if settings.scheduler_mode == "off":
        return

    if not scheduler.running:
        scheduler.start()
        log.info(f"Scheduler iniciado (mode={settings.scheduler_mode})")


def stop_scheduler():
    """Para o scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        log.info("Scheduler parado")


def get_scheduler_status() -> dict:
    """Retorna status do scheduler."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })

    return {
        "running": scheduler.running,
        "jobs": jobs,
    }
