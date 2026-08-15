# HITL Approval Checklist

Procedural **skill** (no script) — human operator steps before approving destructive remediation.

## Skill vs MCP

- **Skill**: checklist the operator reads; no API call.
- **MCP `create_ticket`**: executes only **after** HITL approve — side effect.

## Checklist

1. Confirm OPA verdict is **allow** (or understand deny reason).
2. Verify runbook citation matches alert service.
3. Confirm severity matches observability (Grafana/Loki spot-check).
4. For P1 + restart/scale language → require explicit comment.
5. Deny if recommendation is not grounded in retrieved runbook text.

This skill is bundled with the remediation worker and Simulation tab HITL flow.
