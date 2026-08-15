"""Midnight cron scheduler for Drive sync + incremental reindex."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import RUNBOOK_CRON_ENABLED, RUNBOOK_CRON_SCHEDULE
from app.jobs import run_pipeline

logger = logging.getLogger("runbook-ingestion.scheduler")


def _parse_cron(expr: str) -> CronTrigger:
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (need 5 fields): {expr}")
    minute, hour, day, month, day_of_week = parts
    return CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)


def start_scheduler() -> BackgroundScheduler | None:
    if not RUNBOOK_CRON_ENABLED:
        logger.info("Runbook cron disabled")
        return None

    scheduler = BackgroundScheduler(timezone="UTC")
    trigger = _parse_cron(RUNBOOK_CRON_SCHEDULE)
    scheduler.add_job(
        lambda: run_pipeline(
            job_type="drive_sync_reindex",
            triggered_by="cron:midnight",
            mode="incremental",
            sync_drive=True,
        ),
        trigger=trigger,
        id="runbook-drive-incremental",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Scheduled runbook ingestion cron: %s UTC", RUNBOOK_CRON_SCHEDULE)
    return scheduler
