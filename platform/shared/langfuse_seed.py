"""Push a walkthrough trace into the Langfuse project for a design."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from shared.design_stack import langfuse_host, langfuse_keys, langfuse_public_url, normalize_design_id


def seed_walkthrough_trace(
    *,
    design_id: str,
    alert_name: str,
    service: str,
    severity: str,
    runbook_id: str,
) -> dict[str, Any] | None:
    pk, sk = langfuse_keys(design_id)
    if not pk or not sk:
        return None
    did = normalize_design_id(design_id)
    now = datetime.now(timezone.utc)
    trace_id = uuid.uuid4().hex
    batch: list[dict[str, Any]] = [
        {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": now.isoformat().replace("+00:00", "Z"),
            "body": {
                "id": trace_id,
                "name": f"ops-triage-walkthrough-{did}",
                "userId": "operator@agentops.local",
                "sessionId": f"walkthrough-{did}-{service}",
                "metadata": {
                    "design": did,
                    "alert_name": alert_name,
                    "service": service,
                    "severity": severity,
                    "runbook_id": runbook_id,
                    "source": "observability-walkthrough",
                },
                "tags": [did, "walkthrough", service, severity],
                "input": {"alert_name": alert_name, "service": service, "severity": severity},
                "output": {"runbook_id": runbook_id, "status": "walkthrough"},
            },
        }
    ]
    steps = [
        ("classify", "Classify alert"),
        ("retrieve_runbook", "RAG runbook retrieval"),
        ("query_logs", "Query logs"),
        ("query_metrics", "Query metrics"),
        ("recommend", "Recommend remediation"),
        ("hitl_gate", "HITL gate"),
    ]
    for i, (node, title) in enumerate(steps):
        start = now + timedelta(milliseconds=80 * i)
        end = start + timedelta(milliseconds=60)
        span_id = uuid.uuid4().hex[:16]
        batch.append(
            {
                "id": str(uuid.uuid4()),
                "type": "span-create",
                "timestamp": start.isoformat().replace("+00:00", "Z"),
                "body": {
                    "id": span_id,
                    "traceId": trace_id,
                    "name": f"{node} · {title}",
                    "startTime": start.isoformat().replace("+00:00", "Z"),
                    "endTime": end.isoformat().replace("+00:00", "Z"),
                    "metadata": {"design": did, "node": node},
                    "input": {"service": service},
                    "output": {"ok": True},
                },
            }
        )
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.post(
                f"{langfuse_host()}/api/public/ingestion",
                json={"batch": batch},
                auth=(pk, sk),
            )
            r.raise_for_status()
        return {
            "trace_id": trace_id,
            "url": f"{langfuse_public_url()}/trace/{trace_id}",
            "design": did,
        }
    except Exception:
        return None
