"""Ingestion job orchestration."""

from __future__ import annotations

import logging
import threading
from typing import Literal

from app.config import RUNBOOKS_DIR, SEED_RUNBOOKS_DIR
from app.drive_sync import sync_google_drive_folder
from app.models import IngestionJob, SessionLocal, create_job, utcnow
from rag.indexer import active_manifest_path, index_runbooks, read_active_collection, seed_runbooks_from_git

logger = logging.getLogger("runbook-ingestion.jobs")
_lock = threading.Lock()


def _set_job_running(job_id: str) -> IngestionJob:
    with SessionLocal() as session:
        job = session.get(IngestionJob, job_id)
        if not job:
            raise RuntimeError(f"Unknown job: {job_id}")
        job.status = "running"
        job.started_at = utcnow()
        session.commit()
        session.refresh(job)
        return job


def _finish_job(
    job_id: str,
    *,
    status: str,
    index_version: str | None = None,
    documents_indexed: int = 0,
    runbooks_changed: int = 0,
    drive_files_synced: int = 0,
    error_message: str | None = None,
) -> None:
    with SessionLocal() as session:
        job = session.get(IngestionJob, job_id)
        if not job:
            return
        job.status = status
        job.finished_at = utcnow()
        job.index_version = index_version
        job.documents_indexed = documents_indexed
        job.runbooks_changed = runbooks_changed
        job.drive_files_synced = drive_files_synced
        job.error_message = error_message
        session.commit()


def run_pipeline(
    *,
    job_type: Literal["full_reindex", "incremental_reindex", "drive_sync_reindex"],
    triggered_by: str,
    mode: Literal["full", "incremental"] = "incremental",
    sync_drive: bool = True,
) -> IngestionJob:
    with SessionLocal() as session:
        job = create_job(session, job_type=job_type, triggered_by=triggered_by)

    def _worker() -> None:
        if not _lock.acquire(blocking=False):
            _finish_job(job.id, status="failed", error_message="Another ingestion job is running")
            return
        try:
            _set_job_running(job.id)
            seed_runbooks_from_git(SEED_RUNBOOKS_DIR, RUNBOOKS_DIR)

            drive_stats = {"synced": 0}
            if sync_drive:
                drive_stats = sync_google_drive_folder()

            index_mode = "full" if mode == "full" or job_type == "full_reindex" else "incremental"
            result = index_runbooks(mode=index_mode)

            _finish_job(
                job.id,
                status="succeeded",
                index_version=result.index_version,
                documents_indexed=result.documents_indexed,
                runbooks_changed=len(result.changed_files),
                drive_files_synced=int(drive_stats.get("synced", 0)),
            )
            logger.info(
                "Ingestion job %s succeeded collection=%s version=%s",
                job.id,
                result.collection,
                result.index_version,
            )
        except Exception as exc:
            logger.exception("Ingestion job %s failed", job.id)
            _finish_job(job.id, status="failed", error_message=str(exc))
        finally:
            _lock.release()

    threading.Thread(target=_worker, name=f"ingestion-{job.id}", daemon=True).start()
    return job


def bootstrap_index_if_missing() -> str | None:
    if active_manifest_path().is_file():
        return read_active_collection()

    logger.info("Bootstrapping initial runbook index from seed corpus")
    RUNBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    seed_runbooks_from_git(SEED_RUNBOOKS_DIR, RUNBOOKS_DIR)
    result = index_runbooks(mode="full")
    return result.index_version
