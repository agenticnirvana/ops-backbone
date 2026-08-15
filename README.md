# Architecture Design 1 — Chroma + Loki + Prometheus + Langfuse

See [`diagram.html`](diagram.html) (editable source) · regenerate PNG: [`../scripts/render-diagrams.sh`](../scripts/render-diagrams.sh)

![Architecture diagram](images/architecture-diagram.png)

**Tagline:** Lightweight, widely adopted OSS path — embedded vector store, Grafana Loki stack, Langfuse LLM engineering platform.

**When to pick:** Greenfield teams, fast local dev, Langfuse as single pane for traces / sessions / prompts / evals.

**Run the stack:** [`DESIGN-1-COMPLETE-WALKTHROUGH.md`](DESIGN-1-COMPLETE-WALKTHROUGH.md) · [`IMPLEMENTATION.md`](IMPLEMENTATION.md) · `cd deploy && ./deploy.sh up`

---

## Full architecture diagram

```mermaid
flowchart TB
  subgraph triggers [EntryPoints]
    AMWebhook[Alertmanager_webhook]
    OperatorUI[Platform_UI_8080]
  end

  subgraph phase1 [Phase1_Ingestion_D1_tools]
    AM[Alertmanager_9093]
    AR[alert_receiver_8090]
    PT[Promtail]
    LOKI[Loki_3100]
    PROM[Prometheus_9090]
    GRAF[Grafana_3001]
    RB[(runbooks_git_md)]
    REINDEX[chroma_reindex_job]
    CHROMA[(ChromaDB_vector)]
  end

  subgraph phase2 [Phase2_Orchestration_FIXED]
    GW[gateway_8080]
    AG[LangGraph_agent_8002]
    MCP[mcp_server_8081]
    OLL[Ollama_11434]
  end

  subgraph phase3 [Phase3_Evaluation_D1_tools]
    OTEL[OTEL_Collector_4318]
    LF[Langfuse_3000]
    LFDB[(postgres_langfuse)]
    MLF[MLflow_5001]
    EVL[eval_gate_Langfuse_datasets]
  end

  subgraph phase4 [Phase4_Guardrails_D1_tools]
    OPA[OPA_Rego_8181]
    HITL[LangGraph_hitl_interrupt]
    GUARD[FastAPI_guardrails]
  end

  subgraph phase5 [Phase5_Action_D1_tools]
    PG[(PostgreSQL)]
    TK[ticket_api_8091]
    GHA[GitHub_Actions]
  end

  AMWebhook --> AM
  AM --> AR
  OperatorUI --> GW
  AR --> AG
  PT --> LOKI
  LOKI --> GRAF
  PROM --> GRAF
  RB --> REINDEX
  REINDEX --> CHROMA

  GW --> AG
  AG --> MCP
  AG --> OLL
  AG --> CHROMA
  AG --> LOKI
  AG --> PROM
  AG --> HITL
  HITL --> GUARD
  HITL --> OPA

  AG --> OTEL
  GW --> OTEL
  OTEL --> LF
  AG --> LF
  LF --> LFDB
  EVL --> LF
  EVL --> MLF
  EVL --> CHROMA

  AG --> TK
  TK --> PG
  GHA --> EVL
  GHA --> REINDEX
```

---

## Tool map — Design 1 primaries + alternatives

### Phase 1 — Ingestion

| Section | **Design 1 primary** | Alt 1 | Alt 2 |
|---------|------------------------|-------|-------|
| Alert routing | **Alertmanager** | Grafana OnCall | Kapacitor |
| Logs | **Loki** + Promtail | Fluent Bit → Loki | Vector → Loki |
| Metrics | **Prometheus** | VictoriaMetrics | Mimir |
| Dashboards | **Grafana** | Prometheus UI | Redash |
| **Vector / runbooks** | **ChromaDB** | Qdrant | FAISS file index |
| Ingestion | **`runbook-ingestion` API + Drive cron** | CI reindex workflow | Manual CLI |
| Drop zone | Google Drive folder + git seed | — | — |

### Phase 2 — Orchestration (fixed)

| Section | Primary |
|---------|---------|
| Graph | **LangGraph** |
| API | FastAPI agent + gateway |
| LLM | Ollama / OpenAI API |

### Phase 3 — Evaluation

| Section | **Design 1 primary** | Alt 1 | Alt 2 |
|---------|------------------------|-------|-------|
| Tracing | **Langfuse** | LangSmith (SaaS) | Jaeger |
| Sessions | **Langfuse sessions** | — | OTEL traceparent |
| Prompt registry | **Langfuse Prompt Management** | Git prompts | LangSmith hub |
| Evals | **Langfuse datasets + eval gate** | DeepEval | Braintrust (SaaS) |
| Experiments | **MLflow** | W&B | Neptune |
| Distributed traces | **OTEL Collector → Langfuse OTLP** | OTEL → Jaeger | Datadog (SaaS) |

### Phase 4 — Guardrails

| Section | **Design 1 primary** | Alt 1 | Alt 2 |
|---------|------------------------|-------|-------|
| Action policy | **OPA / Rego** | Cedar | OpenFGA |
| Content safety | **FastAPI guardrails** | Presidio | NeMo Guardrails |
| HITL | Platform UI + interrupt | — | — |

### Phase 5 — Action

| Section | **Design 1 primary** | Alt 1 | Alt 2 |
|---------|------------------------|-------|-------|
| Tickets + checkpoints | **PostgreSQL** | SQLite dev | CockroachDB |
| CI/CD | **GitHub Actions** | GitLab CI | Tekton |

---

## Observability trio (Design 1)

| # | Tool | Role |
|---|------|------|
| 1 | **Langfuse** | Traces, sessions, prompts, evals |
| 2 | **MLflow** | Eval experiment metrics |
| 3 | **OTEL Collector** | Standard span pipeline → Langfuse |

---

## SRE capstone data path

```
Alert → agent → Chroma RAG (checkout-redis-pool.md)
              → Loki LogQL (pool timeout logs)
              → Prometheus (error rate)
              → Langfuse trace → HITL → ticket
```

**Compare:** [Design 2 — Weaviate + ELK](../architecture-design-2/) · [Design 3 — OpenSearch](../architecture-design-3/)

See [`PHASE-MAP.md`](PHASE-MAP.md) · [`diagram-full.md`](diagram-full.md)
