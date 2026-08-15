"""Platform configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
DESIGN_ROOT = PLATFORM_ROOT.parent
AGENT_ROOT = DESIGN_ROOT / "agent"

# Allow imports from the Design 1 agent package in gateway and multi-agent graphs.
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

MOCK_LLM = os.getenv("MOCK_LLM", "true").lower() == "true"
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8081/mcp")
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "1.0.0")
INDEX_VERSION = os.getenv("INDEX_VERSION", "runbooks-local")
INGESTION_URL = os.getenv("INGESTION_URL", "http://localhost:8092")
INGESTION_API_TOKEN = os.getenv("INGESTION_API_TOKEN", "design1-ingestion-token-change-me")
TICKET_API_URL = os.getenv("TICKET_API_URL", "http://localhost:8091")
AGENT_URL = os.getenv("AGENT_URL", "http://agent:8000").rstrip("/")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
PLATFORM_PUBLIC_URL = os.getenv("PLATFORM_PUBLIC_URL", "http://localhost:8080")
