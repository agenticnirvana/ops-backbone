#!/usr/bin/env python3
"""Rule-based severity classifier for demo alerts."""

from __future__ import annotations

import json
import sys


def classify(text: str) -> dict:
    lower = text.lower()
    if any(k in lower for k in ("redis", "pool", "checkout", "payment", "data loss", "p1")):
        return {"severity": "P1", "reason": "Customer-facing checkout/payment or Redis pool signal"}
    if any(k in lower for k in ("5xx", "auth", "jwt", "latency", "cpu")):
        return {"severity": "P2", "reason": "Elevated errors or dependency degradation"}
    return {"severity": "P3", "reason": "No critical keywords — default informational tier"}


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else ""
    result = classify(text)
    result["source"] = "skill-script:classify_severity.py"
    print(json.dumps(result))


if __name__ == "__main__":
    main()
