"""
Sistema de jobs agendados.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from app.config import settings
from app.core.logging import log
from app.database import get_session_context


scheduler = AsyncIOScheduler(timezone=pytz.timezone("America/Sao_Paulo"))


async def sync_all_feeds_job():
    """Job para sincronizar todos os feeds."""
    log.bind(feed_sync=True).info("Iniciando job de sincronização de feeds")
    
    try:
        async with get_session_context() as db:
            from app.services import FeedAggregatorService
            
            service = FeedAggregatorService(db)
            result = await service.sync_all_active_feeds()
            await service.close()
            
            log.bind(feed_sync=True).info(
                f"Sincronização concluída: {result.successful}/{result.total_feeds} feeds, "
                f"{result.new_articles} novos artigos"
            )
    
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
    
    # Sincronização de feeds a cada hora
    scheduler.add_job(
        sync_all_feeds_job,
        CronTrigger(minute=0),  # A cada hora, no minuto 0
        id="sync_feeds",
        name="Sincronização de Feeds",
        replace_existing=True,
    )
    
    log.info("Jobs agendados configurados")


def start_scheduler():
    """Inicia o scheduler."""
    if not settings.enable_scheduler:
        return
    
    if not scheduler.running:
        scheduler.start()
        log.info("Scheduler iniciado")


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
