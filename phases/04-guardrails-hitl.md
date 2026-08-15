# Phase 4 — Guardrails & HITL (Design 1)

| Tool | Role |
|------|------|
| LangGraph `interrupt_before` | Pause before execute |
| Platform UI | Approve / reject |
| **OPA / Rego** | Tool authorization — [`deploy/config/opa/policy.rego`](../deploy/config/opa/policy.rego) |
| FastAPI guardrails | Input validation |

**Alternatives:** OpenFGA (D2) · NeMo Guardrails (D3)
