"""Runbook ingestion API — on-demand reindex + status."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.config import INGESTION_API_TOKEN
from app.index_browser import (
    drive_status,
    get_chunk_by_id,
    list_collections,
    list_index_chunks,
    query_index,
)
from app.jobs import bootstrap_index_if_missing, run_pipeline
from app.models import Base, IngestionJob, SessionLocal, engine
from app.scheduler import start_scheduler
from rag.indexer import active_manifest_path, read_active_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("runbook-ingestion")


class ReindexRequest(BaseModel):
    mode: Literal["full", "incremental"] = "incremental"
    sync_drive: bool = True


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    triggered_by: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    index_version: str | None = None
    documents_indexed: int = 0
    runbooks_changed: int = 0
    drive_files_synced: int = 0
    error_message: str | None = None


class StatusResponse(BaseModel):
    status: str
    active_collection: str
    index_version: str | None = None
    manifest_path: str
    drive: dict
    latest_job: JobResponse | None = None


class IndexChunkResponse(BaseModel):
    id: str
    chunk_index: int
    preview: str
    document: str | None = None
    char_count: int
    token_estimate: int | None = None
    service: str | None = None
    severity: str | None = None
    domain: str | None = None
    source: str | None = None
    runbook_id: str | None = None
    metadata: dict | None = None
    embedding_dims: int | None = None
    embedding_preview: list[float] | None = None


class IndexRunbookResponse(BaseModel):
    runbook_id: str
    service: str | None = None
    severity: str | None = None
    domain: str | None = None
    source: str | None = None
    chunk_count: int
    total_chars: int | None = None
    chunks: list[IndexChunkResponse]


class IndexBrowseResponse(BaseModel):
    collection: str
    chroma_path: str
    total_chunks: int
    total_in_collection: int = 0
    runbook_count: int
    embedding_dims: int | None = None
    index_version: str | None = None
    activated_at: str | None = None
    distance_metric: str | None = "cosine"
    embedding_model: str | None = None
    services: list[str] = []
    severities: list[str] = []
    runbooks: list[IndexRunbookResponse]
    error: str | None = None


class IndexQueryRequest(BaseModel):
    query: str
    n_results: int = 5
    collection: str | None = None
    service: str | None = None
    severity: str | None = None
    runbook_id: str | None = None


def verify_token(authorization: str | None = Header(default=None), x_api_token: str | None = Header(default=None)) -> str:
    token = x_api_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token or token != INGESTION_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid ingestion API token")
    return token


def _job_to_response(job: IngestionJob) -> JobResponse:
    return JobResponse(
        id=str(job.id),
        job_type=job.job_type,
        status=job.status,
        triggered_by=job.triggered_by,
        started_at=job.started_at,
        finished_at=job.finished_at,
        index_version=job.index_version,
        documents_indexed=job.documents_indexed,
        runbooks_changed=job.runbooks_changed,
        drive_files_synced=job.drive_files_synced,
        error_message=job.error_message,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    bootstrap_index_if_missing()
    start_scheduler()
    logger.info("Runbook ingestion service ready")
    yield


app = FastAPI(title="Runbook Ingestion", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/ingest/status", response_model=StatusResponse)
def ingest_status(_: str = Depends(verify_token)) -> StatusResponse:
    manifest_path = active_manifest_path()
    index_version = None
    if manifest_path.is_file():
        import json

        try:
            index_version = json.loads(manifest_path.read_text(encoding="utf-8")).get("index_version")
        except json.JSONDecodeError:
            index_version = None

    with SessionLocal() as session:
        latest = session.scalars(
            select(IngestionJob).order_by(IngestionJob.started_at.desc().nullslast()).limit(1)
        ).first()

    return StatusResponse(
        status="ready",
        active_collection=read_active_collection(),
        index_version=index_version,
        manifest_path=str(manifest_path),
        drive=drive_status(),
        latest_job=_job_to_response(latest) if latest else None,
    )


@app.get("/v1/ingest/index", response_model=IndexBrowseResponse)
def ingest_index(limit: int = 500, collection: str | None = None, _: str = Depends(verify_token)) -> IndexBrowseResponse:
    payload = list_index_chunks(limit=min(max(limit, 1), 2000), collection=collection)
    return IndexBrowseResponse(**payload)


@app.get("/v1/ingest/index/collections")
def ingest_index_collections(_: str = Depends(verify_token)) -> dict:
    return list_collections()


@app.get("/v1/ingest/index/chunks/{chunk_id}")
def ingest_index_chunk(chunk_id: str, collection: str | None = None, _: str = Depends(verify_token)) -> dict:
    result = get_chunk_by_id(chunk_id, collection=collection)
    if result is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.post("/v1/ingest/index/query")
def ingest_index_query(body: IndexQueryRequest, _: str = Depends(verify_token)) -> dict:
    return query_index(
        query_text=body.query,
        n_results=body.n_results,
        collection=body.collection,
        service=body.service,
        severity=body.severity,
        runbook_id=body.runbook_id,
    )


@app.post("/v1/ingest/reindex", response_model=JobResponse)
def reindex(body: ReindexRequest, _: str = Depends(verify_token)) -> JobResponse:
    job = run_pipeline(
        job_type="full_reindex" if body.mode == "full" else "incremental_reindex",
        triggered_by="api:reindex",
        mode=body.mode,
        sync_drive=body.sync_drive,
    )
    return _job_to_response(job)


@app.post("/v1/ingest/sync-drive", response_model=JobResponse)
def sync_drive(_: str = Depends(verify_token)) -> JobResponse:
    job = run_pipeline(
        job_type="drive_sync_reindex",
        triggered_by="api:sync-drive",
        mode="incremental",
        sync_drive=True,
    )
    return _job_to_response(job)


@app.get("/v1/ingest/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, _: str = Depends(verify_token)) -> JobResponse:
    with SessionLocal() as session:
        job = session.get(IngestionJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return _job_to_response(job)
