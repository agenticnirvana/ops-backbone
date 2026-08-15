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
    parent = _parent()
    if not parent:
        yield None
        return

    meta = metadata or {}
    if kind == "generation":
        obs = parent.generation(name=name, input=_safe_payload(input), metadata=meta)
    else:
        obs = parent.span(name=name, input=_safe_payload(input), metadata=meta)

    push_span(obs)
    try:
        yield obs
    except Exception as exc:
        obs.end(level="ERROR", status_message=str(exc))
        raise
    finally:
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
        if obs:
            obs.end(
                output={"content": result[:4000]},
                metadata={"model": model, "provider": provider},
            )
        return result


@contextmanager
def trace_tool(name: str, *, input: Any = None, metadata: dict[str, Any] | None = None):
    """Record a tool/integration span (RAG, Loki, OPA, tickets, etc.)."""
    meta = {"type": "tool", **(metadata or {})}
    with trace_span(name, input=input, metadata=meta) as obs:
        yield obs


def infer_llm_trace_name(system: str) -> str:
    sys_lower = system.lower()
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
            }
            with trace_span(display, input=node_input, metadata=node_meta) as obs:
                result = fn(state, *args, **kwargs)
                if obs:
                    obs.end(output=_safe_payload(result))
                return result

        return wrapper  # type: ignore[return-value]

    return decorator
