"""Shared Langfuse trace context for orchestrator, sub-agents, LLM, and tool spans."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_trace: ContextVar[Any] = ContextVar("lf_trace", default=None)
_span_stack: ContextVar[list[Any]] = ContextVar("lf_span_stack", default=[])

STANDALONE_NODES: dict[str, dict[str, str]] = {
    "classify": {"label": "Classify Alert", "phase": "1-triage", "agent": "orchestrator", "icon": "🎯"},
    "retrieve_runbook": {"label": "Retrieve Runbook (RAG)", "phase": "2-context", "agent": "orchestrator", "icon": "📚"},
    "query_logs": {"label": "Query Logs (Loki)", "phase": "2-context", "agent": "orchestrator", "icon": "📋"},
    "query_metrics": {"label": "Query Metrics (Prometheus)", "phase": "2-context", "agent": "orchestrator", "icon": "📈"},
    "recommend": {"label": "Recommend Remediation", "phase": "3-decision", "agent": "orchestrator", "icon": "💡"},
    "hitl_gate": {"label": "Human-in-the-Loop Gate", "phase": "4-guardrails", "agent": "orchestrator", "icon": "🛡️"},
    "execute": {"label": "Execute & Ticket", "phase": "5-action", "agent": "orchestrator", "icon": "⚡"},
}

MULTI_NODES: dict[str, dict[str, str]] = {
    "supervisor": {"label": "Supervisor Route", "phase": "0-route", "agent": "supervisor", "icon": "🧭"},
    "triage_worker": {"label": "Triage Sub-Agent", "phase": "1-triage", "agent": "sub-agent", "icon": "🔍"},
    "runbook_worker": {"label": "Runbook Sub-Agent", "phase": "2-context", "agent": "sub-agent", "icon": "📚"},
    "logs_worker": {"label": "Logs Sub-Agent", "phase": "2-context", "agent": "sub-agent", "icon": "📋"},
    "metrics_worker": {"label": "Metrics Sub-Agent", "phase": "2-context", "agent": "sub-agent", "icon": "📈"},
    "observability_worker": {"label": "Observability Sub-Agent", "phase": "2-context", "agent": "sub-agent", "icon": "📊"},
    "remediation_worker": {"label": "Remediation Sub-Agent", "phase": "3-decision", "agent": "sub-agent", "icon": "💡"},
    "hitl_gate": {"label": "Human-in-the-Loop Gate", "phase": "4-guardrails", "agent": "supervisor", "icon": "🛡️"},
    "incident_worker": {"label": "Incident Sub-Agent", "phase": "5-action", "agent": "sub-agent", "icon": "🎫"},
}


def init_trace_context(trace: Any, *, orchestrator_name: str, metadata: dict[str, Any] | None = None) -> Any:
    """Attach a Langfuse trace and open the top-level orchestrator span."""
    _trace.set(trace)
    _span_stack.set([])
    meta = metadata or {}
    root = trace.span(
        name=orchestrator_name,
        metadata={"type": "orchestrator", **meta},
        input={"description": "Agent pipeline execution"},
    )
    push_span(root)
    return root


def clear_trace_context() -> None:
    stack = _span_stack.get()
    while stack:
        span = stack.pop()
        try:
            span.end()
        except Exception:
            pass
    _span_stack.set([])
    _trace.set(None)


def push_span(span: Any) -> None:
    stack = _span_stack.get()
    stack.append(span)
    _span_stack.set(stack)


def pop_span() -> None:
    stack = _span_stack.get()
    if stack:
        stack.pop()
    _span_stack.set(stack)


def _parent() -> Any:
    stack = _span_stack.get()
    if stack:
        return stack[-1]
    return _trace.get()


def _start_observation(
    name: str,
    *,
    kind: str = "span",
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    output: Any = None,
    level: str | None = None,
) -> Any:
    """Create a Langfuse 2.x SPAN, GENERATION, or EVENT under the current parent."""
    parent = _parent()
    if not parent:
        return None
    meta = dict(metadata or {})
    payload_in = _safe_payload(input)
    kind = (kind or "span").lower()
    try:
        if kind == "generation" and hasattr(parent, "generation"):
            return parent.generation(
                name=name,
                input=payload_in,
                metadata=meta,
                model=meta.get("model") or os.getenv("LLM_MODEL", "llama3.2"),
            )
        if kind == "event" and hasattr(parent, "event"):
            kwargs: dict[str, Any] = {
                "name": name,
                "input": payload_in,
                "metadata": {"type": meta.get("type") or "event", **meta},
            }
            if output is not None:
                kwargs["output"] = _safe_payload(output)
            if level:
                kwargs["level"] = level
            return parent.event(**kwargs)
        return parent.span(name=name, input=payload_in, metadata=meta)
    except Exception:
        try:
            return parent.span(name=name, input=payload_in, metadata=meta)
        except Exception:
            return None


def emit_event(
    name: str,
    *,
    input: Any = None,
    output: Any = None,
    metadata: dict[str, Any] | None = None,
    level: str = "DEFAULT",
) -> None:
    """Point-in-time Langfuse EVENT (HITL, ticket, RAG verdict, policy)."""
    _start_observation(name, kind="event", input=input, output=output, metadata=metadata, level=level)


def _safe_payload(value: Any, limit: int = 3000) -> Any:
    try:
        import json

        text = json.dumps(value, default=str)
        if len(text) <= limit:
            return value
        return {"preview": text[:limit], "truncated": True}
    except Exception:
        text = str(value)
        return text[:limit] if len(text) > limit else text


@contextmanager
def trace_span(
    name: str,
    *,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    kind: str = "span",
):
    obs = _start_observation(name, kind=kind, input=input, metadata=metadata)
    if not obs:
        yield None
        return

    if kind != "event":
        push_span(obs)
    try:
        yield obs
    except Exception as exc:
        if hasattr(obs, "end"):
            try:
                obs.end(level="ERROR", status_message=str(exc))
            except Exception:
                pass
        raise
    finally:
        if kind != "event":
            pop_span()


def trace_llm_generation(name: str, system: str, user: str, fn: Callable[[], str]) -> str:
    """Record an LLM generation span with prompts and response."""
    if not _parent():
        return fn()

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    provider = os.getenv("LLM_PROVIDER") or ("mock" if os.getenv("MOCK_LLM", "false").lower() == "true" else "openai")
    use_mock = os.getenv("MOCK_LLM", "false").lower() == "true"

    with trace_span(
        name,
        kind="generation",
        input={
            "system": system[:2000],
            "user": user[:4000],
            "messages": [
                {"role": "system", "content": system[:800]},
                {"role": "user", "content": user[:1200]},
            ],
        },
        metadata={"model": model, "provider": provider, "mock": use_mock, "type": "llm"},
    ) as obs:
        result = fn()
        if obs and hasattr(obs, "end"):
            try:
                obs.end(
                    output={"content": result[:4000]},
                    metadata={"model": model, "provider": provider, "type": "llm"},
                    usage={
                        "input": max(1, len(system) // 4),
                        "output": max(1, len(result) // 4),
                        "unit": "TOKENS",
                    },
                )
            except TypeError:
                obs.end(output={"content": result[:4000]})
        return result


@contextmanager
def trace_tool(name: str, *, input: Any = None, metadata: dict[str, Any] | None = None):
    """Record a tool/integration span (RAG, Loki, OPA, tickets, etc.)."""
    meta = {"type": "tool", **(metadata or {})}
    with trace_span(name, input=input, metadata=meta) as obs:
        yield obs


def infer_llm_trace_name(system: str) -> str:
    sys_lower = system.lower()
    if "llm-as-judge" in sys_lower or "llm as judge" in sys_lower:
        return "LLM · LLM-as-judge"
    if "supervisor" in sys_lower:
        return "LLM · Supervisor Routing"
    if "classify" in sys_lower:
        return "LLM · Classify Intent"
    if "recommend" in sys_lower or "remediation" in sys_lower:
        return "LLM · Recommend Remediation"
    return "LLM · Completion"


def trace_graph_node(node_id: str, *, multi: bool = False) -> Callable[[F], F]:
    """Decorator for LangGraph nodes — opens a named agent/node span."""
    catalog = MULTI_NODES if multi else STANDALONE_NODES
    meta = catalog.get(node_id, {"label": node_id, "phase": "pipeline", "agent": "orchestrator", "icon": "▸"})

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(state: dict, *args: Any, **kwargs: Any) -> dict:
            if not _parent():
                return fn(state, *args, **kwargs)

            alert = state.get("alert") or {}
            display = f"{meta.get('icon', '▸')} {meta['label']}"
            node_input = {
                "service": alert.get("service"),
                "severity": alert.get("severity"),
                "error_summary": (alert.get("error_summary") or "")[:200],
            }
            node_meta = {
                "node": node_id,
                "phase": meta.get("phase"),
                "agent": meta.get("agent"),
                "agent_type": meta.get("agent"),
                "type": "agent",
            }
            with trace_span(display, input=node_input, metadata=node_meta) as obs:
                result = fn(state, *args, **kwargs)
                if obs:
                    obs.end(output=_safe_payload(result))
                return result

        return wrapper  # type: ignore[return-value]

    return decorator
