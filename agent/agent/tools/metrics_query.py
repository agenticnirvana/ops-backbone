"""Metrics query — Prometheus (production)."""

from __future__ import annotations

import os

import httpx
import json


def query_metrics(service: str) -> dict:
    """Run PromQL against Prometheus. Returns latest gauge values for the service."""
    from observability.trace_context import trace_tool

    backend = os.getenv("METRICS_QUERY_BACKEND", "prometheus")
    with trace_tool(
        "🔧 Tool · VictoriaMetrics Query" if "victoria" in backend or os.getenv("VM_URL") else "🔧 Tool · Prometheus Metrics",
        input={"service": service},
        metadata={"backend": backend, "integration": "metrics"},
    ) as span:
        result = _query_metrics_impl(service)
        if span:
            span.end(output=result)
        return result


def _query_metrics_impl(service: str) -> dict:
    if os.getenv("METRICS_QUERY_BACKEND", "").lower() == "fixture":
        path = os.getenv("METRICS_FILE", "")
        if path and os.path.isfile(path):
            data = json.loads(open(path, encoding="utf-8").read())
            return {"service": service, **data.get(service, {})}
        return {"service": service, "cpu_percent": 0.0, "error_rate_5m": 0.0, "p95_latency_ms": 0.0, "active_incidents": 0}

    prom_url = (os.getenv("VM_URL") or os.getenv("PROMETHEUS_URL") or "").rstrip("/")
    if not prom_url:
        raise RuntimeError("VM_URL or PROMETHEUS_URL is required (production stack — no synthetic metrics)")

    queries = {
        "cpu_percent": f'service_cpu_percent{{service="{service}"}}',
        "error_rate_5m": f'service_error_rate{{service="{service}"}}',
        "p95_latency_ms": f'service_p95_latency_ms{{service="{service}"}}',
        "active_incidents": f'service_active_incidents{{service="{service}"}}',
    }

    result: dict = {"service": service}
    with httpx.Client(timeout=10.0) as client:
        for key, promql in queries.items():
            r = client.get(
                f"{prom_url}/api/v1/query",
                params={"query": promql},
            )
            r.raise_for_status()
            data = r.json()
            value = None
            if data.get("data", {}).get("result"):
                value = float(data["data"]["result"][0]["value"][1])
            result[key] = value if value is not None else 0.0
    return result
