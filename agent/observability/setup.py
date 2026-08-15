"""Observability — Langfuse, MLflow, OpenTelemetry setup."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any


def is_langfuse_enabled(design_id: str | None = None) -> bool:
    from observability.design_keys import langfuse_keys

    pk, sk = langfuse_keys(design_id)
    return bool(pk and sk)


def is_mlflow_enabled() -> bool:
    return bool(os.getenv("MLFLOW_TRACKING_URI"))


def get_langfuse_handler(*, trace_name: str = "ops-triage-invoke", session_id: str | None = None, user_id: str | None = None, design_id: str | None = None):
    """Return LangChain callback handler for Langfuse 2.x server."""
    if not is_langfuse_enabled(design_id):
        return None
    try:
        from observability.langfuse_handler import LangfuseGraphHandler

        return LangfuseGraphHandler(trace_name=trace_name, session_id=session_id, user_id=user_id, design_id=design_id)
    except Exception:
        return None


def flush_langfuse(design_id: str | None = None) -> None:
    """Push pending Langfuse batches (required after short-lived invoke calls)."""
    if not is_langfuse_enabled(design_id):
        return
    try:
        from observability.trace_context import clear_trace_context

        clear_trace_context()
    except Exception:
        pass
    try:
        from langfuse import Langfuse
        from observability.design_keys import langfuse_keys

        pk, sk = langfuse_keys(design_id)
        Langfuse(
            public_key=pk,
            secret_key=sk,
            host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
        ).flush()
    except Exception:
        pass


def setup_otel(service_name: str = "ops-triage-agent") -> None:
    """Configure OpenTelemetry SDK — collector only (Langfuse uses SDK callbacks)."""
    if os.getenv("OTEL_ENABLED", "false").lower() != "true":
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://otel-collector:4318/v1/traces",
        )
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
    except Exception:
        pass


def setup_mlflow_tracing(experiment_name: str = "ops-triage-agent") -> None:
    if not is_mlflow_enabled():
        return
    try:
        import mlflow

        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", ""))
        mlflow.set_experiment(experiment_name)
        if os.getenv("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", "true").lower() == "true":
            os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "true"
    except Exception:
        pass


@contextmanager
def trace_run(name: str, metadata: dict[str, Any] | None = None):
    """Context manager for manual span (fallback when Langfuse/OTel unavailable)."""
    meta = metadata or {}
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("ops-triage-agent")
        with tracer.start_as_current_span(name) as span:
            for k, v in meta.items():
                span.set_attribute(k, str(v))
            yield span
    except Exception:
        yield None


def build_invoke_config(trace_name: str, session_id: str | None = None, design_id: str | None = None) -> dict:
    """Build LangGraph invoke config with observability callbacks."""
    from observability.design_keys import normalize_design_id

    did = normalize_design_id(design_id)
    config: dict = {
        "configurable": {"thread_id": session_id or "default"},
        "run_name": trace_name,
        "tags": ["ops-triage", os.getenv("ENVIRONMENT", "dev"), did],
        "metadata": {
            "graph_version": os.getenv("GRAPH_VERSION", "1.0.0"),
            "index_version": os.getenv("INDEX_VERSION", "unknown"),
            "langfuse_trace_name": trace_name,
            "design": did,
        },
    }
    if session_id:
        config["metadata"]["langfuse_session_id"] = session_id
    handler = get_langfuse_handler(trace_name=trace_name, session_id=session_id, design_id=did)
    if handler:
        config["callbacks"] = [handler]
    return config
