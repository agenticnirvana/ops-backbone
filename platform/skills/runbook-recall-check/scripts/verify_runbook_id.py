#!/usr/bin/env python3
"""Verify runbook ID matches golden expectations (eval helper)."""

from __future__ import annotations

import json
import sys

GOLDEN = {
    "checkout-service": "checkout-redis-pool",
    "payment-api": "payment-api-high-cpu",
    "auth-service": "auth-jwt-validation",
}


def main() -> None:
    service = sys.argv[1] if len(sys.argv) > 1 else "checkout-service"
    runbook_id = sys.argv[2] if len(sys.argv) > 2 else ""
    expected = GOLDEN.get(service)
    match = bool(expected and runbook_id == expected)
    print(
        json.dumps(
            {
                "service": service,
                "runbook_id": runbook_id,
                "expected": expected,
                "match": match,
                "source": "skill-script:verify_runbook_id.py",
            }
        )
    )


if __name__ == "__main__":
    main()
