"""Per-design Langfuse API keys (same mapping as platform/shared/design_stack.py)."""

from __future__ import annotations

import os


def normalize_design_id(design_id: str | None) -> str:
    raw = (design_id or os.getenv("ARCH_DESIGN_ID") or "d2").strip().lower()
    if raw in ("1", "design-1", "design1"):
        return "d1"
    if raw in ("2", "design-2", "design2"):
        return "d2"
    if raw in ("3", "design-3", "design3"):
        return "d3"
    return raw if raw in ("d1", "d2", "d3") else "d2"


def langfuse_keys(design_id: str | None = None) -> tuple[str, str]:
    did = normalize_design_id(design_id).upper()
    pk = os.getenv(f"LANGFUSE_{did}_PUBLIC_KEY") or os.getenv("LANGFUSE_PUBLIC_KEY") or ""
    sk = os.getenv(f"LANGFUSE_{did}_SECRET_KEY") or os.getenv("LANGFUSE_SECRET_KEY") or ""
    return pk, sk
