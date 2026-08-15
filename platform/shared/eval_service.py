"""Run golden-set evals on demand from the platform or GitHub eval-gate."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.eval_store import get_latest_eval_run, list_eval_runs, save_eval_run

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "agent" / "evals" / "golden_alerts.json"


def load_golden_cases() -> list[dict[str, Any]]:
    if not GOLDEN_PATH.is_file():
        return []
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def run_eval_suite(*, triggered_by: str | None = None, source: str = "platform") -> dict[str, Any]:
    """Execute golden_alerts.json against the agent graph; persist + score."""
    started = datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())
    try:
        from evals.run_evals import run_evals

        report = run_evals(session_prefix=run_id)
        report["run_id"] = run_id
        _log_mlflow(report, run_id)
        _push_langfuse_eval_scores(report, run_id)
        saved = save_eval_run(
            report=report,
            triggered_by=triggered_by,
            source=source,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
        )
        _record_eval_gate(saved, triggered_by=triggered_by, source=source)
        return saved
    except Exception as exc:
        fail_report = {
            "passed": False,
            "case_count": 0,
            "averages": {},
            "thresholds": {},
            "cases": [],
            "run_id": run_id,
        }
        saved = save_eval_run(
            report=fail_report,
            triggered_by=triggered_by,
            source=source,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            error_message=str(exc),
        )
        saved["error"] = str(exc)
        _record_eval_gate(saved, triggered_by=triggered_by, source=source)
        return saved


def get_eval_dashboard() -> dict[str, Any]:
    golden = load_golden_cases()
    latest = get_latest_eval_run()
    history = list_eval_runs(limit=10)
    return {
        "golden_count": len(golden),
        "golden_cases": [
            {
                "id": c.get("id"),
                "service": c.get("alert", {}).get("service"),
                "severity": c.get("alert", {}).get("severity"),
                "expected_runbook_id": c.get("expected_runbook_id"),
                "expects_hitl": c.get("expects_hitl", False),
            }
            for c in golden
        ],
        "latest": latest,
        "history": [
            {
                "id": h["id"],
                "passed": h["passed"],
                "case_count": h["case_count"],
                "cases_passed": h.get("cases_passed"),
                "started_at": h["started_at"],
                "triggered_by": h["triggered_by"],
                "averages": h.get("averages") or {},
            }
            for h in history
        ],
        "ci_cd_note": "On-demand here, and as the required GitHub check eval-gate / golden-set. See Governance → GitHub setup (YOUR_GITHUB_ORG / YOUR_GITHUB_REPO until wired).",
    }


def _record_eval_gate(saved: dict[str, Any], *, triggered_by: str | None, source: str) -> None:
    try:
        from shared.governance import record_pipeline_run

        passed = bool(saved.get("passed"))
        cases = saved.get("case_count") or 0
        ok = saved.get("cases_passed") or 0
        record_pipeline_run(
            workflow="eval-gate",
            check_name="eval-gate / golden-set",
            conclusion="success" if passed else "failure",
            triggered_by=triggered_by or "platform",
            source=source,
            summary=f"{ok}/{cases} golden cases · {'pass' if passed else 'fail'}",
            details={"eval_run_id": saved.get("id"), "averages": saved.get("averages") or {}},
        )
    except Exception:
        pass


def _log_mlflow(report: dict[str, Any], run_id: str) -> None:
    if not os.getenv("MLFLOW_TRACKING_URI"):
        return
    try:
        import mlflow

        mlflow.set_experiment(os.getenv("MLFLOW_EVAL_EXPERIMENT", "ops-triage-eval-gate"))
        with mlflow.start_run(run_name=f"eval-{run_id[:8]}"):
            for key, value in (report.get("averages") or {}).items():
                mlflow.log_metric(key, float(value))
            mlflow.log_metric("eval_gate_pass", 1.0 if report.get("passed") else 0.0)
            mlflow.log_param("case_count", report.get("case_count", 0))
    except Exception:
        pass


def _push_langfuse_eval_scores(report: dict[str, Any], run_id: str) -> None:
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return
    try:
        import base64

        import httpx
        from langfuse import Langfuse

        lf = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
        )
        trace = lf.trace(name="eval-suite-run", session_id=f"eval-{run_id}")
        averages = report.get("averages") or {}
        scores = [
            ("eval_rag_recall", averages.get("rag_recall_at_3", 0), "RAG recall@3 average"),
            ("eval_groundedness", averages.get("groundedness", 0), "Groundedness average"),
            ("eval_correctness", averages.get("correctness", 0), "Runbook correctness average"),
            ("eval_tool_accuracy", averages.get("tool_call_accuracy", 0), "Tool/HITL accuracy"),
            ("eval_p95_latency_ms", averages.get("p95_latency_ms", 0), "P95 latency ms"),
            ("eval_gate_pass", 1 if report.get("passed") else 0, "Eval gate pass/fail"),
        ]
        for name, value, comment in scores:
            trace.score(name=name, value=float(value), comment=comment)
        lf.flush()
    except Exception:
        pass
