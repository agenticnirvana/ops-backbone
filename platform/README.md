# Production AgentOps Platform

**Course:** Production AgentOps — see [`../00-PROBLEM-STATEMENT.md`](../00-PROBLEM-STATEMENT.md)

Enterprise agent platform: **standalone · multi-agent · MCP** with JWT auth and HITL UI.

## Architecture tiers

| Tier | What you get | Folder |
|------|--------------|--------|
| **1 — Standalone** | Single LangGraph pipeline | [`../reference-agent/`](../reference-agent/) |
| **2 — Multi-agent** | Supervisor + specialist workers | [`multi_agent/`](multi_agent/) |
| **3 — MCP** | Tools via Model Context Protocol | [`mcp_server/`](mcp_server/) |
| **4 — Enterprise UI** | JWT auth, HITL console, mode switcher | [`gateway/`](gateway/) + [`ui/`](ui/) |

```
                    ┌─────────────────────────────────┐
                    │   Web UI (JWT auth, HITL queue)  │
                    └───────────────┬─────────────────┘
                                    │
                    ┌───────────────▼─────────────────┐
                    │         API Gateway            │
                    │  /standalone /multi /mcp       │
                    └───────┬───────────┬───────────┘
                            │           │
              ┌─────────────▼─┐   ┌─────▼──────┐
              │ Standalone    │   │ Multi-agent │
              │ LangGraph     │   │ Supervisor  │
              └───────┬───────┘   └─────┬──────┘
                      │                 │
              ┌───────▼─────────────────▼───────┐
              │     MCP Server (ops tools)       │
              │  logs · runbooks · tickets · metrics │
              └───────────────────────────────────┘
                      │
              ┌───────▼───────────────────────────┐
              │ Langfuse · MLflow · OTel · K8s     │
              │ AWS AgentCore · Azure Foundry      │
              └───────────────────────────────────┘
```

## Quick start

```bash
cd agentic-aiops-course/platform
cp .env.example .env
pip install -r requirements.txt
cd ../reference-agent && python -m rag.build_index && cd ../platform
uvicorn gateway.main:app --reload --port 8080
```

Open http://localhost:8080 — login `operator@agentops.local` / `operator123`

## Agent modes

### 1. Standalone agent
Classic linear LangGraph: classify → RAG → logs → recommend → HITL → ticket.

### 2. Multi-agent system
Supervisor orchestrates specialist workers:
- `triage_worker` — classification
- `runbook_worker` — RAG retrieval
- `observability_worker` — log/metrics context
- `remediation_worker` — recommendation
- `incident_worker` — ticket creation

Worker trace visible in UI for debugging.

### 3. MCP agent
Same flow but tools exposed via **Model Context Protocol** — one server, any MCP-compatible client (LangGraph, Claude Desktop, Cursor).

```bash
# Run MCP server (stdio or HTTP)
python -m mcp_server.server http
```

## Docker (full stack)

```bash
docker compose up --build
```

Services: gateway (8080), MCP server (8081), MLflow (5000), OTEL collector.

## Auth (enterprise pattern)

| User | Role | Can invoke agents |
|------|------|-------------------|
| operator@agentops.local | operator | Yes |
| admin@agentops.local | admin | Yes + config |
| viewer@agentops.local | viewer | Read-only |

Replace `DEMO_USERS` in `shared/auth.py` with **Entra ID / OIDC** in production.

## Docs

- [`../11-ZERO-TO-HERO-ARCHITECTURE.md`](../11-ZERO-TO-HERO-ARCHITECTURE.md) — maturity tiers
- [`../12-AIOPS-LIFECYCLE-TOOLMAP.md`](../12-AIOPS-LIFECYCLE-TOOLMAP.md) — OSS / AWS / Azure per phase
- [`../13-MARKET-ALTERNATIVES.md`](../13-MARKET-ALTERNATIVES.md) — market tool map
