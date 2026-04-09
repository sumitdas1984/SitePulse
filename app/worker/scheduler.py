"""APScheduler service for managing monitor check jobs."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.models import Monitor

scheduler = AsyncIOScheduler()


def add_monitor_job(monitor: Monitor) -> None:
    """Add a new scheduled job for a monitor."""
    from app.worker.runner import run_check

    scheduler.add_job(
        run_check,
        trigger=IntervalTrigger(minutes=monitor.interval_minutes),
        args=[monitor.id],
        id=monitor.id,
        replace_existing=True,
    )


def remove_monitor_job(monitor_id: str) -> None:
    """Remove a scheduled job for a monitor."""
    try:
        scheduler.remove_job(monitor_id)
    except Exception:
        pass


def reschedule_monitor_job(monitor: Monitor) -> None:
    """Reschedule a monitor job with new interval."""
    from app.worker.runner import run_check

    scheduler.reschedule_job(
        monitor.id,
        trigger=IntervalTrigger(minutes=monitor.interval_minutes),
    )
