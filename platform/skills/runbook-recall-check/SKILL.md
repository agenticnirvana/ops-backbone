# Runbook Recall Check

Eval skill for RAG quality — verifies the agent retrieved the **expected runbook ID** for a service.

## Skill vs MCP

| Skill | MCP `retrieve_runbooks` |
|-------|-------------------------|
| Assert expected ID in CI/eval | Fetch live chunks from Chroma at runtime |
| Golden-alert regression gate | Production triage with fresh embeddings |

Used by MLflow eval gate and manual verification before trusting automation.
