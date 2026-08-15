"""Publish golden-set evals to the design's LLM-ops tool — one tool in depth.

D1 → Langfuse datasets + dataset runs + LLM-as-judge scores
D2 → Phoenix datasets / evaluations
D3 → MLflow experiments + traces + artifacts
"""

from __future__ import annotations

import json
import os
from typing import Any

from shared.design_stack import get_stack, langfuse_host, langfuse_keys, langfuse_public_url, normalize_design_id

DATASET_NAME = "ops-triage-golden"


def publish_eval(report: dict[str, Any], *, design_id: str | None, run_id: str) -> dict[str, Any]:
    did = normalize_design_id(design_id)
    backend = get_stack(did).get("eval_backend") or {"d1": "langfuse", "d2": "phoenix", "d3": "mlflow"}.get(did, "langfuse")
    if backend == "phoenix":
        return {"backend": "phoenix", **_publish_phoenix(report, run_id=run_id)}
    if backend == "mlflow":
        return {"backend": "mlflow", **_publish_mlflow(report, run_id=run_id, design_id=did)}
    return {"backend": "langfuse", **_publish_langfuse(report, run_id=run_id, design_id=did)}


def _publish_langfuse(report: dict[str, Any], *, run_id: str, design_id: str) -> dict[str, Any]:
    pk, sk = langfuse_keys(design_id)
    if not pk or not sk:
        return {"ok": False, "error": "Langfuse keys missing for this design"}
    try:
        import httpx
        from langfuse import Langfuse
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    host = langfuse_host()
    public = langfuse_public_url()
    run_name = f"eval-{run_id[:8]}"
    auth = (pk, sk)
    out: dict[str, Any] = {
        "ok": True,
        "run_name": run_name,
        "dataset": DATASET_NAME,
        "url": public,
        "datasets_url": public,
        "scores_url": public,
    }
    try:
        lf = Langfuse(public_key=pk, secret_key=sk, host=host)
        with httpx.Client(timeout=20.0, auth=auth) as client:
            _lf_upsert_dataset(client, host)
            item_ids = _lf_upsert_items(client, host, report.get("cases") or [])
            _lf_ensure_score_configs(client, host)
        for case in report.get("cases") or []:
            trace = lf.trace(
                name=f"eval:{case.get('id')}",
                session_id=case.get("session_id") or f"eval-{run_id}",
                input=case.get("error_summary") or case.get("id"),
                output={
                    "runbook_id": case.get("actual_runbook_id"),
                    "recommendation": case.get("recommendation_preview"),
                    "passed": case.get("passed"),
                },
                metadata={"design": design_id, "eval_run": run_name, "case_id": case.get("id")},
            )
            metrics = case.get("metrics") or {}
            for name, value in (
                ("rag_recall_at_3", metrics.get("rag_recall_at_3")),
                ("groundedness", metrics.get("groundedness")),
                ("correctness", metrics.get("correctness")),
                ("tool_call_accuracy", metrics.get("tool_call_accuracy")),
                ("llm_judge_groundedness", metrics.get("llm_judge_groundedness")),
            ):
                if value is None:
                    continue
                trace.score(
                    name=name,
                    value=float(value),
                    comment=case.get("llm_judge_reason") if name.startswith("llm_judge") else None,
                )
            judge = case.get("llm_judge") or {}
            gen_kwargs = dict(
                name="llm-as-judge",
                model=os.getenv("LLM_MODEL", "llama3.2"),
                input={
                    "task": "groundedness",
                    "expected_runbook_id": case.get("expected_runbook_id"),
                    "actual_runbook_id": case.get("actual_runbook_id"),
                },
                output={"score": judge.get("score"), "reason": judge.get("reason") or case.get("llm_judge_reason")},
                metadata={"evaluator": "llm-as-judge", "design": design_id},
            )
            try:
                trace.generation(**gen_kwargs)
            except Exception:
                try:
                    lf.generation(trace_id=getattr(trace, "id", None), **gen_kwargs)
                except Exception:
                    pass
            item_id = item_ids.get(case.get("id"))
            trace_id = getattr(trace, "id", None) or getattr(trace, "trace_id", None)
            if item_id and trace_id:
                try:
                    with httpx.Client(timeout=20.0, auth=auth) as client:
                        client.post(
                            f"{host}/api/public/dataset-run-items",
                            json={
                                "runName": run_name,
                                "runDescription": "Design 1 golden-set eval · LLM-as-judge",
                                "metadata": {"design": design_id, "passed": bool(report.get("passed"))},
                                "datasetItemId": item_id,
                                "traceId": trace_id,
                            },
                        )
                except Exception:
                    pass
        averages = report.get("averages") or {}
        summary = lf.trace(name="eval-suite-run", session_id=f"eval-{run_id}", metadata={"design": design_id})
        summary.score(name="eval_gate_pass", value=1.0 if report.get("passed") else 0.0)
        for key, value in averages.items():
            try:
                summary.score(name=f"eval_{key}", value=float(value))
            except Exception:
                pass
        lf.flush()
    except Exception as exc:
        out["ok"] = False
        out["error"] = str(exc)
    return out


def _lf_upsert_dataset(client: Any, host: str) -> None:
    r = client.post(
        f"{host}/api/public/datasets",
        json={
            "name": DATASET_NAME,
            "description": "Golden alerts for RAG recall, correctness, and LLM-as-judge groundedness",
            "metadata": {"suite": "ops-triage"},
        },
    )
    if r.status_code not in (200, 201, 409):
        r.raise_for_status()


def _lf_upsert_items(client: Any, host: str, cases: list[dict[str, Any]]) -> dict[str, str]:
    ids: dict[str, str] = {}
    existing: dict[str, str] = {}
    listed = client.get(f"{host}/api/public/dataset-items", params={"datasetName": DATASET_NAME, "limit": 100})
    if listed.status_code == 200:
        for item in listed.json().get("data") or []:
            meta = item.get("metadata") or {}
            case_id = meta.get("case_id") or item.get("id")
            if case_id and item.get("id"):
                existing[str(case_id)] = item["id"]
    for case in cases:
        case_id = case.get("id")
        if not case_id:
            continue
        payload = {
            "datasetName": DATASET_NAME,
            "input": {
                "service": case.get("service"),
                "severity": case.get("severity"),
                "error_summary": case.get("error_summary"),
            },
            "expectedOutput": {"runbook_id": case.get("expected_runbook_id")},
            "metadata": {"case_id": case_id},
        }
        if case_id in existing:
            ids[case_id] = existing[case_id]
            continue
        created = client.post(f"{host}/api/public/dataset-items", json=payload)
        if created.status_code in (200, 201):
            body = created.json()
            ids[case_id] = body.get("id") or existing.get(case_id) or case_id
        else:
            ids[case_id] = existing.get(case_id) or case_id
    return ids


def _lf_ensure_score_configs(client: Any, host: str) -> None:
    configs = [
        ("llm_judge_groundedness", "LLM-as-judge groundedness (0-1)"),
        ("rag_recall_at_3", "Expected runbook in top-3 RAG hits"),
        ("correctness", "Actual runbook_id matches expected"),
        ("groundedness", "Keyword overlap with runbook"),
        ("eval_gate_pass", "Golden-set eval gate pass/fail"),
    ]
    for name, description in configs:
        try:
            client.post(
                f"{host}/api/public/score-configs",
                json={"name": name, "dataType": "NUMERIC", "minValue": 0, "maxValue": 1, "description": description},
            )
        except Exception:
            pass


def _publish_phoenix(report: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    base = (os.getenv("PHOENIX_URL") or "http://phoenix:6006").rstrip("/")
    public = (os.getenv("PHOENIX_PUBLIC_URL") or "http://localhost:6006").rstrip("/")
    out: dict[str, Any] = {"ok": False, "url": public, "dataset": DATASET_NAME, "run_name": f"eval-{run_id[:8]}"}
    try:
        import httpx

        examples = []
        for case in report.get("cases") or []:
            examples.append(
                {
                    "input": {
                        "service": case.get("service"),
                        "severity": case.get("severity"),
                        "error_summary": case.get("error_summary"),
                    },
                    "output": {
                        "runbook_id": case.get("actual_runbook_id"),
                        "passed": case.get("passed"),
                    },
                    "metadata": {
                        "case_id": case.get("id"),
                        "expected_runbook_id": case.get("expected_runbook_id"),
                        "llm_judge": (case.get("metrics") or {}).get("llm_judge_groundedness"),
                        "llm_judge_reason": case.get("llm_judge_reason"),
                    },
                }
            )
        with httpx.Client(timeout=20.0) as client:
            created = client.post(
                f"{base}/v1/datasets",
                json={"name": DATASET_NAME, "description": "Design 2 golden-set · Phoenix experiments + LLM-as-judge"},
            )
            dataset_id = None
            if created.status_code in (200, 201):
                body = created.json() if created.content else {}
                if isinstance(body, dict):
                    data = body.get("data")
                    dataset_id = (data.get("id") if isinstance(data, dict) else None) or body.get("id")
            if not dataset_id:
                listed = client.get(f"{base}/v1/datasets")
                rows = listed.json().get("data") or listed.json().get("datasets") or []
                if isinstance(rows, list):
                    for row in rows:
                        name = (row.get("name") if isinstance(row, dict) else None) or (row.get("data") or {}).get("name")
                        if name == DATASET_NAME:
                            dataset_id = row.get("id") or (row.get("data") or {}).get("id")
            if dataset_id and examples:
                client.post(
                    f"{base}/v1/datasets/{dataset_id}/examples",
                    json={
                        "inputs": [e["input"] for e in examples],
                        "outputs": [e["output"] for e in examples],
                        "metadata": [e["metadata"] for e in examples],
                    },
                )
            eval_payload = {
                "eval_name": "llm_judge_groundedness",
                "records": [
                    {
                        "span_id": case.get("id"),
                        "score": (case.get("metrics") or {}).get("llm_judge_groundedness") or 0,
                        "label": "grounded" if ((case.get("metrics") or {}).get("llm_judge_groundedness") or 0) >= 0.7 else "ungrounded",
                        "explanation": case.get("llm_judge_reason") or "",
                    }
                    for case in report.get("cases") or []
                ],
            }
            ev = client.post(f"{base}/v1/evaluations", json=eval_payload)
            out["evaluations_status"] = ev.status_code
        out["ok"] = True
        out["dataset_id"] = dataset_id
    except Exception as exc:
        out["error"] = str(exc)
    return out


def _publish_mlflow(report: dict[str, Any], *, run_id: str, design_id: str) -> dict[str, Any]:
    if not os.getenv("MLFLOW_TRACKING_URI"):
        return {"ok": False, "error": "MLFLOW_TRACKING_URI not set"}
    public = os.getenv("MLFLOW_PUBLIC_URL", "http://localhost:5001").rstrip("/")
    out: dict[str, Any] = {
        "ok": False,
        "url": public,
        "experiment": os.getenv("MLFLOW_EVAL_EXPERIMENT", "ops-triage-d3"),
        "run_name": f"eval-{run_id[:8]}",
    }
    try:
        import mlflow

        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
        mlflow.set_experiment(out["experiment"])
        with mlflow.start_run(run_name=out["run_name"]):
            mlflow.set_tags(
                {
                    "design": design_id,
                    "eval_type": "golden-set",
                    "llm_as_judge": "true",
                    "suite": DATASET_NAME,
                }
            )
            mlflow.log_param("case_count", report.get("case_count", 0))
            mlflow.log_param("cases_passed", report.get("cases_passed", 0))
            mlflow.log_metric("eval_gate_pass", 1.0 if report.get("passed") else 0.0)
            for key, value in (report.get("averages") or {}).items():
                try:
                    mlflow.log_metric(key, float(value))
                except Exception:
                    pass
            rows = []
            for case in report.get("cases") or []:
                metrics = case.get("metrics") or {}
                rows.append(
                    {
                        "id": case.get("id"),
                        "expected": case.get("expected_runbook_id"),
                        "actual": case.get("actual_runbook_id"),
                        "passed": case.get("passed"),
                        "llm_judge": metrics.get("llm_judge_groundedness"),
                        "reason": case.get("llm_judge_reason"),
                    }
                )
                try:
                    with mlflow.start_span(name=f"eval:{case.get('id')}") as span:
                        span.set_inputs({"case": case.get("id"), "service": case.get("service")})
                        span.set_outputs({"runbook_id": case.get("actual_runbook_id"), "passed": case.get("passed")})
                    with mlflow.start_span(name="llm-as-judge") as span:
                        span.set_inputs({"expected": case.get("expected_runbook_id"), "actual": case.get("actual_runbook_id")})
                        span.set_outputs({"score": metrics.get("llm_judge_groundedness"), "reason": case.get("llm_judge_reason")})
                except Exception:
                    pass
            mlflow.log_dict({"cases": rows, "averages": report.get("averages")}, "eval_report.json")
            md = ["# LLM-as-judge", ""]
            for row in rows:
                md.append(f"- `{row['id']}` score={row['llm_judge']} — {row['reason'] or ''}")
            mlflow.log_text("\n".join(md), "llm_judge.md")
        out["ok"] = True
    except Exception as exc:
        out["error"] = str(exc)
    return out
