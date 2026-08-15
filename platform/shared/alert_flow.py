"""Alert ingestion flow — catalog, live snapshots, full journey simulation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from shared.design_stack import get_stack, normalize_design_id
from shared.langfuse_seed import seed_walkthrough_trace
from shared.opa_guardrails import build_evaluation_result, is_destructive

try:
    from agent.tools.runbook_rag import assess_runbook_match, unmatched_recommendation
except Exception:  # pragma: no cover — gateway always has agent on path
    assess_runbook_match = None  # type: ignore
    unmatched_recommendation = None  # type: ignore

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "agent" / "sample_data" / "alerts"
METRICS_FILE = Path(__file__).resolve().parents[2] / "agent" / "sample_data" / "metrics" / "services.json"
LOGS_DIR = Path(__file__).resolve().parents[2] / "agent" / "sample_data" / "logs"

SERVICE_TO_RUNBOOK: dict[str, str] = {
    "checkout-service": "checkout-redis-pool",
    "payment-api": "payment-high-cpu",
    "auth-service": "auth-error-spike",
    "order-service": "db-pool-exhausted",
}

ALERT_CATALOG: list[dict[str, Any]] = [
    {
        "id": "checkout-redis-pool",
        "fixture": "checkout-redis-pool.json",
        "alert_name": "CheckoutHighErrorRate",
        "service": "checkout-service",
        "severity": "P1",
        "promql": 'service_error_rate{service="checkout-service"} > 0.05',
        "threshold": 0.05,
        "metric_key": "error_rate_5m",
        "runbook_id": "checkout-redis-pool",
        "summary": "HTTP 500 spike on /checkout",
        "description": "Timeout waiting for connection pool (Redis)",
        "has_live_rule": True,
    },
    {
        "id": "payment-high-cpu",
        "fixture": "payment-high-cpu.json",
        "alert_name": "PaymentHighCPU",
        "service": "payment-api",
        "severity": "P1",
        "promql": 'service_cpu_percent{service="payment-api"} > 90',
        "threshold": 90.0,
        "metric_key": "cpu_percent",
        "runbook_id": "payment-high-cpu",
        "summary": "High CPU usage above 90%",
        "description": "connection timeout retry storm after deploy v2.4.1",
        "has_live_rule": False,
    },
    {
        "id": "auth-error-spike",
        "fixture": "auth-error-spike.json",
        "alert_name": "AuthErrorSpike",
        "service": "auth-service",
        "severity": "P2",
        "promql": 'service_error_rate{service="auth-service"} > 0.05',
        "threshold": 0.05,
        "metric_key": "error_rate_5m",
        "runbook_id": "auth-error-spike",
        "summary": "5xx error rate spike",
        "description": "JWT validation failures increasing",
        "has_live_rule": False,
    },
    {
        "id": "db-pool-exhausted",
        "fixture": "db-pool-exhausted.json",
        "alert_name": "DatabasePoolExhausted",
        "service": "order-service",
        "severity": "P1",
        "promql": 'service_error_rate{service="order-service"} > 0.03',
        "threshold": 0.03,
        "metric_key": "error_rate_5m",
        "runbook_id": "db-pool-exhausted",
        "summary": "Database connection pool exhausted",
        "description": "pool wait time exceeded 2 seconds",
        "has_live_rule": False,
    },
]

PHASE_LABELS = {
    "ingestion": "Phase 1 · Signals",
    "agent": "Phase 2 · Agent pipeline",
    "guardrails": "Phase 3 · OPA guardrails",
    "hitl": "Phase 4 · Human approval",
}


def _prom_url() -> str:
    return (os.getenv("VM_URL") or os.getenv("PROMETHEUS_URL") or "http://victoriametrics:8428").rstrip("/")


def _loki_url() -> str:
    return os.getenv("LOKI_URL", "http://loki:3100").rstrip("/")


def _es_url() -> str:
    return os.getenv("ELASTICSEARCH_URL", "").rstrip("/")


def _opensearch_url() -> str:
    return (os.getenv("OPENSEARCH_URL") or "").rstrip("/")


def _alert_receiver_url() -> str:
    return os.getenv("ALERT_RECEIVER_URL", "http://alert-receiver:8090").rstrip("/")


def _ingestion_url() -> str:
    return os.getenv("INGESTION_URL", "http://runbook-ingestion:8092").rstrip("/")


def _ingestion_headers() -> dict[str, str]:
    token = os.getenv("INGESTION_API_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _load_fixture(fixture: str) -> dict[str, Any]:
    path = FIXTURES_DIR / fixture
    if not path.is_file():
        raise FileNotFoundError(f"Alert fixture not found: {fixture}")
    return json.loads(path.read_text(encoding="utf-8"))


def _fixture_metrics(service: str) -> dict[str, Any]:
    if METRICS_FILE.is_file():
        data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
        if service in data:
            return {"service": service, **data[service]}
    return {"service": service, "cpu_percent": 0.0, "error_rate_5m": 0.0, "p95_latency_ms": 0.0, "active_incidents": 0}


def _query_prometheus(promql: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.get(f"{_prom_url()}/api/v1/query", params={"query": promql})
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        return {"status": "error", "error": str(exc), "data": {"result": []}}


def _prometheus_alerts() -> list[dict[str, Any]]:
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.get(f"{_prom_url()}/api/v1/alerts")
            r.raise_for_status()
            return r.json().get("data", {}).get("alerts") or []
    except Exception:
        return []


def _loki_logs(service: str, limit: int = 8) -> list[dict[str, Any]]:
    log_path = LOGS_DIR / f"{service}.jsonl"
    rows: list[dict[str, Any]] = []
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if rows:
        return rows[:limit]
    for base, index in (
        (_es_url(), os.getenv("ELASTICSEARCH_INDEX", "agentops-logs")),
        (_opensearch_url(), os.getenv("OPENSEARCH_LOGS_INDEX", "agentops-d3-logs")),
    ):
        if not base:
            continue
        try:
            body = {
                "query": {"bool": {"must": [{"match": {"service": service}}]}},
                "size": limit,
                "sort": [
                    {"timestamp": {"order": "desc", "unmapped_type": "date"}},
                    {"@timestamp": {"order": "desc", "unmapped_type": "date"}},
                ],
            }
            with httpx.Client(timeout=10.0) as client:
                r = client.post(f"{base}/{index}/_search", json=body)
                r.raise_for_status()
                for hit in (((r.json().get("hits") or {}).get("hits")) or []):
                    src = hit.get("_source") or {}
                    rows.append(
                        {
                            "timestamp": src.get("timestamp") or src.get("@timestamp"),
                            "level": src.get("level", "INFO"),
                            "service": src.get("service", service),
                            "message": src.get("message") or "",
                        }
                    )
            if rows:
                return rows[:limit]
        except Exception:
            pass
    try:
        query = f'{{job="agentops"}} |= "{service}"'
        url = f"{_loki_url()}/loki/api/v1/query_range"
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, params={"query": query, "limit": limit, "direction": "BACKWARD"})
            r.raise_for_status()
            data = r.json()
        for stream in data.get("data", {}).get("result", []):
            for _ts, line in stream.get("values", []):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    rows.append({"message": line, "service": service, "level": "INFO"})
                if len(rows) >= limit:
                    return rows
    except Exception:
        pass
    return rows[:limit]


def _query_chroma(
    *,
    service: str,
    error_summary: str,
    log_snippet: str = "",
    runbook_id: str | None = None,
) -> dict[str, Any]:
    query = f"{service} {error_summary} {log_snippet}".strip()
    body: dict[str, Any] = {"query": query, "n_results": 3, "service": service}
    if runbook_id and runbook_id not in ("none", "unknown"):
        body["runbook_id"] = runbook_id
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                f"{_ingestion_url()}/v1/ingest/index/query",
                headers=_ingestion_headers(),
                json=body,
            )
            r.raise_for_status()
            data = r.json()
        chunks = data.get("results") or data.get("chunks") or []
        match = (
            assess_runbook_match(chunks, query=query, service=service)
            if assess_runbook_match
            else {"matched": bool(chunks), "runbook_id": (chunks[0].get("runbook_id") if chunks else None), "nearest": None, "similarity": 0}
        )
        selected = match.get("runbook_id") if match.get("matched") else "none"
        return {
            "collection": data.get("collection") or "runbooks",
            "query": query,
            "top_k": 3,
            "chunks": chunks[:3],
            "selected_runbook_id": selected,
            "match": match,
        }
    except Exception as exc:
        return {
            "collection": "runbooks",
            "query": query,
            "top_k": 3,
            "chunks": [],
            "selected_runbook_id": "none",
            "match": {"matched": False, "runbook_id": "none", "reason": "query_error", "nearest": None, "similarity": 0},
            "error": str(exc),
        }


def _build_alertmanager_payload(entry: dict[str, Any], alert_body: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "receiver": "agentops-agent",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": entry["alert_name"],
                    "service": entry["service"],
                    "severity": entry["severity"],
                },
                "annotations": {
                    "summary": entry.get("summary") or alert_body.get("error_summary", ""),
                    "description": entry.get("description") or alert_body.get("log_snippet", ""),
                },
                "startsAt": now,
                "generatorURL": f"{_prom_url()}/graph?g0.expr={entry['promql']}",
            }
        ],
        "commonLabels": {
            "alertname": entry["alert_name"],
            "service": entry["service"],
            "severity": entry["severity"],
        },
        "_derived_agent_payload": alert_body,
    }


def _resolve_entry_and_body(
    *,
    alert_id: str | None,
    custom_alert: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if custom_alert and custom_alert.get("service"):
        service = custom_alert["service"]
        body = {
            "service": service,
            "severity": custom_alert.get("severity", "P2"),
            "error_summary": custom_alert.get("error_summary", "Custom alert"),
            "log_snippet": custom_alert.get("log_snippet", ""),
        }
        runbook_id = custom_alert.get("runbook_id") or "none"
        entry = {
            "id": "custom",
            "fixture": "",
            "alert_name": custom_alert.get("alert_name") or f"CustomAlert_{service.replace('-', '_')}",
            "service": service,
            "severity": body["severity"],
            "promql": f'service_error_rate{{service="{service}"}} > 0.05',
            "threshold": 0.05,
            "metric_key": "error_rate_5m",
            "runbook_id": runbook_id,
            "summary": body["error_summary"],
            "description": body["log_snippet"],
            "has_live_rule": False,
        }
        return entry, body
    if not alert_id:
        raise ValueError("alert_id or custom_alert required")
    entry = next((a for a in ALERT_CATALOG if a["id"] == alert_id), None)
    if not entry:
        raise ValueError(f"Unknown alert_id: {alert_id}")
    return entry, _load_fixture(entry["fixture"])


def _agent_pipeline_steps(
    *,
    entry: dict[str, Any],
    alert_body: dict[str, Any],
    metrics: dict[str, Any],
    logs: list[dict[str, Any]],
    chroma: dict[str, Any],
    agent_response: dict[str, Any] | None,
    stack: dict[str, Any],
) -> list[dict[str, Any]]:
    match = chroma.get("match") or {}
    grounded = bool(match.get("matched"))
    runbook_id = (agent_response or {}).get("runbook_id") or chroma.get("selected_runbook_id") or entry["runbook_id"]
    if (agent_response or {}).get("runbook_gap") or not grounded:
        if not (agent_response or {}).get("runbook_id") or (agent_response or {}).get("runbook_gap"):
            runbook_id = "none"
    if runbook_id in ("unknown", None, ""):
        runbook_id = "none" if not grounded else (entry.get("runbook_id") or "none")
    recommendation = (agent_response or {}).get("recommendation")
    if not recommendation:
        if grounded:
            recommendation = f"Follow runbook `{runbook_id}`: inspect {entry['service']} metrics/logs, apply remediation steps."
        elif unmatched_recommendation:
            recommendation = unmatched_recommendation(alert=alert_body, match=match)
        else:
            recommendation = "No grounded runbook. Investigate logs/metrics, open a ticket, then draft a runbook."
    classification = (agent_response or {}).get("classification") or f"{entry['severity']} · {entry['service']} degradation"
    requires_hitl = (agent_response or {}).get("requires_hitl")
    if requires_hitl is None:
        requires_hitl = entry["severity"] == "P1" or is_destructive(recommendation) or not grounded

    opa_result = build_evaluation_result(
        service=entry["service"],
        recommendation=recommendation,
        severity=entry["severity"],
    )

    chunks = chroma.get("chunks") or (agent_response or {}).get("runbook_chunks") or []

    steps: list[dict[str, Any]] = [
        {
            "id": "agent_classify",
            "phase": "agent",
            "title": "Classify alert",
            "subtitle": "LangGraph · classify node",
            "visual": {
                "type": "pipeline_node",
                "icon": "🎯",
                "summary": classification,
                "badges": [entry["severity"], entry["service"]],
            },
            "payload": {
                "node": "classify",
                "input": alert_body,
                "output": {"classification": classification, "requires_hitl": requires_hitl},
            },
        },
        {
            "id": "agent_chroma",
            "phase": "agent",
            "title": stack["vector_title"],
            "subtitle": f"{stack['vector']} · semantic search",
            "visual": {
                "type": stack.get("vector_visual") or "chroma",
                "collection": chroma.get("collection"),
                "query": chroma.get("query"),
                "selected_runbook_id": runbook_id,
                "match": match,
                "unmatched": not grounded,
                "chunks": [
                    {
                        "runbook_id": c.get("runbook_id"),
                        "score": c.get("score") or c.get("distance"),
                        "similarity": c.get("similarity"),
                        "preview": (c.get("document") or c.get("text") or c.get("preview") or "")[:160],
                        "rejected": (not grounded) and i == 0,
                    }
                    for i, c in enumerate(chunks[:3])
                ],
            },
            "payload": {
                "node": "retrieve_runbook",
                "backend": stack["vector"],
                "query": chroma,
                "runbook_id": runbook_id,
                "match": match,
            },
        },
        {
            "id": "agent_logs",
            "phase": "agent",
            "title": stack["logs_title"],
            "subtitle": "Tool · query_logs",
            "visual": {"type": "logs", "lines": logs[:4]},
            "payload": {"node": "query_logs", "backend": stack["logs_backend"], "results": logs[:4]},
        },
        {
            "id": "agent_metrics",
            "phase": "agent",
            "title": stack["metrics_title"],
            "subtitle": "Tool · query_metrics",
            "visual": {"type": "metrics", "metrics": metrics},
            "payload": {"node": "query_metrics", "backend": stack["metrics_backend"], "results": metrics},
        },
        {
            "id": "agent_recommend",
            "phase": "agent",
            "title": "Recommend remediation",
            "subtitle": "LLM + runbook grounding",
            "visual": {
                "type": "recommendation",
                "runbook_id": runbook_id,
                "text": recommendation[:700],
                "destructive": is_destructive(recommendation),
                "unmatched": not grounded,
                "match": match,
            },
            "payload": {"node": "recommend", "recommendation": recommendation, "runbook_id": runbook_id},
        },
        {
            "id": "opa_evaluate",
            "phase": "guardrails",
            "title": stack["policy_title"],
            "subtitle": stack["policy_sub"],
            "visual": {
                "type": "opa",
                "allowed": opa_result["allowed"],
                "reason": opa_result["reason"],
                "matched_rule": opa_result["matched_rule"],
                "destructive": opa_result["destructive"],
            },
            "payload": {"node": "opa_guardrails", "evaluation": opa_result},
        },
        {
            "id": "hitl_gate",
            "phase": "hitl",
            "title": "Human-in-the-loop gate",
            "subtitle": "Pause before ticket / execute",
            "visual": {
                "type": "hitl",
                "status": "awaiting_hitl" if requires_hitl and opa_result["allowed"] else (
                    "blocked_by_policy" if not opa_result["allowed"] else "auto_approved"
                ),
                "thread_id": (agent_response or {}).get("thread_id"),
                "notify": "Slack webhook + Platform Simulation tab" if requires_hitl else None,
            },
            "payload": {
                "node": "hitl_gate",
                "requires_hitl": requires_hitl,
                "opa_allowed": opa_result["allowed"],
                "status": (agent_response or {}).get("status") or ("awaiting_hitl" if requires_hitl else "completed"),
            },
        },
    ]
    if stack.get("include_tempo_step"):
        steps.insert(
            4,
            {
                "id": "agent_traces",
                "phase": "agent",
                "title": "Query traces · Tempo",
                "subtitle": "OTEL · Grafana Explore · Tempo datasource",
                "visual": {
                    "type": "pipeline_node",
                    "icon": "🧵",
                    "summary": "Distributed traces in Grafana Tempo (not logs)",
                    "badges": [stack["name"], "Explore → Tempo"],
                },
                "payload": {
                    "node": "query_traces",
                    "backend": "tempo",
                    "hint": "Grafana Explore → datasource Tempo → Search. Filter resource.agentops.design=d3",
                },
            },
        )
    return steps


def get_alert_catalog() -> dict[str, Any]:
    firing = _prometheus_alerts()
    firing_names = {a.get("labels", {}).get("alertname") for a in firing if a.get("state") == "firing"}
    items = []
    for entry in ALERT_CATALOG:
        fixture = _load_fixture(entry["fixture"])
        metrics = _fixture_metrics(entry["service"])
        if entry["metric_key"] == "error_rate_5m":
            prom_result = _query_prometheus(f'service_error_rate{{service="{entry["service"]}"}}')
        elif entry["metric_key"] == "cpu_percent":
            prom_result = _query_prometheus(f'service_cpu_percent{{service="{entry["service"]}"}}')
        else:
            prom_result = {"data": {"result": []}}
        value = None
        results = prom_result.get("data", {}).get("result") or []
        if results:
            value = float(results[0]["value"][1])
        items.append(
            {
                **entry,
                "fixture_payload": fixture,
                "metrics": metrics,
                "prometheus_value": value,
                "prometheus_firing": entry["alert_name"] in firing_names,
                "log_preview": _loki_logs(entry["service"], limit=3),
            }
        )
    return {
        "alerts": items,
        "services": list(SERVICE_TO_RUNBOOK.keys()),
        "phases": PHASE_LABELS,
        "prometheus_url": os.getenv("PROMETHEUS_PUBLIC_URL", "http://localhost:9090"),
        "grafana_url": os.getenv("GRAFANA_PUBLIC_URL", "http://localhost:3001"),
        "loki_url": os.getenv("LOKI_PUBLIC_URL", "http://localhost:3100"),
        "alertmanager_url": os.getenv("ALERTMANAGER_PUBLIC_URL", "http://localhost:9093"),
    }


def simulate_alert_flow(
    *,
    alert_id: str | None = None,
    custom_alert: dict[str, Any] | None = None,
    invoke_agent: bool = False,
    design_id: str | None = None,
) -> dict[str, Any]:
    stack = get_stack(design_id)
    did = normalize_design_id(design_id)
    entry, alert_body = _resolve_entry_and_body(alert_id=alert_id, custom_alert=custom_alert)
    metrics = _fixture_metrics(entry["service"])
    logs = _loki_logs(entry["service"], limit=6)
    chroma = _query_chroma(
        service=entry["service"],
        error_summary=alert_body.get("error_summary", ""),
        log_snippet=alert_body.get("log_snippet", ""),
        runbook_id=None if entry.get("id") == "custom" else entry.get("runbook_id"),
    )

    if entry["metric_key"] == "error_rate_5m":
        prom_query = f'service_error_rate{{service="{entry["service"]}"}}'
    else:
        prom_query = f'service_cpu_percent{{service="{entry["service"]}"}}'
    prom_snapshot = _query_prometheus(prom_query)
    prom_value = None
    if prom_snapshot.get("data", {}).get("result"):
        prom_value = float(prom_snapshot["data"]["result"][0]["value"][1])

    ingestion_steps: list[dict[str, Any]] = [
        {
            "id": "metrics_exporter",
            "phase": "ingestion",
            "title": "Metrics Exporter",
            "subtitle": "Fixture gauges → :9100/metrics",
            "visual": {"type": "metrics", "metrics": metrics, "source": "services.json"},
            "payload": {"job": "agentops-services", "target": "metrics-exporter:9100", "metrics": metrics},
        },
        {
            "id": "prometheus",
            "phase": "ingestion",
            "title": stack["metrics_ingest_title"],
            "subtitle": stack["metrics_ingest_sub"],
            "visual": {
                "type": "promql",
                "query": prom_query,
                "value": prom_value,
                "threshold": entry["threshold"],
                "firing": prom_value is not None and prom_value > entry["threshold"],
            },
            "payload": {
                "query": prom_query,
                "query_result": prom_snapshot,
                "rule": {
                    "alert": entry["alert_name"],
                    "expr": entry["promql"],
                    "current_value": prom_value,
                    "threshold": entry["threshold"],
                },
            },
        },
        {
            "id": "alertmanager",
            "phase": "ingestion",
            "title": "Alertmanager",
            "subtitle": "Group · route · webhook",
            "visual": {"type": "webhook", "receiver": "agentops-agent", "status": "firing"},
            "payload": _build_alertmanager_payload(entry, alert_body),
        },
        {
            "id": "alert_receiver",
            "phase": "ingestion",
            "title": "Alert Receiver",
            "subtitle": "Webhook → agent JSON",
            "visual": {"type": "transform", "from": "Alertmanager", "to": "Agent /invoke"},
            "payload": {
                "webhook_url": f"{_alert_receiver_url()}/webhook/alertmanager",
                "derived_agent_alert": alert_body,
            },
        },
        {
            "id": "agent_invoke",
            "phase": "agent",
            "title": "Agent entry · POST /invoke",
            "subtitle": "LangGraph orchestrator starts",
            "visual": {"type": "pipeline_node", "icon": "🤖", "summary": "Pipeline invoked", "badges": [entry["service"]]},
            "payload": {"url": os.getenv("AGENT_URL", "http://agent:8000") + "/invoke", "body": alert_body},
        },
    ]

    agent_response: dict[str, Any] | None = None
    fire_error: str | None = None
    if invoke_agent:
        try:
            invoke_body = {**alert_body, "design_id": did}
            with httpx.Client(timeout=120.0) as client:
                r = client.post(
                    os.getenv("AGENT_URL", "http://agent:8000") + "/invoke",
                    json=invoke_body,
                )
                r.raise_for_status()
                agent_response = r.json()
            ingestion_steps[-1]["response"] = agent_response
            ingestion_steps[-1]["status"] = "completed"
            if agent_response.get("runbook_id") and not agent_response.get("runbook_gap"):
                chroma["selected_runbook_id"] = agent_response["runbook_id"]
        except Exception as exc:
            fire_error = str(exc)
            ingestion_steps[-1]["status"] = "error"
            ingestion_steps[-1]["error"] = fire_error

    pipeline_steps = _agent_pipeline_steps(
        entry=entry,
        alert_body=alert_body,
        metrics=metrics,
        logs=logs,
        chroma=chroma,
        agent_response=agent_response,
        stack=stack,
    )

    all_steps = ingestion_steps + pipeline_steps

    lf = seed_walkthrough_trace(
        design_id=did,
        alert_name=entry["alert_name"],
        service=entry["service"],
        severity=entry["severity"],
        runbook_id=chroma.get("selected_runbook_id") or entry["runbook_id"],
    )

    grafana_url = os.getenv("GRAFANA_PUBLIC_URL", "http://localhost:3001")
    external_views = {
        "prometheus": {
            "title": stack["metrics"],
            "url": os.getenv("PROMETHEUS_PUBLIC_URL", "http://localhost:9090"),
            "query": prom_query,
            "value": prom_value,
            "metrics": metrics,
        },
        "grafana": {
            "title": stack["dashboards"],
            "url": grafana_url,
            "metrics": metrics,
            "hint": (
                "Explore → datasource Mimir for metrics, Tempo for traces. Logs are OpenSearch Dashboards."
                if did == "d3"
                else "Explore the provisioned AgentOps dashboard for this design."
            ),
        },
        "loki": {
            "title": stack["logs"],
            "url": os.getenv("OPENSEARCH_DASHBOARDS_PUBLIC_URL", "http://localhost:5602") if did == "d3"
            else os.getenv("KIBANA_PUBLIC_URL", "http://localhost:5601") if did == "d2"
            else os.getenv("LOKI_PUBLIC_URL", "http://localhost:3100"),
            "query": f'service:{entry["service"]}' if did != "d1" else f'{{job="agentops"}} |= "{entry["service"]}"',
            "logs": logs,
        },
    }

    hitl = next((s for s in pipeline_steps if s["id"] == "hitl_gate"), pipeline_steps[-1])
    rec_step = next((s for s in pipeline_steps if s["id"] == "agent_recommend"), pipeline_steps[4])
    match = chroma.get("match") or (agent_response or {}).get("runbook_match") or {}
    grounded = bool(match.get("matched")) and not (agent_response or {}).get("runbook_gap")
    return {
        "alert_id": entry.get("id") or "custom",
        "alert_name": entry["alert_name"],
        "service": entry["service"],
        "severity": entry["severity"],
        "design_id": did,
        "stack": {k: stack[k] for k in ("name", "vector", "logs", "metrics", "policy", "llmops", "dashboards") if k in stack},
        "runbook_id": chroma.get("selected_runbook_id") or entry["runbook_id"],
        "runbook_gap": not grounded,
        "runbook_match": match,
        "phases": PHASE_LABELS,
        "steps": all_steps,
        "external_views": external_views,
        "agent_response": agent_response,
        "langfuse": lf,
        "hitl": {
            "required": hitl["payload"].get("requires_hitl"),
            "opa_allowed": hitl["payload"].get("opa_allowed"),
            "status": hitl["payload"].get("status"),
            "thread_id": (agent_response or {}).get("thread_id"),
            "recommendation": (agent_response or {}).get("recommendation") or rec_step["payload"].get("recommendation"),
        },
        "error": fire_error,
    }
