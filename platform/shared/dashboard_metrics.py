"""Platform dashboard metrics — persisted in PostgreSQL (agentops DB)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import DateTime, Integer, Numeric, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://agentops:agentops@postgres:5432/agentops",
)


class Base(DeclarativeBase):
    pass


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(32), default="standalone")
    domain: Mapped[str] = mapped_column(String(32), default="sre")
    service: Mapped[str | None] = mapped_column(String(128))
    severity: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), index=True)
    runbook_id: Mapped[str | None] = mapped_column(String(128))
    triggered_by: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    hitl_required: Mapped[bool] = mapped_column(default=False)
    ticket_id: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    active_pipelines: Mapped[int] = mapped_column(Integer)
    p1_alerts: Mapped[int] = mapped_column(Integer)
    agents_online: Mapped[int] = mapped_column(Integer)
    success_rate_pct: Mapped[float] = mapped_column(Numeric(5, 2))
    mttr_seconds: Mapped[int | None] = mapped_column(Integer)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

_tables_ready = False


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_tables() -> None:
    global _tables_ready
    if _tables_ready:
        return
    Base.metadata.create_all(bind=engine)
    _tables_ready = True


def _format_duration(seconds: int | None) -> str:
    if seconds is None or seconds <= 0:
        return "—"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _trend_label(current: float, previous: float, *, invert: bool = False) -> str:
    if previous <= 0 and current <= 0:
        return "—"
    if previous <= 0:
        delta_pct = 100.0
    else:
        delta_pct = ((current - previous) / previous) * 100.0
    if invert:
        delta_pct = -delta_pct
    if abs(delta_pct) < 0.05:
        return "—"
    arrow = "↑" if delta_pct > 0 else "↓"
    return f"{arrow} {abs(delta_pct):.1f}%"


def _probe_service(url: str, timeout: float = 2.0) -> bool:
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url)
            return r.status_code < 400
    except Exception:
        return False


def count_agents_online() -> int:
    from shared import config

    checks = [
        f"{config.AGENT_URL}/health",
        f"{config.INGESTION_URL.rstrip('/')}/health",
        f"{config.TICKET_API_URL.rstrip('/')}/health",
    ]
    mcp_base = os.getenv("MCP_HTTP_URL", "http://mcp-server:8081").rstrip("/")
    mcp_user = os.getenv("MCP_BASIC_USER", "mcp")
    mcp_pass = os.getenv("MCP_BASIC_PASSWORD", "mcp-secret")
    online = sum(1 for url in checks if _probe_service(url))
    try:
        with httpx.Client(timeout=3.0) as client:
            r = client.get(f"{mcp_base}/health", auth=(mcp_user, mcp_pass))
            if r.status_code < 400:
                online += 1
    except Exception:
        pass
    return online


def record_run_start(
    *,
    thread_id: str,
    mode: str,
    domain: str,
    service: str | None,
    severity: str | None,
    status: str,
    runbook_id: str | None = None,
    triggered_by: str | None = None,
    source: str | None = "platform",
    hitl_required: bool = False,
) -> None:
    ensure_tables()
    now = utcnow()
    with SessionLocal() as session:
        existing = session.scalar(select(AgentRun).where(AgentRun.thread_id == thread_id))
        if existing:
            existing.status = status
            existing.service = service or existing.service
            existing.severity = severity or existing.severity
            existing.runbook_id = runbook_id or existing.runbook_id
            existing.hitl_required = hitl_required or existing.hitl_required
            existing.triggered_by = triggered_by or existing.triggered_by
            existing.source = source or existing.source
            if status == "running" and not existing.started_at:
                existing.started_at = now
        else:
            session.add(
                AgentRun(
                    id=str(uuid.uuid4()),
                    thread_id=thread_id,
                    mode=mode,
                    domain=domain,
                    service=service,
                    severity=severity,
                    status=status,
                    runbook_id=runbook_id,
                    triggered_by=triggered_by,
                    source=source,
                    started_at=now,
                    hitl_required=hitl_required,
                )
            )
        session.commit()


def record_run_finish(
    *,
    thread_id: str,
    status: str,
    runbook_id: str | None = None,
    ticket_id: str | None = None,
    hitl_required: bool | None = None,
    error_message: str | None = None,
) -> None:
    ensure_tables()
    now = utcnow()
    with SessionLocal() as session:
        run = session.scalar(select(AgentRun).where(AgentRun.thread_id == thread_id))
        if not run:
            return
        run.status = status
        run.finished_at = now
        if runbook_id:
            run.runbook_id = runbook_id
        if ticket_id:
            run.ticket_id = ticket_id
        if hitl_required is not None:
            run.hitl_required = hitl_required
        if error_message:
            run.error_message = error_message
        if run.started_at:
            run.duration_seconds = max(1, int((now - run.started_at).total_seconds()))
        session.commit()


def get_dashboard_stats() -> dict[str, Any]:
    ensure_tables()
    now = utcnow()
    active_statuses = ("running", "awaiting_hitl")
    agents_online = count_agents_online()
    prev_for_trend: MetricSnapshot | None = None

    with SessionLocal() as session:
        active_pipelines = session.scalar(
            select(func.count()).select_from(AgentRun).where(AgentRun.status.in_(active_statuses))
        ) or 0
        p1_alerts = session.scalar(
            select(func.count())
            .select_from(AgentRun)
            .where(AgentRun.severity == "P1", AgentRun.status.in_(active_statuses))
        ) or 0

        terminal = session.scalars(
            select(AgentRun).where(AgentRun.status.in_(("completed", "failed", "cancelled")))
        ).all()
        completed = [r for r in terminal if r.status == "completed"]
        failed = [r for r in terminal if r.status == "failed"]
        total_terminal = len(completed) + len(failed)
        success_rate = round((len(completed) / total_terminal) * 100, 1) if total_terminal else 100.0

        durations = [r.duration_seconds for r in completed if r.duration_seconds]
        mttr_seconds = int(sum(durations) / len(durations)) if durations else None

        prev = session.scalar(
            select(MetricSnapshot).order_by(MetricSnapshot.captured_at.desc()).limit(1)
        )
        last_snap_at = prev.captured_at if prev else None
        if not last_snap_at or (now - last_snap_at) > timedelta(hours=1):
            session.add(
                MetricSnapshot(
                    captured_at=now,
                    active_pipelines=active_pipelines,
                    p1_alerts=p1_alerts,
                    agents_online=agents_online,
                    success_rate_pct=success_rate,
                    mttr_seconds=mttr_seconds,
                )
            )
            session.commit()
            prev_for_trend = session.scalar(
                select(MetricSnapshot)
                .where(MetricSnapshot.captured_at < now - timedelta(minutes=30))
                .order_by(MetricSnapshot.captured_at.desc())
                .limit(1)
            )
        else:
            prev_for_trend = session.scalar(
                select(MetricSnapshot)
                .where(MetricSnapshot.id != prev.id)
                .order_by(MetricSnapshot.captured_at.desc())
                .limit(1)
            ) if prev else None

    prev_pipelines = int(prev_for_trend.active_pipelines) if prev_for_trend else active_pipelines
    prev_p1 = int(prev_for_trend.p1_alerts) if prev_for_trend else p1_alerts
    prev_success = float(prev_for_trend.success_rate_pct) if prev_for_trend else success_rate
    prev_mttr = int(prev_for_trend.mttr_seconds or 0) if prev_for_trend and prev_for_trend.mttr_seconds else (mttr_seconds or 0)

    return {
        "source": "postgresql",
        "active_pipelines": active_pipelines,
        "active_pipelines_trend": _trend_label(active_pipelines, prev_pipelines),
        "p1_alerts": p1_alerts,
        "p1_alerts_trend": f"↑ {p1_alerts}" if p1_alerts else "—",
        "agents_online": agents_online,
        "agents_online_trend": _trend_label(agents_online, prev_for_trend.agents_online if prev_for_trend else agents_online),
        "success_rate": f"{success_rate:.1f}%",
        "success_rate_trend": _trend_label(success_rate, prev_success),
        "mttr": _format_duration(mttr_seconds),
        "mttr_seconds": mttr_seconds,
        "mttr_trend": _trend_label(float(mttr_seconds or 0), float(prev_mttr), invert=True),
        "total_runs": total_terminal + active_pipelines,
        "completed_runs": len(completed),
    }


def list_recent_runs(*, limit: int = 15) -> list[dict[str, Any]]:
    ensure_tables()
    with SessionLocal() as session:
        rows = session.scalars(
            select(AgentRun).order_by(AgentRun.started_at.desc()).limit(max(1, min(limit, 50)))
        ).all()
    return [
        {
            "thread_id": r.thread_id,
            "service": r.service,
            "severity": r.severity,
            "status": r.status,
            "triggered_by": r.triggered_by,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "duration_seconds": r.duration_seconds,
        }
        for r in rows
    ]
