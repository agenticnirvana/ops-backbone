# Severity Classifier (Rule-Based)

Structured **knowledge + script** for mapping alert text to P1/P2/P3 before the LLM classifies in LangGraph.

## Skill vs MCP

- **Skill**: deterministic rules in `classify_severity.py` — fast, testable, no network.
- **MCP / LLM**: use when rules are insufficient or you need log/metric context from live systems.

## Rules (summary)

- **P1**: checkout/payment outage, Redis pool, widespread 5xx, data loss language.
- **P2**: elevated errors on single service, auth degradation.
- **P3**: informational spikes, non-customer-facing noise.

Run the script with alert summary text as the first argument.
