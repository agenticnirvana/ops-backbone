"""Persist golden-set eval runs for platform UI (on-demand — no CI/CD required)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from shared.dashboard_metrics import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

_tables_ready = False


class Base(DeclarativeBase):
    pass


class AgentEvalRun(Base):
    __tablename__ = "agent_eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    triggered_by: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(32), default="platform")
    averages_json: Mapped[str] = mapped_column(Text, default="{}")
    thresholds_json: Mapped[str] = mapped_column(Text, default="{}")
    cases_json: Mapped[str] = mapped_column(Text, default="[]")
    error_message: Mapped[str | None] = mapped_column(Text)


def ensure_eval_tables() -> None:
    global _tables_ready
    if _tables_ready:
        return
    Base.metadata.create_all(bind=engine)
    _tables_ready = True


def save_eval_run(
    *,
    report: dict[str, Any],
    triggered_by: str | None = None,
    source: str = "platform",
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    ensure_eval_tables()
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    row = AgentEvalRun(
        id=run_id,
        started_at=started_at or now,
        finished_at=finished_at or now,
        passed=bool(report.get("passed")),
        case_count=int(report.get("case_count") or 0),
        triggered_by=triggered_by,
        source=source,
        averages_json=json.dumps(report.get("averages") or {}),
        thresholds_json=json.dumps(report.get("thresholds") or {}),
        cases_json=json.dumps(report.get("cases") or []),
        error_message=error_message,
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return eval_run_to_dict(row)


def list_eval_runs(*, limit: int = 20) -> list[dict[str, Any]]:
    ensure_eval_tables()
    with SessionLocal() as session:
        rows = session.scalars(
            select(AgentEvalRun).order_by(AgentEvalRun.started_at.desc()).limit(limit)
        ).all()
        return [eval_run_to_dict(r) for r in rows]


def get_latest_eval_run() -> dict[str, Any] | None:
    runs = list_eval_runs(limit=1)
    return runs[0] if runs else None


def get_eval_run(run_id: str) -> dict[str, Any] | None:
    ensure_eval_tables()
    with SessionLocal() as session:
        row = session.get(AgentEvalRun, run_id)
        return eval_run_to_dict(row) if row else None


def eval_run_to_dict(row: AgentEvalRun) -> dict[str, Any]:
    cases = json.loads(row.cases_json or "[]")
    cases_passed = sum(1 for c in cases if c.get("passed"))
    cases_failed = len(cases) - cases_passed
    return {
        "id": row.id,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "passed": row.passed,
        "case_count": row.case_count,
        "cases_passed": cases_passed,
        "cases_failed": cases_failed,
        "triggered_by": row.triggered_by,
        "source": row.source,
        "averages": json.loads(row.averages_json or "{}"),
        "thresholds": json.loads(row.thresholds_json or "{}"),
        "cases": cases,
        "error_message": row.error_message,
    }
