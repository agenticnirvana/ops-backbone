# Phase 2 — Orchestration (Design 1)

**Fixed across all designs:** LangGraph · gateway · MCP · Ollama

| Component | Port |
|-----------|------|
| LangGraph agent | 8002 |
| Platform UI + gateway | 8080 |
| MCP server | 8081 |
| Ollama | 11434 |

Graph: `classify → retrieve_runbook → query_logs → query_metrics → recommend → hitl_gate → execute`

Code: [`../agent/agent/graph.py`](../agent/agent/graph.py)
