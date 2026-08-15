"""Langfuse tracing via langchain-core callbacks (no langchain package required)."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler

from observability.trace_context import MULTI_NODES, STANDALONE_NODES, init_trace_context

_langfuse_clients: dict[str, Any] = {}

_SKIP_CHAIN_NAMES = frozenset(
    {
        "LangGraph",
        "RunnableSequence",
        "RunnableLambda",
        "RunnableParallel",
        "__start__",
        "__end__",
        "ChannelWrite",
        "ChannelRead",
        "route_after_recommend",
        "route_after_hitl",
        "route_after_supervisor",
    }
)

_INSTRUMENTED_NODES = frozenset(STANDALONE_NODES.keys()) | frozenset(MULTI_NODES.keys())


def _client(design_id: str | None = None):
    from observability.design_keys import langfuse_keys, normalize_design_id

    did = normalize_design_id(design_id)
    if did not in _langfuse_clients:
        from langfuse import Langfuse

        pk, sk = langfuse_keys(did)
        _langfuse_clients[did] = Langfuse(
            public_key=pk,
            secret_key=sk,
            host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
        )
    return _langfuse_clients[did]


class LangfuseGraphHandler(BaseCallbackHandler):
    """Emit LangGraph runs to Langfuse 2.x with orchestrator + manual child spans."""

    def __init__(self, *, trace_name: str, session_id: str | None = None, user_id: str | None = None, design_id: str | None = None):
        super().__init__()
        from observability.design_keys import normalize_design_id

        self._design_id = normalize_design_id(design_id)
        self._lf = _client(self._design_id)
        self._trace = self._lf.trace(
            name=trace_name,
            session_id=session_id,
            user_id=user_id,
            tags=[self._design_id, "ops-triage"],
            metadata={"trace_name": trace_name, "session_id": session_id, "design": self._design_id},
        )
        self._observations: dict[UUID, Any] = {}
        is_multi = "multi" in trace_name
        orchestrator_name = "Supervisor Orchestrator" if is_multi else "Standalone Orchestrator"
        init_trace_context(
            self._trace,
            orchestrator_name=f"{'🧭' if is_multi else '🤖'} {orchestrator_name}",
            metadata={"mode": trace_name, "topology": "multi-agent" if is_multi else "standalone"},
        )

    @property
    def trace_id(self) -> str | None:
        return getattr(self._trace, "id", None)

    def _parent(self, parent_run_id: UUID | None):
        if parent_run_id and parent_run_id in self._observations:
            return self._observations[parent_run_id]
        from observability.trace_context import _parent as ctx_parent

        ctx = ctx_parent()
        return ctx or self._trace

    def _should_skip_chain(self, name: str) -> bool:
        if name in _SKIP_CHAIN_NAMES or name in _INSTRUMENTED_NODES:
            return True
        if name.endswith("-invoke") or name.endswith("-approve"):
            return True
        return name.startswith("Runnable") or name.startswith("Channel")

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        name = kwargs.get("name") or (serialized or {}).get("name") or (serialized or {}).get("id") or "chain"
        name = str(name)
        if self._should_skip_chain(name):
            self._observations[run_id] = self._parent(parent_run_id)
            return
        parent = self._parent(parent_run_id)
        obs = parent.span(name=name, input=_safe_payload(inputs), metadata=metadata or {})
        self._observations[run_id] = obs

    def on_chain_end(self, outputs: dict[str, Any], *, run_id: UUID, **kwargs: Any) -> None:
        obs = self._observations.pop(run_id, None)
        if obs and hasattr(obs, "end") and obs not in (self._trace,):
            try:
                obs.end(output=_safe_payload(outputs))
            except Exception:
                pass

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        obs = self._observations.pop(run_id, None)
        if obs and hasattr(obs, "end"):
            try:
                obs.end(level="ERROR", status_message=str(error))
            except Exception:
                pass

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        parent = self._parent(parent_run_id)
        name = (serialized or {}).get("name") or "LLM · LangChain"
        obs = parent.generation(
            name=str(name),
            input={"prompts": prompts[:3]},
            model=os.getenv("LLM_MODEL", "llama3.2"),
            metadata={"type": "llm"},
        )
        self._observations[run_id] = obs

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        obs = self._observations.pop(run_id, None)
        if obs:
            obs.end(output=_safe_payload(getattr(response, "generations", response)))

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        obs = self._observations.pop(run_id, None)
        if obs:
            obs.end(level="ERROR", status_message=str(error))

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        parent = self._parent(parent_run_id)
        name = (serialized or {}).get("name") or "tool"
        obs = parent.span(
            name=f"🔧 Tool · {name}",
            input={"input": input_str},
            metadata={"type": "tool"},
        )
        self._observations[run_id] = obs

    def on_tool_end(self, output: str, *, run_id: UUID, **kwargs: Any) -> None:
        obs = self._observations.pop(run_id, None)
        if obs:
            obs.end(output={"output": output})

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        obs = self._observations.pop(run_id, None)
        if obs:
            obs.end(level="ERROR", status_message=str(error))


def _safe_payload(value: Any, limit: int = 4000) -> Any:
    try:
        import json

        text = json.dumps(value, default=str)
        if len(text) <= limit:
            return value
        return {"preview": text[:limit], "truncated": True}
    except Exception:
        text = str(value)
        return text[:limit] if len(text) > limit else text
