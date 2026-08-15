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


def run_eval_suite(*, triggered_by: str | None = None, source: str = "platform", design_id: str | None = None) -> dict[str, Any]:
    """Execute golden_alerts.json against the agent graph; persist + publish to this design's eval tool."""
    from shared.design_stack import get_stack, normalize_design_id

    did = normalize_design_id(design_id)
    stack = get_stack(did)
    started = datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())
    try:
        from evals.run_evals import run_evals

        report = run_evals(session_prefix=run_id)
        report["run_id"] = run_id
        report["design_id"] = did
        from shared.eval_backends import publish_eval

        report["publish"] = publish_eval(report, design_id=did, run_id=run_id)
        saved = save_eval_run(
            report=report,
            triggered_by=triggered_by,
            source=source,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
        )
        saved["design_id"] = did
        saved["eval_backend"] = stack.get("eval_backend")
        saved["publish"] = report.get("publish")
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


def get_eval_dashboard(*, design_id: str | None = None) -> dict[str, Any]:
    from shared.design_stack import get_stack, langfuse_public_url, normalize_design_id

    did = normalize_design_id(design_id)
    stack = get_stack(did)
    backend = stack.get("eval_backend") or "langfuse"
    golden = load_golden_cases()
    latest = get_latest_eval_run()
    history = list_eval_runs(limit=10)
    guide = {
        "langfuse": {
            "tool": "Langfuse",
            "url": langfuse_public_url(),
            "where": "Left nav: Tracing · Playground · Prompts · Datasets · Evaluation (LLM-as-judge). After Eval Suite: Datasets → ops-triage-golden. Settings → LLM connection → Ollama llama3.2 for Playground and judges.",
            "login": "a@ex.com / 123456789 · project Design 1 Ops Triage",
        },
        "phoenix": {
            "tool": "Arize Phoenix",
            "url": os.getenv("PHOENIX_PUBLIC_URL", "http://localhost:6006"),
            "where": "Datasets / Experiments · Evaluations → llm_judge_groundedness · Traces",
            "login": "No login · http://localhost:6006",
        },
        "mlflow": {
            "tool": "MLflow",
            "url": os.getenv("MLFLOW_PUBLIC_URL", "http://localhost:5001"),
            "where": "Experiments → ops-triage-d3 · run eval-* · artifacts eval_report.json + llm_judge.md · Traces for llm-as-judge spans",
            "login": "No login · http://localhost:5001",
        },
    }.get(backend, {})
    return {
        "design_id": did,
        "eval_backend": backend,
        "eval_tool": stack.get("llmops"),
        "eval_guide": guide,
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
