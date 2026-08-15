"""Fetch Langfuse traces and analytics for platform UI visualization."""

from __future__ import annotations

import base64
import os
from collections import defaultdict
from statistics import mean
from typing import Any

import httpx

from observability.trace_context import MULTI_NODES, STANDALONE_NODES


def _auth_header() -> dict[str, str]:
    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sk = os.getenv("LANGFUSE_SECRET_KEY", "")
    token = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _host() -> str:
    return os.getenv("LANGFUSE_HOST", "http://langfuse:3000").rstrip("/")


def _ms(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        from datetime import datetime

        fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
        s = datetime.strptime(start.replace("+00:00", "Z"), fmt)
        e = datetime.strptime(end.replace("+00:00", "Z"), fmt)
        return max(0, int((e - s).total_seconds() * 1000))
    except Exception:
        return None


def _format_duration(ms: int | None) -> str:
    if ms is None:
        return "—"
    if ms >= 1000:
        return f"{ms / 1000:.1f}s"
    return f"{ms}ms"


def _obs_type(obs: dict[str, Any]) -> str:
    kind = (obs.get("type") or obs.get("observationType") or "SPAN").upper()
    if kind in ("GENERATION", "EVENT"):
        return kind.lower()
    meta = obs.get("metadata") or {}
    if isinstance(meta, str):
        return "span"
    if meta.get("type") == "llm":
        return "generation"
    if meta.get("type") == "tool":
        return "tool"
    if meta.get("type") == "orchestrator" or meta.get("agent_type"):
        return "agent"
    return "span"


def _build_tree(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {o["id"]: {**o, "children": []} for o in observations if o.get("id")}
    roots: list[dict[str, Any]] = []
    for obs in by_id.values():
        parent_id = obs.get("parentObservationId")
        if parent_id and parent_id in by_id:
            by_id[parent_id]["children"].append(obs)
        else:
            roots.append(obs)

    def sort_key(o: dict[str, Any]) -> str:
        return o.get("startTime") or o.get("createdAt") or ""

    def walk(node: dict[str, Any], depth: int = 0) -> dict[str, Any]:
        children = sorted(node.get("children") or [], key=sort_key)
        duration_ms = _ms(node.get("startTime"), node.get("endTime"))
        meta = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        return {
            "id": node.get("id"),
            "name": node.get("name") or "span",
            "type": _obs_type(node),
            "depth": depth,
            "duration_ms": duration_ms,
            "duration": _format_duration(duration_ms),
            "phase": meta.get("phase"),
            "agent": meta.get("agent") or meta.get("agent_type"),
            "node": meta.get("node"),
            "model": meta.get("model"),
            "status": node.get("level") or "DEFAULT",
            "children": [walk(c, depth + 1) for c in children],
        }

    return [walk(r) for r in sorted(roots, key=sort_key)]


def fetch_trace_by_session(session_id: str) -> dict[str, Any]:
    """Return hierarchical trace tree for a Langfuse session (thread_id)."""
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return {"session_id": session_id, "spans": [], "message": "Langfuse not configured"}

    headers = _auth_header()
    host = _host()

    try:
        with httpx.Client(timeout=20.0) as client:
            tr = client.get(
                f"{host}/api/public/traces",
                params={"sessionId": session_id, "limit": 1},
                headers=headers,
            )
            tr.raise_for_status()
            traces = tr.json().get("data") or []
            if not traces:
                return {"session_id": session_id, "spans": [], "message": "No trace yet — run the pipeline first"}

            trace = traces[0]
            trace_id = trace.get("id")
            obs_resp = client.get(
                f"{host}/api/public/observations",
                params={"traceId": trace_id, "limit": 100},
                headers=headers,
            )
            obs_resp.raise_for_status()
            observations = obs_resp.json().get("data") or []

        tree = _build_tree(observations)
        return {
            "session_id": session_id,
            "trace_id": trace_id,
            "trace_name": trace.get("name"),
            "timestamp": trace.get("timestamp"),
            "spans": tree,
            "flat_count": len(observations),
            "langfuse_url": f"{os.getenv('LANGFUSE_PUBLIC_URL', host)}/trace/{trace_id}",
        }
    except httpx.HTTPStatusError as exc:
        return {"session_id": session_id, "spans": [], "message": f"Langfuse API error: {exc.response.status_code}"}
    except Exception as exc:
        return {"session_id": session_id, "spans": [], "message": str(exc)}


def _public_url() -> str:
    return os.getenv("LANGFUSE_PUBLIC_URL", _host())


def _langfuse_client() -> httpx.Client:
    return httpx.Client(timeout=25.0, headers=_auth_header())


def _fetch_traces(client: httpx.Client, *, limit: int = 50) -> list[dict[str, Any]]:
    host = _host()
    traces: list[dict[str, Any]] = []
    page = 1
    while len(traces) < limit:
        batch_limit = min(50, limit - len(traces))
        resp = client.get(f"{host}/api/public/traces", params={"page": page, "limit": batch_limit})
        resp.raise_for_status()
        batch = resp.json().get("data") or []
        if not batch:
            break
        traces.extend(batch)
        if len(batch) < batch_limit:
            break
        page += 1
    return traces[:limit]


def _fetch_observations(client: httpx.Client, trace_id: str) -> list[dict[str, Any]]:
    host = _host()
    resp = client.get(f"{host}/api/public/observations", params={"traceId": trace_id, "limit": 100})
    resp.raise_for_status()
    return resp.json().get("data") or []


def _fetch_daily_metrics(client: httpx.Client, days: int = 14) -> list[dict[str, Any]]:
    host = _host()
    resp = client.get(f"{host}/api/public/metrics/daily", params={"limit": days})
    resp.raise_for_status()
    rows = resp.json().get("data") or []
    return [
        {
            "date": row.get("date"),
            "traces": row.get("countTraces", 0),
            "observations": row.get("countObservations", 0),
            "cost": row.get("totalCost", 0),
        }
        for row in reversed(rows)
    ]


def _fetch_scores(client: httpx.Client, limit: int = 50) -> list[dict[str, Any]]:
    host = _host()
    resp = client.get(f"{host}/api/public/scores", params={"limit": limit})
    resp.raise_for_status()
    return resp.json().get("data") or []


def _trace_latency_ms(trace: dict[str, Any]) -> int:
    latency = trace.get("latency")
    if latency is None:
        return 0
    return int(float(latency) * 1000)


def _mode_from_trace_name(name: str) -> str:
    if "multi" in name:
        return "multi-agent"
    if "standalone" in name:
        return "standalone"
    if "mcp" in name:
        return "mcp"
    return "other"


def _node_label(node_id: str) -> str:
    meta = STANDALONE_NODES.get(node_id) or MULTI_NODES.get(node_id) or {}
    icon = meta.get("icon", "")
    label = meta.get("label", node_id)
    return f"{icon} {label}".strip()


def _avg(values: list[int]) -> int:
    return int(mean(values)) if values else 0


def fetch_langfuse_dashboard(*, trace_limit: int = 30) -> dict[str, Any]:
    """Aggregate Langfuse analytics for dashboard charts and KPIs."""
    phoenix = os.getenv("PHOENIX_PUBLIC_URL") or os.getenv("PHOENIX_URL")
    if phoenix:
        return {
            "configured": True,
            "backend": "phoenix",
            "message": "Arize Phoenix is the Design 2 LLM ops UI",
            "phoenix_url": phoenix,
            "kpis": {},
            "recent_traces": [],
        }
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return {"configured": False, "message": "Langfuse not configured", "kpis": {}}

    try:
        with _langfuse_client() as client:
            traces = _fetch_traces(client, limit=trace_limit)
            daily = _fetch_daily_metrics(client, 14)
            scores = _fetch_scores(client, 100)

            latencies_ms = [_trace_latency_ms(t) for t in traces if _trace_latency_ms(t) > 0]
            span_types: dict[str, int] = defaultdict(int)
            phase_latency: dict[str, list[int]] = defaultdict(list)
            node_latency: dict[str, list[int]] = defaultdict(list)
            tool_latency: dict[str, list[int]] = defaultdict(list)
            mode_counts: dict[str, int] = defaultdict(int)
            hourly: dict[str, int] = defaultdict(int)
            llm_total = tool_total = obs_total = error_traces = 0

            recent_traces: list[dict[str, Any]] = []
            for trace in traces[: min(20, len(traces))]:
                name = trace.get("name") or "trace"
                mode = _mode_from_trace_name(name)
                mode_counts[mode] += 1
                ts = trace.get("timestamp") or trace.get("createdAt") or ""
                if len(ts) >= 13:
                    hourly[ts[11:13] + ":00"] += 1
                trace_id = trace.get("id")
                latency_ms = _trace_latency_ms(trace)
                recent_traces.append(
                    {
                        "trace_id": trace_id,
                        "session_id": trace.get("sessionId"),
                        "name": name,
                        "mode": mode,
                        "latency_ms": latency_ms,
                        "latency": _format_duration(latency_ms),
                        "timestamp": ts,
                        "langfuse_url": f"{_public_url()}/trace/{trace_id}",
                    }
                )
                observations = _fetch_observations(client, trace_id)
                obs_total += len(observations)
                for obs in observations:
                    typ = _obs_type(obs)
                    span_types[typ] += 1
                    if typ == "generation":
                        llm_total += 1
                    if typ == "tool":
                        tool_total += 1
                    dur = _ms(obs.get("startTime"), obs.get("endTime"))
                    meta = obs.get("metadata") if isinstance(obs.get("metadata"), dict) else {}
                    if meta.get("phase") and dur is not None:
                        phase_latency[str(meta["phase"])].append(dur)
                    if meta.get("node") and dur is not None:
                        node_latency[str(meta["node"])].append(dur)
                    if typ == "tool" and dur is not None:
                        tool_latency[obs.get("name") or "tool"].append(dur)
                    if (obs.get("level") or "").upper() == "ERROR":
                        error_traces += 1

            phase_order = ["0-route", "1-triage", "2-context", "3-decision", "4-guardrails", "5-action"]
            latency_by_phase = [
                {
                    "phase": phase,
                    "label": phase.split("-", 1)[-1].replace("-", " ").title(),
                    "avg_ms": _avg(phase_latency.get(phase, [])),
                    "count": len(phase_latency.get(phase, [])),
                }
                for phase in phase_order
                if phase_latency.get(phase)
            ]
            latency_by_node = sorted(
                [
                    {
                        "node": node,
                        "label": _node_label(node),
                        "avg_ms": _avg(values),
                        "count": len(values),
                    }
                    for node, values in node_latency.items()
                ],
                key=lambda x: x["avg_ms"],
                reverse=True,
            )[:8]
            tool_latency_chart = sorted(
                [
                    {"name": name.replace("🔧 Tool · ", ""), "avg_ms": _avg(values), "count": len(values)}
                    for name, values in tool_latency.items()
                ],
                key=lambda x: x["avg_ms"],
                reverse=True,
            )[:6]
            span_type_chart = [{"type": k, "count": v} for k, v in sorted(span_types.items(), key=lambda x: -x[1])]
            mode_chart = [{"mode": k, "count": v} for k, v in sorted(mode_counts.items(), key=lambda x: -x[1])]
            hourly_chart = sorted(
                [{"hour": h, "count": c} for h, c in hourly.items()],
                key=lambda x: x["hour"],
            )
            latency_trend = [
                {"timestamp": t.get("timestamp", "")[:16].replace("T", " "), "latency_ms": _trace_latency_ms(t)}
                for t in reversed(traces[:15])
                if _trace_latency_ms(t) > 0
            ]

            score_names = defaultdict(list)
            for score in scores:
                name = score.get("name") or "score"
                value = score.get("value")
                if value is not None:
                    score_names[name].append(float(value))

            score_summary = [
                {
                    "name": name,
                    "count": len(values),
                    "avg": round(mean(values), 2),
                    "latest": values[-1],
                }
                for name, values in sorted(score_names.items())
            ]

            sorted_lat = sorted(latencies_ms)
            p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0

            return {
                "configured": True,
                "langfuse_url": f"{_public_url()}/project/traces",
                "scores_url": f"{_public_url()}/project/scores",
                "kpis": {
                    "total_traces": len(traces),
                    "total_observations": obs_total or sum(d.get("observations", 0) for d in daily),
                    "avg_latency_ms": _avg(latencies_ms),
                    "p95_latency_ms": p95,
                    "llm_calls": llm_total,
                    "tool_calls": tool_total,
                    "error_observations": error_traces,
                    "avg_observations_per_trace": round(obs_total / len(traces), 1) if traces else 0,
                },
                "daily_activity": daily,
                "hourly_activity": hourly_chart,
                "latency_trend": latency_trend,
                "latency_by_phase": latency_by_phase,
                "latency_by_node": latency_by_node,
                "tool_latency": tool_latency_chart,
                "span_types": span_type_chart,
                "mode_breakdown": mode_chart,
                "recent_traces": recent_traces[:10],
                "scores": score_summary,
            }
    except httpx.HTTPStatusError as exc:
        return {"configured": True, "message": f"Langfuse API error: {exc.response.status_code}", "kpis": {}}
    except Exception as exc:
        return {"configured": True, "message": str(exc), "kpis": {}}


def record_pipeline_scores(
    session_id: str,
    *,
    mode: str = "standalone",
    domain: str = "sre",
    hitl_required: bool = False,
    trace_id: str | None = None,
) -> None:
    """Push numeric scores to Langfuse so its native Scores dashboard is populated."""
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return

    host = _host()
    headers = {**_auth_header(), "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=20.0) as client:
            if not trace_id:
                tr = client.get(f"{host}/api/public/traces", params={"sessionId": session_id, "limit": 1})
                tr.raise_for_status()
                traces = tr.json().get("data") or []
                if not traces:
                    return
                trace_id = traces[0]["id"]
            observations = _fetch_observations(client, trace_id)
            llm_calls = sum(1 for o in observations if _obs_type(o) == "generation")
            tool_calls = sum(1 for o in observations if _obs_type(o) == "tool")

            latency_ms = 0
            for obs in observations:
                name = obs.get("name") or ""
                if "Orchestrator" in name:
                    latency_ms = _ms(obs.get("startTime"), obs.get("endTime")) or latency_ms
            if not latency_ms:
                try:
                    tr = client.get(f"{host}/api/public/traces/{trace_id}")
                    if tr.status_code == 200:
                        latency_ms = _trace_latency_ms(tr.json())
                except Exception:
                    pass
            if not latency_ms and observations:
                durs = [_ms(o.get("startTime"), o.get("endTime")) for o in observations]
                latency_ms = max(d for d in durs if d is not None) if any(durs) else 0

            scores = [
                ("pipeline_latency_ms", latency_ms, f"{domain}-{mode} end-to-end latency"),
                ("llm_call_count", llm_calls, "LLM generations in pipeline"),
                ("tool_call_count", tool_calls, "Tool/integration invocations"),
                ("observation_count", len(observations), "Total Langfuse observations"),
                ("hitl_required", 1 if hitl_required else 0, "Human approval required"),
            ]
            for name, value, comment in scores:
                resp = client.post(
                    f"{host}/api/public/scores",
                    headers=headers,
                    json={"traceId": trace_id, "name": name, "value": value, "comment": comment},
                )
                resp.raise_for_status()
    except Exception:
        pass
