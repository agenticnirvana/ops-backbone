"""HITL approval / rejection audit log."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from shared.dashboard_metrics import Base, SessionLocal, ensure_tables, utcnow


class HitlDecision(Base):
    __tablename__ = "hitl_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    decided_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    change_run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    service: Mapped[str | None] = mapped_column(String(128))
    severity: Mapped[str | None] = mapped_column(String(16))
    runbook_id: Mapped[str | None] = mapped_column(String(128))
    recommendation: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(String(16), index=True)
    decided_by: Mapped[str] = mapped_column(String(128))
    opa_allowed: Mapped[bool | None] = mapped_column(Boolean)
    opa_rule: Mapped[str | None] = mapped_column(String(64))
    ticket_id: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text, default="")


def ensure_hitl_schema() -> None:
    ensure_tables()
    from sqlalchemy import text

    from shared.dashboard_metrics import engine

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE hitl_decisions ADD COLUMN IF NOT EXISTS reason TEXT DEFAULT ''"))


def change_run_id(thread_id: str) -> str:
    return f"CR-{(thread_id or '0000')[:4].upper()}"


def record_hitl_decision(
    *,
    thread_id: str,
    decision: str,
    decided_by: str,
    service: str | None = None,
    severity: str | None = None,
    runbook_id: str | None = None,
    recommendation: str | None = None,
    opa_allowed: bool | None = None,
    opa_rule: str | None = None,
    ticket_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    ensure_hitl_schema()
    row = HitlDecision(
        id=str(uuid.uuid4()),
        decided_at=utcnow(),
        thread_id=thread_id,
        change_run_id=change_run_id(thread_id),
        service=service,
        severity=severity,
        runbook_id=runbook_id,
        recommendation=(recommendation or "")[:4000],
        decision=decision,
        decided_by=decided_by,
        opa_allowed=opa_allowed,
        opa_rule=opa_rule,
        ticket_id=ticket_id,
        reason=(reason or "")[:4000],
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
    return _decision_to_dict(row)


def list_hitl_decisions(*, limit: int = 100, decision: str | None = None) -> list[dict[str, Any]]:
    ensure_hitl_schema()
    with SessionLocal() as session:
        stmt = select(HitlDecision).order_by(HitlDecision.decided_at.desc()).limit(limit)
        if decision in ("approved", "rejected"):
            stmt = stmt.where(HitlDecision.decision == decision)
        rows = session.scalars(stmt).all()
    return [_decision_to_dict(row) for row in rows]


def _decision_to_dict(row: HitlDecision) -> dict[str, Any]:
    return {
        "id": row.id,
        "decided_at": row.decided_at.isoformat(),
        "thread_id": row.thread_id,
        "change_run_id": row.change_run_id,
        "service": row.service,
        "severity": row.severity,
        "runbook_id": row.runbook_id,
        "recommendation": row.recommendation,
        "decision": row.decision,
        "decided_by": row.decided_by,
        "opa_allowed": row.opa_allowed,
        "opa_rule": row.opa_rule,
        "ticket_id": row.ticket_id,
        "reason": row.reason or "",
    }
