"""Evaluation runner — golden set against agent graph (platform or CI/CD)."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

from agent.graph import get_graph
from agent.tools.runbook_rag import retrieve_runbooks
from evals.llm_judge import judge_recommendation
from observability.setup import build_invoke_config, flush_langfuse

EVALS_DIR = Path(__file__).parent
GOLDEN_FILE = EVALS_DIR / "golden_alerts.json"

THRESHOLDS = {
    "tool_call_accuracy": 0.90,
    "rag_recall_at_3": 0.85,
    "groundedness": 0.80,
    "correctness": 0.85,
    "p95_latency_ms": 8000.0,
}


def load_golden() -> list[dict]:
    return json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))


def eval_rag_recall(case: dict) -> float:
    alert = case["alert"]
    expected = case.get("expected_runbook_id")
    if not expected:
        return 1.0
    query = f"{alert['service']} {alert.get('error_summary', '')}"
    chunks = retrieve_runbooks(query, service=alert.get("service"), top_k=3)
    ids = [c["runbook_id"] for c in chunks]
    return 1.0 if expected in ids else 0.0


def eval_groundedness(case: dict, result: dict) -> float:
    rec = result.get("recommendation", "").lower()
    chunks = result.get("runbook_chunks") or []
    if not chunks:
        return 0.0
    keywords = case.get("grounded_keywords", [])
    if keywords:
        return 1.0 if any(k.lower() in rec for k in keywords) else 0.5
    return 1.0 if case.get("expected_runbook_id") == result.get("runbook_id") else 0.5


def eval_tool_accuracy(case: dict, result: dict) -> float:
    if case.get("expects_ticket") and result.get("ticket", {}).get("ticket_id"):
        return 1.0
    if case.get("expects_hitl") and result.get("requires_hitl"):
        return 1.0
    if not case.get("expects_hitl") and not case.get("expects_ticket"):
        return 1.0
    return 0.0


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx]


def _case_passed(case: dict, metrics: dict[str, float]) -> bool:
    return (
        metrics["rag_recall_at_3"] >= 1.0
        and metrics["correctness"] >= 1.0
        and metrics["groundedness"] >= 0.5
        and metrics["tool_call_accuracy"] >= 1.0
    )


def run_evals(*, session_prefix: str | None = None) -> dict:
    # CI / local golden-set has no Prometheus or Loki. Production compose sets URLs.
    if os.getenv("MOCK_LLM", "").lower() == "true":
        os.environ.setdefault("LOG_QUERY_BACKEND", "fixture")
        os.environ.setdefault("METRICS_QUERY_BACKEND", "fixture")

    graph = get_graph()
    cases = load_golden()
    scores = {
        "rag_recall_at_3": [],
        "groundedness": [],
        "tool_call_accuracy": [],
        "correctness": [],
        "llm_judge_groundedness": [],
        "latency_ms": [],
    }
    case_results: list[dict] = []

    for case in cases:
        alert = case["alert"]
        case_id = case.get("id") or str(uuid.uuid4())
        session_id = f"{session_prefix or 'eval'}-{case_id}"
        config = build_invoke_config("eval-suite-run", session_id=session_id)
        t0 = time.perf_counter()
        out = graph.invoke({"alert": alert}, config=config)
        latency_ms = (time.perf_counter() - t0) * 1000

        rag = eval_rag_recall(case)
        grounded = eval_groundedness(case, out)
        tool_acc = eval_tool_accuracy(case, out)
        correct = (
            1.0
            if out.get("runbook_id") == case.get("expected_runbook_id") or case.get("expected_runbook_id") is None
            else 0.0
        )
        try:
            judge = judge_recommendation(
                alert=alert,
                recommendation=out.get("recommendation") or "",
                expected_runbook_id=case.get("expected_runbook_id"),
                actual_runbook_id=out.get("runbook_id"),
                grounded_keywords=case.get("grounded_keywords") or [],
            )
        except Exception:
            judge = {"score": 0.5, "reason": "judge unavailable", "raw": ""}

        scores["latency_ms"].append(latency_ms)
        scores["rag_recall_at_3"].append(rag)
        scores["groundedness"].append(grounded)
        scores["tool_call_accuracy"].append(tool_acc)
        scores["correctness"].append(correct)
        scores["llm_judge_groundedness"].append(float(judge.get("score") or 0.5))

        metrics = {
            "rag_recall_at_3": rag,
            "groundedness": grounded,
            "tool_call_accuracy": tool_acc,
            "correctness": correct,
            "llm_judge_groundedness": float(judge.get("score") or 0.5),
            "latency_ms": latency_ms,
        }
        case_results.append(
            {
                "id": case_id,
                "service": alert.get("service"),
                "severity": alert.get("severity"),
                "error_summary": alert.get("error_summary", "")[:120],
                "expected_runbook_id": case.get("expected_runbook_id"),
                "actual_runbook_id": out.get("runbook_id"),
                "requires_hitl": bool(out.get("requires_hitl")),
                "expects_hitl": bool(case.get("expects_hitl")),
                "recommendation_preview": (out.get("recommendation") or "")[:160],
                "metrics": metrics,
                "llm_judge": judge,
                "llm_judge_reason": judge.get("reason"),
                "passed": _case_passed(case, metrics),
                "session_id": session_id,
            }
        )

    flush_langfuse()

    averages = {k: sum(v) / len(v) if v else 0.0 for k, v in scores.items() if k != "latency_ms"}
    p95_latency = _p95(scores["latency_ms"])
    averages["p95_latency_ms"] = p95_latency

    metric_pass = all(averages.get(k, 0) >= THRESHOLDS[k] for k in THRESHOLDS if k != "p95_latency_ms")
    latency_pass = p95_latency <= THRESHOLDS["p95_latency_ms"]
    passed = metric_pass and latency_pass

    return {
        "averages": averages,
        "thresholds": THRESHOLDS,
        "passed": passed,
        "case_count": len(cases),
        "cases_passed": sum(1 for c in case_results if c["passed"]),
        "cases_failed": sum(1 for c in case_results if not c["passed"]),
        "latency_ms_per_case": scores["latency_ms"],
        "cases": case_results,
    }


def main() -> int:
    report = run_evals()
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
