#!/usr/bin/env python3
"""Demo script — inspect sample metrics for Redis pool pressure (read-only)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    service = sys.argv[1] if len(sys.argv) > 1 else "checkout-service"
    fixture = Path(
        os.getenv(
            "METRICS_FIXTURE",
            str(Path(__file__).resolve().parents[4] / "agent" / "sample_data" / "metrics" / "services.json"),
        )
    )
    data: dict = {}
    if fixture.is_file():
        data = json.loads(fixture.read_text(encoding="utf-8")).get(service, {})

    cpu = float(data.get("cpu_percent", 0))
    errors = float(data.get("error_rate_5m", 0))
    exhausted = service == "checkout-service" and (errors >= 0.05 or cpu >= 70)

    print(
        json.dumps(
            {
                "service": service,
                "cpu_percent": cpu,
                "error_rate_5m": errors,
                "redis_pool_exhausted": exhausted,
                "suggested_runbook": "checkout-redis-pool" if exhausted else None,
                "source": "skill-script:check_redis_pool.py",
            }
        )
    )


if __name__ == "__main__":
    main()
