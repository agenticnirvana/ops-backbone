"""Per-design tool names, Langfuse keys, and Grafana Explore deep links.

Live pipeline labels MUST come from this module so D3 never says Chroma/Loki.
"""

from __future__ import annotations

import os
from typing import Any

STACKS: dict[str, dict[str, Any]] = {
    "d1": {
        "id": "d1",
        "name": "Design 1",
        "vector": "Chroma",
        "vector_title": "Chroma RAG · Runbook retrieval",
        "logs": "Loki",
        "logs_title": "Query logs · Loki",
        "metrics": "Prometheus",
        "metrics_title": "Query metrics · Prometheus",
        "metrics_ingest_title": "Prometheus",
        "metrics_ingest_sub": "Scrape + rule evaluation",
        "policy": "OPA / Rego",
        "policy_title": "OPA policy check",
        "policy_sub": "Rego · allow/deny destructive actions",
        "dashboards": "Grafana",
        "llmops": "Langfuse",
        "traces": "OTEL → Langfuse",
        "eval_backend": "langfuse",
        "logs_backend": "loki",
        "metrics_backend": "prometheus",
        "vector_visual": "chroma",
        "grafana_metrics_uid": "prometheus",
        "grafana_logs_uid": "loki",
    },
    "d2": {
        "id": "d2",
        "name": "Design 2",
        "vector": "Weaviate",
        "vector_title": "Weaviate RAG · Runbook retrieval",
        "logs": "Elasticsearch",
        "logs_title": "Query logs · Elasticsearch",
        "metrics": "VictoriaMetrics",
        "metrics_title": "Query metrics · VictoriaMetrics",
        "metrics_ingest_title": "VictoriaMetrics",
        "metrics_ingest_sub": "Scrape + rule evaluation",
        "policy": "OpenFGA",
        "policy_title": "OpenFGA authorization check",
        "policy_sub": "Tuple · allow/deny destructive actions",
        "dashboards": "Kibana + Grafana",
        "llmops": "Arize Phoenix",
        "traces": "OTEL → Phoenix",
        "eval_backend": "phoenix",
        "logs_backend": "elasticsearch",
        "metrics_backend": "victoriametrics",
        "vector_visual": "chroma",
        "grafana_metrics_uid": "victoriametrics",
        "grafana_logs_uid": "elasticsearch",
    },
    "d3": {
        "id": "d3",
        "name": "Design 3",
        "vector": "OpenSearch k-NN",
        "vector_title": "OpenSearch k-NN · Runbook retrieval",
        "logs": "OpenSearch",
        "logs_title": "Query logs · OpenSearch",
        "metrics": "Mimir",
        "metrics_title": "Query metrics · Mimir",
        "metrics_ingest_title": "Prometheus + Mimir",
        "metrics_ingest_sub": "Scrape → remote_write to Mimir",
        "policy": "OPA / Rego",
        "policy_title": "OPA policy check",
        "policy_sub": "Rego · allow/deny destructive actions",
        "dashboards": "OpenSearch Dashboards + Grafana",
        "llmops": "MLflow",
        "traces": "MLflow Tracing",
        "eval_backend": "mlflow",
        "logs_backend": "opensearch",
        "metrics_backend": "mimir",
        "vector_visual": "chroma",
        "grafana_metrics_uid": "mimir",
        "grafana_logs_uid": "opensearch",
        "include_tempo_step": True,
    },
}


def normalize_design_id(design_id: str | None) -> str:
    raw = (design_id or os.getenv("ARCH_DESIGN_ID") or "d2").strip().lower()
    if raw in ("1", "design-1", "design1"):
        return "d1"
    if raw in ("2", "design-2", "design2"):
        return "d2"
    if raw in ("3", "design-3", "design3"):
        return "d3"
    return raw if raw in STACKS else "d2"


def get_stack(design_id: str | None = None) -> dict[str, Any]:
    return STACKS[normalize_design_id(design_id)]


def langfuse_keys(design_id: str | None = None) -> tuple[str, str]:
    """Public/secret key for the Langfuse project that belongs to this design."""
    did = normalize_design_id(design_id).upper()
    pk = os.getenv(f"LANGFUSE_{did}_PUBLIC_KEY") or os.getenv("LANGFUSE_PUBLIC_KEY") or ""
    sk = os.getenv(f"LANGFUSE_{did}_SECRET_KEY") or os.getenv("LANGFUSE_SECRET_KEY") or ""
    return pk, sk


def langfuse_host() -> str:
    return os.getenv("LANGFUSE_HOST", "http://langfuse:3000").rstrip("/")


def langfuse_public_url() -> str:
    return os.getenv("LANGFUSE_PUBLIC_URL", "http://localhost:3000").rstrip("/")
