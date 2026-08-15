"""OPA guardrails — policy persistence, evaluation audit log, live reload."""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from shared.dashboard_metrics import Base, SessionLocal, ensure_tables, utcnow

DESTRUCTIVE_KEYWORDS = ("restart", "rollback", "kill", "delete", "scale-down")

POLICY_RULES = [
    {"id": "allow_non_destructive", "label": "Non-destructive recommendation", "effect": "allow"},
    {"id": "allow_p1_destructive", "label": "Destructive action + P1 severity", "effect": "allow"},
    {"id": "deny_destructive_not_p1", "label": "Destructive action on P2/P3", "effect": "deny"},
    {"id": "deny_default", "label": "Default deny (no matching allow rule)", "effect": "deny"},
]


class OpaEvaluation(Base):
    __tablename__ = "opa_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, index=True)
    reason: Mapped[str] = mapped_column(String(64))
    matched_rule: Mapped[str] = mapped_column(String(64))
    destructive: Mapped[bool] = mapped_column(Boolean, default=False)
    service: Mapped[str | None] = mapped_column(String(128))
    severity: Mapped[str | None] = mapped_column(String(16))
    recommendation: Mapped[str] = mapped_column(Text)
    thread_id: Mapped[str | None] = mapped_column(String(64), index=True)
    evaluated_by: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(32), default="ui_preview")


class OpaPolicyRevision(Base):
    __tablename__ = "opa_policy_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    saved_by: Mapped[str] = mapped_column(String(128))
    rego: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(String(256))


def policy_file_path() -> Path:
    env = os.getenv("OPA_POLICY_PATH", "").strip()
    if env:
        return Path(env)
    root = Path(__file__).resolve().parents[2]
    return root / "deploy" / "config" / "opa" / "policy.rego"


def read_policy_rego() -> str:
    path = policy_file_path()
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def is_destructive(recommendation: str) -> bool:
    text = recommendation.lower()
    return any(keyword in text for keyword in DESTRUCTIVE_KEYWORDS)


def matched_rule_for(*, allowed: bool, destructive: bool, severity: str) -> str:
    if allowed and not destructive:
        return "allow_non_destructive"
    if allowed and destructive and severity == "P1":
        return "allow_p1_destructive"
    if not allowed and destructive:
        return "deny_destructive_not_p1"
    return "deny_default"


def evaluate_with_opa(*, service: str, recommendation: str, severity: str) -> tuple[bool, str]:
    if os.getenv("OPENFGA_URL", "").rstrip("/"):
        from agent.tools.policy_check import check_action_allowed

        return check_action_allowed(service=service, recommendation=recommendation, severity=severity)
    opa_url = os.getenv("OPA_URL", "").rstrip("/")
    if not opa_url:
        return True, "opa_disabled"

    payload = {
        "input": {
            "service": service,
            "severity": severity,
            "recommendation": recommendation,
        }
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(f"{opa_url}/v1/data/agentops/allow", json=payload)
            response.raise_for_status()
            allowed = bool(response.json().get("result", False))
            return (True, "policy_allow") if allowed else (False, "policy_deny")
    except Exception as exc:
        if os.getenv("OPA_FAIL_OPEN", "false").lower() == "true":
            return True, f"opa_error_fail_open:{exc}"
        return False, f"opa_error:{exc}"


def build_evaluation_result(
    *,
    service: str,
    recommendation: str,
    severity: str,
    allowed: bool | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    destructive = is_destructive(recommendation)
    if allowed is None or reason is None:
        allowed, reason = evaluate_with_opa(
            service=service,
            recommendation=recommendation,
            severity=severity,
        )
    matched_rule = matched_rule_for(allowed=allowed, destructive=destructive, severity=severity)
    return {
        "allowed": allowed,
        "reason": reason,
        "destructive": destructive,
        "severity": severity,
        "service": service,
        "matched_rule": matched_rule,
        "opa_url": os.getenv("OPA_URL", "http://opa:8181"),
        "policy_path": str(policy_file_path()),
        "rules": POLICY_RULES[:3],
        "input": {
            "service": service,
            "severity": severity,
            "recommendation": recommendation,
        },
    }


def record_evaluation(
    *,
    result: dict[str, Any],
    evaluated_by: str | None = None,
    thread_id: str | None = None,
    source: str = "ui_preview",
) -> dict[str, Any]:
    ensure_tables()
    row = OpaEvaluation(
        id=str(uuid.uuid4()),
        evaluated_at=utcnow(),
        allowed=bool(result.get("allowed")),
        reason=str(result.get("reason", "")),
        matched_rule=str(result.get("matched_rule", "")),
        destructive=bool(result.get("destructive")),
        service=result.get("service"),
        severity=result.get("severity"),
        recommendation=(result.get("input") or {}).get("recommendation") or "",
        thread_id=thread_id,
        evaluated_by=evaluated_by,
        source=source,
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
    return _evaluation_to_dict(row)


def list_evaluations(*, limit: int = 100, verdict: str | None = None) -> list[dict[str, Any]]:
    ensure_tables()
    with SessionLocal() as session:
        stmt = select(OpaEvaluation).order_by(OpaEvaluation.evaluated_at.desc()).limit(limit)
        if verdict == "allow":
            stmt = stmt.where(OpaEvaluation.allowed.is_(True))
        elif verdict == "deny":
            stmt = stmt.where(OpaEvaluation.allowed.is_(False))
        rows = session.scalars(stmt).all()
    return [_evaluation_to_dict(row) for row in rows]


def get_evaluation_stats() -> dict[str, Any]:
    ensure_tables()
    since = utcnow() - timedelta(hours=24)
    with SessionLocal() as session:
        total = session.scalar(select(func.count()).select_from(OpaEvaluation)) or 0
        allowed = session.scalar(
            select(func.count()).select_from(OpaEvaluation).where(OpaEvaluation.allowed.is_(True))
        ) or 0
        denied = session.scalar(
            select(func.count()).select_from(OpaEvaluation).where(OpaEvaluation.allowed.is_(False))
        ) or 0
        last_24h = session.scalar(
            select(func.count()).select_from(OpaEvaluation).where(OpaEvaluation.evaluated_at >= since)
        ) or 0
        last_eval = session.scalar(
            select(OpaEvaluation).order_by(OpaEvaluation.evaluated_at.desc()).limit(1)
        )
        revisions = session.scalar(select(func.count()).select_from(OpaPolicyRevision)) or 0
    return {
        "total": total,
        "allowed": allowed,
        "denied": denied,
        "last_24h": last_24h,
        "policy_revisions": revisions,
        "last_evaluation": _evaluation_to_dict(last_eval) if last_eval else None,
    }


def parse_destructive_keywords(rego: str) -> list[str]:
    match = re.search(r"destructive_keywords\s*:=\s*\{([^}]+)\}", rego, re.DOTALL)
    if not match:
        return list(DESTRUCTIVE_KEYWORDS)
    return re.findall(r'"([^"]+)"', match.group(1)) or list(DESTRUCTIVE_KEYWORDS)


def compile_policy_rego(rego: str) -> tuple[bool, str]:
    opa_url = os.getenv("OPA_URL", "").rstrip("/")
    if not opa_url:
        return True, "opa_disabled"
    payload = {
        "query": "data.agentops.allow",
        "input": {"service": "test", "severity": "P1", "recommendation": "restart pods"},
        "unknowns": ["input"],
        "modules": {"policy.rego": rego},
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{opa_url}/v1/compile", json=payload)
            if response.status_code >= 400:
                detail = response.text
                try:
                    detail = response.json().get("message", detail)
                except Exception:
                    pass
                return False, detail
            return True, "compile_ok"
    except Exception as exc:
        return False, str(exc)


def reload_opa_policy(rego: str) -> tuple[bool, str]:
    opa_url = os.getenv("OPA_URL", "").rstrip("/")
    if not opa_url:
        return True, "opa_disabled"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.put(
                f"{opa_url}/v1/policies/agentops",
                content=rego.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
            if response.status_code >= 400:
                return False, response.text
            probe = client.post(
                f"{opa_url}/v1/data/agentops/allow",
                json={"input": {"service": "probe", "severity": "P3", "recommendation": "restart"}},
            )
            probe.raise_for_status()
            return True, "reloaded"
    except Exception as exc:
        return False, str(exc)


def save_policy_rego(*, rego: str, saved_by: str, note: str | None = None) -> dict[str, Any]:
    ok, detail = compile_policy_rego(rego)
    if not ok:
        raise ValueError(f"Policy compile failed: {detail}")

    path = policy_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rego, encoding="utf-8")

    reloaded, reload_detail = reload_opa_policy(rego)
    if not reloaded:
        raise RuntimeError(f"Policy saved to disk but OPA reload failed: {reload_detail}")

    ensure_tables()
    revision = OpaPolicyRevision(
        id=str(uuid.uuid4()),
        saved_at=utcnow(),
        saved_by=saved_by,
        rego=rego,
        note=note,
    )
    with SessionLocal() as session:
        session.add(revision)
        session.commit()

    return {
        "saved": True,
        "path": str(path),
        "saved_by": saved_by,
        "saved_at": revision.saved_at.isoformat(),
        "revision_id": revision.id,
        "destructive_keywords": parse_destructive_keywords(rego),
    }


def list_policy_revisions(*, limit: int = 20) -> list[dict[str, Any]]:
    ensure_tables()
    with SessionLocal() as session:
        rows = session.scalars(
            select(OpaPolicyRevision).order_by(OpaPolicyRevision.saved_at.desc()).limit(limit)
        ).all()
    return [
        {
            "id": row.id,
            "saved_at": row.saved_at.isoformat(),
            "saved_by": row.saved_by,
            "note": row.note,
            "rego_preview": row.rego[:240] + ("…" if len(row.rego) > 240 else ""),
        }
        for row in rows
    ]


def _evaluation_to_dict(row: OpaEvaluation) -> dict[str, Any]:
    return {
        "id": row.id,
        "evaluated_at": row.evaluated_at.isoformat(),
        "allowed": row.allowed,
        "reason": row.reason,
        "matched_rule": row.matched_rule,
        "destructive": row.destructive,
        "service": row.service,
        "severity": row.severity,
        "recommendation": row.recommendation,
        "thread_id": row.thread_id,
        "evaluated_by": row.evaluated_by,
        "source": row.source,
    }
