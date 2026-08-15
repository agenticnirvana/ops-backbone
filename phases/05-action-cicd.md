# Phase 5 — Action & CI/CD (Design 1)

| Tool | Role |
|------|------|
| ticket-api | Remediation record :8091 |
| PostgreSQL | Tickets + checkpoints via [`services/ticket-api/`](../services/ticket-api/) |
| **GitHub Actions** | [`.github/workflows/design1-ci.yml`](../.github/workflows/design1-ci.yml) |
| Chroma reindex CI | Rebuild agent image after `agent/rag/runbooks/**` change |
