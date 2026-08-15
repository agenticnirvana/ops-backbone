"""Input guardrails — prompt injection and abuse patterns."""

from __future__ import annotations

INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous",
    "system prompt",
    "you are now",
    "jailbreak",
    "<|im_start|>",
)

MAX_FIELD_LEN = 4000


def validate_alert_input(alert: dict) -> tuple[bool, str]:
    """Return (ok, reason). Blocks obvious injection / oversized payloads."""
    for key, value in alert.items():
        if isinstance(value, str) and len(value) > MAX_FIELD_LEN:
            return False, f"Field {key} exceeds max length"
        text = str(value).lower()
        for pattern in INJECTION_PATTERNS:
            if pattern in text:
                return False, f"Blocked input pattern: {pattern}"
    return True, ""
