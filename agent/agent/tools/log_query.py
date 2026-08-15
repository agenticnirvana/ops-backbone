"""Log query — Grafana Loki (production) with optional fixture fallback for offline dev."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.parse import quote

import httpx


def _fixture_logs(service: str, error_summary: str, limit: int) -> list[dict]:
    logs_dir = os.getenv("LOG_FIXTURES_DIR")
    if logs_dir and os.path.isdir(logs_dir):
        path = os.path.join(logs_dir, f"{service}.jsonl")
        if os.path.isfile(path):
            rows = []
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
            return rows[:limit]
    return [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "service": service,
            "message": error_summary,
        }
    ][:limit]


def _cloudwatch_logs(service: str, error_summary: str, limit: int) -> list[dict]:
    import boto3

    log_group = os.getenv("CLOUDWATCH_LOG_GROUP", "")
    if not log_group:
        raise RuntimeError("CLOUDWATCH_LOG_GROUP is required for cloudwatch log backend")

    client = boto3.client("logs", region_name=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")))
    resp = client.filter_log_events(
        logGroupName=log_group,
        filterPattern=f'"{service}"',
        limit=limit,
    )
    out: list[dict] = []
    for event in resp.get("events", []):
        msg = event.get("message", "")
        try:
            out.append(json.loads(msg))
        except json.JSONDecodeError:
            out.append(
                {
                    "timestamp": datetime.fromtimestamp(event["timestamp"] / 1000, tz=timezone.utc).isoformat(),
                    "level": "ERROR" if "error" in msg.lower() else "INFO",
                    "service": service,
                    "message": msg,
                }
            )
    return out[:limit] if out else _fixture_logs(service, error_summary, limit)


def _elasticsearch_logs(service: str, error_summary: str, limit: int) -> list[dict]:
    es_url = os.getenv("ELASTICSEARCH_URL", "").rstrip("/")
    index = os.getenv("ELASTICSEARCH_INDEX", "agentops-logs")
    if not es_url:
        raise RuntimeError("ELASTICSEARCH_URL is required for elasticsearch log backend")
    needle = (error_summary or "").split()[0] if error_summary else ""
    must: list[dict] = [{"match": {"service": service}}]
    if needle:
        must.append({"query_string": {"query": needle[:40], "default_field": "message"}})
    body = {
        "query": {"bool": {"must": must}},
        "size": limit,
        "sort": [{"timestamp": {"order": "desc", "unmapped_type": "date"}}],
    }
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{es_url}/{index}/_search", json=body)
        r.raise_for_status()
        hits = (((r.json().get("hits") or {}).get("hits")) or [])
    out: list[dict] = []
    for hit in hits:
        src = hit.get("_source") or {}
        out.append(
            {
                "timestamp": src.get("timestamp") or src.get("@timestamp"),
                "level": src.get("level", "INFO"),
                "service": src.get("service", service),
                "message": src.get("message") or src.get("log") or "",
            }
        )
    return out[:limit] if out else _fixture_logs(service, error_summary, limit)


def query_logs(service: str, error_summary: str, limit: int = 5) -> list[dict]:
    """Query logs from Loki, CloudWatch, or fixture backend."""
    from observability.trace_context import trace_tool

    backend = os.getenv("LOG_QUERY_BACKEND", "").lower() or (
        "elasticsearch" if os.getenv("ELASTICSEARCH_URL") else ("loki" if os.getenv("LOKI_URL") else "fixture")
    )
    with trace_tool(
        "🔧 Tool · Elasticsearch Log Query" if backend == "elasticsearch" else "🔧 Tool · Loki Log Query",
        input={"service": service, "error_summary": error_summary[:200], "limit": limit},
        metadata={"backend": backend, "integration": backend or "logs"},
    ) as span:
        result = _query_logs_impl(service, error_summary, limit)
        if span:
            span.end(output={"count": len(result), "sample_level": result[0].get("level") if result else None})
        return result


def _query_logs_impl(service: str, error_summary: str, limit: int = 5) -> list[dict]:
    if not (service or "").strip():
        return _fixture_logs(service or "unknown", error_summary, limit)

    backend = os.getenv("LOG_QUERY_BACKEND", "").lower()
    if backend == "fixture" or (
        not backend
        and not os.getenv("ELASTICSEARCH_URL")
        and not os.getenv("LOKI_URL")
        and not os.getenv("CLOUDWATCH_LOG_GROUP")
    ):
        return _fixture_logs(service, error_summary, limit)
    if backend == "cloudwatch" or os.getenv("CLOUDWATCH_LOG_GROUP"):
        return _cloudwatch_logs(service, error_summary, limit)
    if backend == "elasticsearch" or os.getenv("ELASTICSEARCH_URL"):
        return _elasticsearch_logs(service, error_summary, limit)

    loki_url = os.getenv("LOKI_URL", "").rstrip("/")
    if not loki_url:
        raise RuntimeError("LOKI_URL is required (production stack — no synthetic logs)")

    needle = error_summary.split()[0] if error_summary else ""
    query = f'{{service="{service}"}}'
    if needle:
        query += f' |= "{needle[:40]}"'

    url = f"{loki_url}/loki/api/v1/query_range?query={quote(query)}&limit={limit}&direction=BACKWARD"

    with httpx.Client(timeout=10.0) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()
    out: list[dict] = []
    for stream in data.get("data", {}).get("result", []):
        labels = stream.get("stream", {})
        for ts, line in stream.get("values", [])[:limit]:
            try:
                parsed = json.loads(line)
                out.append(parsed)
            except json.JSONDecodeError:
                out.append(
                    {
                        "timestamp": ts,
                        "level": labels.get("level", "INFO"),
                        "service": labels.get("service", service),
                        "message": line,
                    }
                )
            if len(out) >= limit:
                break
        if len(out) >= limit:
            break
    return out[:limit]
