"""SQLAlchemy models for ingestion job tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    triggered_by: Mapped[str] = mapped_column(String(128), default="system")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    index_version: Mapped[str | None] = mapped_column(String(64))
    documents_indexed: Mapped[int] = mapped_column(Integer, default=0)
    runbooks_changed: Mapped[int] = mapped_column(Integer, default=0)
    drive_files_synced: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class RunbookSource(Base):
    __tablename__ = "runbook_sources"

    source_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32))
    file_name: Mapped[str] = mapped_column(String(256))
    remote_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    local_path: Mapped[str | None] = mapped_column(String(512))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_job(session: Session, *, job_type: str, triggered_by: str) -> IngestionJob:
    job = IngestionJob(
        id=str(uuid.uuid4()),
        job_type=job_type,
        status="pending",
        triggered_by=triggered_by,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
