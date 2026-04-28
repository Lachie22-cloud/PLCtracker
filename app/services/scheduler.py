"""APScheduler background scheduler — runs daily OData extraction."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import settings
from .extract import run_extraction

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _extraction_job() -> None:
    logger.info("Scheduled extraction starting")
    summary = run_extraction(source="odata", trigger="scheduler")
    if summary.error:
        logger.error("Extraction failed: %s", summary.error)
    else:
        logger.info(
            "Extraction complete: mara=%d marc=%d changes=%d violations=%d",
            summary.mara_count,
            summary.marc_count,
            summary.change_count,
            summary.violation_count,
        )


def start_scheduler() -> None:
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled (PLCT_SCHEDULER_ENABLED=false)")
        return
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler()
    trigger = CronTrigger.from_crontab(settings.extraction_cron)
    _scheduler.add_job(_extraction_job, trigger, id="sap_extraction", replace_existing=True)
    _scheduler.start()
    logger.info("Scheduler started (cron: %s)", settings.extraction_cron)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
