"""Ticket API — persists remediation records in PostgreSQL."""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ticket-api")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://agentops:agentops@postgres:5432/agentops",
)


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    service: Mapped[str] = mapped_column(String(128), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="open")
    summary: Mapped[str] = mapped_column(Text)
    runbook_id: Mapped[str] = mapped_column(String(128))
    approved_by: Mapped[str] = mapped_column(String(128), default="agent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TicketCreate(BaseModel):
    service: str
    severity: str = "P3"
    action: str = "remediation"
    recommendation: str
    runbook_id: str
    approved_by: str = "agent"


class TicketResponse(BaseModel):
    id: str
    ticket_id: str
    service: str
    severity: str
    status: str
    summary: str
    runbook_id: str
    approved_by: str
    created_at: datetime


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Ticket API ready")
    yield


app = FastAPI(title="Ticket API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(select(Ticket).limit(1))
    return {"status": "ok"}


@app.post("/tickets", response_model=TicketResponse)
def create_ticket(payload: TicketCreate) -> TicketResponse:
    ticket_id = f"OPS-{uuid.uuid4().hex[:8].upper()}"
    record = Ticket(
        id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        service=payload.service,
        severity=payload.severity,
        status="open",
        summary=payload.recommendation[:500],
        runbook_id=payload.runbook_id,
        approved_by=payload.approved_by,
        created_at=datetime.now(timezone.utc),
    )
    with SessionLocal() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
    logger.info("Created ticket %s for service=%s", ticket_id, payload.service)
    return TicketResponse(
        id=record.id,
        ticket_id=record.ticket_id,
        service=record.service,
        severity=record.severity,
        status=record.status,
        summary=record.summary,
        runbook_id=record.runbook_id,
        approved_by=record.approved_by,
        created_at=record.created_at,
    )


@app.get("/tickets", response_model=list[TicketResponse])
def list_tickets(limit: int = 50) -> list[TicketResponse]:
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200")
    with SessionLocal() as session:
        rows = session.scalars(select(Ticket).order_by(Ticket.created_at.desc()).limit(limit)).all()
    return [
        TicketResponse(
            id=row.id,
            ticket_id=row.ticket_id,
            service=row.service,
            severity=row.severity,
            status=row.status,
            summary=row.summary,
            runbook_id=row.runbook_id,
            approved_by=row.approved_by,
            created_at=row.created_at,
        )
        for row in rows
    ]
