# Phase 3 — Evaluation (Design 1)

**Trio:** **Langfuse** · **MLflow** · **OTEL Collector**

| Tool | Port | Role |
|------|------|------|
| Langfuse | 3000 | Traces, sessions, prompts, evals |
| MLflow | 5001 | Experiments |
| OTEL | 4318 | Spans → Langfuse OTLP |

```bash
cd deploy && ./deploy.sh eval
```
