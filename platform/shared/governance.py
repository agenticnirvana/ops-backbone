"""Enterprise governance — eval gates, CI checks, promotions, audit.

GitHub org/repo stay as placeholders until wired. Demo data seeds so the
console is recordable without a live Actions connection.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://agentops:agentops@postgres:5432/agentops",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

_tables_ready = False


class Base(DeclarativeBase):
    pass


class GovPipelineRun(Base):
    __tablename__ = "gov_pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    workflow: Mapped[str] = mapped_column(String(64))
    check_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    conclusion: Mapped[str] = mapped_column(String(32))
    sha: Mapped[str] = mapped_column(String(40), default="")
    branch: Mapped[str] = mapped_column(String(64), default="main")
    triggered_by: Mapped[str] = mapped_column(String(128), default="ci")
    source: Mapped[str] = mapped_column(String(32), default="github")
    html_url: Mapped[str] = mapped_column(String(512), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")


class GovPromotion(Base):
    __tablename__ = "gov_promotions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    environment: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    sha: Mapped[str] = mapped_column(String(40), default="")
    requested_by: Mapped[str] = mapped_column(String(128))
    decided_by: Mapped[str | None] = mapped_column(String(128))
    eval_run_id: Mapped[str | None] = mapped_column(String(36))
    reason: Mapped[str] = mapped_column(Text, default="")
    decision_note: Mapped[str] = mapped_column(Text, default="")


class GovAuditEvent(Base):
    __tablename__ = "gov_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    resource: Mapped[str] = mapped_column(String(128))
    detail: Mapped[str] = mapped_column(Text, default="")


def github_config() -> dict[str, Any]:
    org = os.getenv("GITHUB_ORG", "agenticnirvana")
    repo = os.getenv("GITHUB_REPO", "ops-backbone")
    wired = org not in ("", "YOUR_GITHUB_ORG") and repo not in ("", "YOUR_GITHUB_REPO")
    base = f"https://github.com/{org}/{repo}" if wired else ""
    return {
        "org": org,
        "repo": repo,
        "wired": wired,
        "html_url": base,
        "actions_url": f"{base}/actions" if wired else "",
        "environments": ["staging", "production"],
        "required_checks": [
            "ci / lint",
            "ci / unit",
            "ci / secret-scan",
            "eval-gate / golden-set",
        ],
        "codeowners": [
            "* @agenticnirvana",
            "/agent/evals/ @agenticnirvana",
            "/deploy/config/opa/ @agenticnirvana",
        ],
        "secrets_needed": [
            "DESIGN1_INGESTION_URL",
            "DESIGN1_INGESTION_TOKEN",
            "GOVERNANCE_WEBHOOK_TOKEN",
        ],
    }


def control_catalog() -> list[dict[str, Any]]:
    return [
        {"id": "GOV-01", "name": "Pre-commit hooks", "domain": "supply-chain", "owner": "platform", "evidence": ".pre-commit-config.yaml + scripts/ci/local-gate.sh"},
        {"id": "GOV-02", "name": "Required CI checks", "domain": "change", "owner": "platform", "evidence": ".github/workflows/ci.yml"},
        {"id": "GOV-03", "name": "Eval gate on merge", "domain": "quality", "owner": "ml-evals", "evidence": ".github/workflows/eval-gate.yml · agent/evals/run_evals.py"},
        {"id": "GOV-04", "name": "Environment approvals", "domain": "change", "owner": "sre", "evidence": "GitHub Environments staging/production + promote.yml"},
        {"id": "GOV-05", "name": "CODEOWNERS dual review", "domain": "access", "owner": "security", "evidence": ".github/CODEOWNERS"},
        {"id": "GOV-06", "name": "OPA policy as code", "domain": "runtime", "owner": "security", "evidence": "deploy/config/opa/policy.rego"},
        {"id": "GOV-07", "name": "HITL dual control", "domain": "runtime", "owner": "sre", "evidence": "LangGraph interrupt_before hitl_gate"},
        {"id": "GOV-08", "name": "Secret scanning", "domain": "supply-chain", "owner": "security", "evidence": "gitleaks in CI + detect-private-key hook"},
        {"id": "GOV-09", "name": "Eval score thresholds", "domain": "quality", "owner": "ml-evals", "evidence": "THRESHOLDS in agent/evals/run_evals.py"},
        {"id": "GOV-10", "name": "Promotion four-eyes", "domain": "change", "owner": "sre", "evidence": "Requester cannot approve own promotion"},
    ]


def ensure_governance_tables() -> None:
    global _tables_ready
    if _tables_ready:
        return
    Base.metadata.create_all(bind=engine)
    _tables_ready = True
    _seed_if_empty()


def _seed_if_empty() -> None:
    with SessionLocal() as session:
        existing = session.scalars(select(GovPipelineRun).limit(1)).first()
        if existing:
            return
        now = datetime.now(timezone.utc)
        gh = github_config()
        sha = "a1b2c3d4e5f60789a1b2c3d4e5f60789a1b2c3d4"
        checks = [
            ("ci", "ci / lint", "completed", "success", "Ruff clean"),
            ("ci", "ci / unit", "completed", "success", "Pytest passed"),
            ("ci", "ci / secret-scan", "completed", "success", "Gitleaks: no leaks"),
            ("eval-gate", "eval-gate / golden-set", "completed", "success", "8/8 golden cases · RAG recall ≥ 0.85"),
            ("promote", "promote / production", "completed", "pending", "Waiting for environment reviewers"),
        ]
        for i, (wf, name, status, conclusion, summary) in enumerate(checks):
            session.add(
                GovPipelineRun(
                    id=str(uuid.uuid4()),
                    created_at=now - timedelta(minutes=40 - i * 6),
                    workflow=wf,
                    check_name=name,
                    status=status,
                    conclusion=conclusion,
                    sha=sha,
                    branch="main",
                    triggered_by="github-actions",
                    source="seed",
                    html_url=gh["actions_url"],
                    summary=summary,
                    details_json="{}",
                )
            )
        session.add(
            GovPromotion(
                id=str(uuid.uuid4()),
                created_at=now - timedelta(hours=2),
                decided_at=None,
                environment="production",
                status="pending",
                sha=sha,
                requested_by="operator@agentops.local",
                eval_run_id=None,
                reason="Promote eval-gated main after golden-set pass",
            )
        )
        session.add(
            GovAuditEvent(
                id=str(uuid.uuid4()),
                created_at=now - timedelta(hours=2),
                actor="operator@agentops.local",
                action="promotion.requested",
                resource="production",
                detail="sha a1b2c3d4 · waiting four-eyes approval",
            )
        )
        session.commit()


def _audit(*, actor: str, action: str, resource: str, detail: str = "") -> None:
    with SessionLocal() as session:
        session.add(
            GovAuditEvent(
                id=str(uuid.uuid4()),
                created_at=datetime.now(timezone.utc),
                actor=actor,
                action=action,
                resource=resource,
                detail=detail[:2000],
            )
        )
        session.commit()


def record_pipeline_run(
    *,
    workflow: str,
    check_name: str,
    conclusion: str,
    triggered_by: str,
    source: str = "platform",
    summary: str = "",
    details: dict[str, Any] | None = None,
    sha: str = "",
    branch: str = "main",
) -> dict[str, Any]:
    ensure_governance_tables()
    row = GovPipelineRun(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        workflow=workflow,
        check_name=check_name,
        status="completed",
        conclusion=conclusion,
        sha=sha,
        branch=branch,
        triggered_by=triggered_by,
        source=source,
        html_url=github_config().get("actions_url") or "",
        summary=summary[:500],
        details_json=json.dumps(details or {}),
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        return _run_dict(row)


def list_pipeline_runs(*, limit: int = 30) -> list[dict[str, Any]]:
    ensure_governance_tables()
    with SessionLocal() as session:
        rows = session.scalars(select(GovPipelineRun).order_by(GovPipelineRun.created_at.desc()).limit(limit)).all()
        return [_run_dict(r) for r in rows]


def list_promotions(*, limit: int = 20) -> list[dict[str, Any]]:
    ensure_governance_tables()
    with SessionLocal() as session:
        rows = session.scalars(select(GovPromotion).order_by(GovPromotion.created_at.desc()).limit(limit)).all()
        return [_promo_dict(r) for r in rows]


def list_audit(*, limit: int = 40) -> list[dict[str, Any]]:
    ensure_governance_tables()
    with SessionLocal() as session:
        rows = session.scalars(select(GovAuditEvent).order_by(GovAuditEvent.created_at.desc()).limit(limit)).all()
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "actor": r.actor,
                "action": r.action,
                "resource": r.resource,
                "detail": r.detail,
            }
            for r in rows
        ]


def request_promotion(
    *,
    environment: str,
    requested_by: str,
    reason: str = "",
    sha: str = "",
    eval_run_id: str | None = None,
) -> dict[str, Any]:
    ensure_governance_tables()
    env = environment if environment in ("staging", "production") else "staging"
    row = GovPromotion(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        environment=env,
        status="pending",
        sha=sha or "local",
        requested_by=requested_by,
        eval_run_id=eval_run_id,
        reason=reason[:1000],
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
    _audit(actor=requested_by, action="promotion.requested", resource=env, detail=reason)
    return _promo_dict(row)


def ingest_github_event(payload: dict[str, Any], *, triggered_by: str = "github") -> dict[str, Any]:
    """Map a GitHub workflow_run / check_run payload into a pipeline row."""
    ensure_governance_tables()
    wr = payload.get("workflow_run") or payload.get("check_run") or payload
    name = wr.get("name") or payload.get("check_name") or "github-check"
    workflow = (payload.get("workflow") or wr.get("path") or name).split("/")[-1]
    if "eval" in name.lower():
        workflow = "eval-gate"
    elif "promote" in name.lower():
        workflow = "promote"
    elif workflow in ("ci.yml", "ci"):
        workflow = "ci"
    conclusion = wr.get("conclusion") or payload.get("conclusion") or "success"
    status = wr.get("status") or payload.get("status") or "completed"
    sha = (wr.get("head_sha") or wr.get("head_sha") or payload.get("sha") or "")[:40]
    branch = wr.get("head_branch") or payload.get("branch") or "main"
    html_url = wr.get("html_url") or payload.get("html_url") or github_config().get("actions_url") or ""
    summary = wr.get("display_title") or payload.get("summary") or name
    return record_pipeline_run(
        workflow=str(workflow)[:64],
        check_name=str(name)[:128],
        conclusion=str(conclusion)[:32],
        triggered_by=triggered_by,
        source="github",
        summary=str(summary)[:500],
        details={"status": status, "run_id": wr.get("id"), "html_url": html_url},
        sha=sha,
        branch=str(branch)[:64],
    )


def decide_promotion(
    *,
    promotion_id: str,
    approved: bool,
    decided_by: str,
    note: str = "",
    actor_role: str = "operator",
) -> dict[str, Any]:
    ensure_governance_tables()
    with SessionLocal() as session:
        row = session.get(GovPromotion, promotion_id)
        if not row:
            raise KeyError("unknown promotion")
        if row.status != "pending":
            raise ValueError("promotion already decided")
        if row.requested_by.lower() == decided_by.lower():
            raise ValueError("four-eyes rule: requester cannot approve their own promotion")
        if row.environment == "production" and actor_role != "admin":
            raise ValueError("production promotions require an admin reviewer")
        row.status = "approved" if approved else "rejected"
        row.decided_by = decided_by
        row.decided_at = datetime.now(timezone.utc)
        row.decision_note = note[:1000]
        session.commit()
        session.refresh(row)
        result = _promo_dict(row)
    _audit(
        actor=decided_by,
        action="promotion.approved" if approved else "promotion.rejected",
        resource=result["environment"],
        detail=note,
    )
    return result


def overview() -> dict[str, Any]:
    ensure_governance_tables()
    runs = list_pipeline_runs(limit=20)
    promos = list_promotions(limit=10)
    pending = [p for p in promos if p["status"] == "pending"]
    latest_eval = next((r for r in runs if "eval" in r["workflow"]), None)
    failing = [r for r in runs if r["conclusion"] not in ("success", "pending", "skipped")]
    return {
        "github": github_config(),
        "controls": control_catalog(),
        "pending_promotions": len(pending),
        "failing_checks": len(failing),
        "latest_eval": latest_eval,
        "runs": runs[:8],
        "promotions": promos[:6],
        "posture": "needs_approval" if pending else ("failing" if failing else "healthy"),
    }


def _run_dict(row: GovPipelineRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "workflow": row.workflow,
        "check_name": row.check_name,
        "status": row.status,
        "conclusion": row.conclusion,
        "sha": row.sha,
        "branch": row.branch,
        "triggered_by": row.triggered_by,
        "source": row.source,
        "html_url": row.html_url,
        "summary": row.summary,
        "details": json.loads(row.details_json or "{}"),
    }


def _promo_dict(row: GovPromotion) -> dict[str, Any]:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "environment": row.environment,
        "status": row.status,
        "sha": row.sha,
        "requested_by": row.requested_by,
        "decided_by": row.decided_by,
        "eval_run_id": row.eval_run_id,
        "reason": row.reason,
        "decision_note": row.decision_note,
    }
