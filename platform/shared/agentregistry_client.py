"""HTTP client for agentregistry (https://github.com/agentregistry-dev/agentregistry)."""

from __future__ import annotations

import os
from typing import Any

import httpx

AGENTREGISTRY_URL = os.getenv("AGENTREGISTRY_URL", "http://agentregistry:8080").rstrip("/")
AGENTREGISTRY_NAMESPACE = os.getenv("AGENTREGISTRY_NAMESPACE", "design1")
AGENTREGISTRY_ENABLED = os.getenv("AGENTREGISTRY_ENABLED", "true").lower() in {"1", "true", "yes"}
AGENTREGISTRY_API_TOKEN = os.getenv("AGENTREGISTRY_API_TOKEN", "")
LABEL_PREFIX = "design1.io/"


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if AGENTREGISTRY_API_TOKEN:
        headers["Authorization"] = f"Bearer {AGENTREGISTRY_API_TOKEN}"
    return headers


def _client(timeout: float = 20.0) -> httpx.Client:
    return httpx.Client(timeout=timeout, headers=_headers())


def ping() -> bool:
    try:
        with _client(timeout=5.0) as client:
            resp = client.get(f"{AGENTREGISTRY_URL}/v0/ping")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


def list_agents(*, namespace: str | None = None, latest_only: bool = True) -> list[dict[str, Any]]:
    params: dict[str, str | int | bool] = {
        "namespace": namespace or AGENTREGISTRY_NAMESPACE,
        "limit": 100,
        "latestOnly": latest_only,
    }
    with _client() as client:
        resp = client.get(f"{AGENTREGISTRY_URL}/v0/agents", params=params)
        resp.raise_for_status()
        return resp.json().get("items") or []


def list_mcp_servers(*, namespace: str | None = None, latest_only: bool = True) -> list[dict[str, Any]]:
    params: dict[str, str | int | bool] = {
        "namespace": namespace or AGENTREGISTRY_NAMESPACE,
        "limit": 100,
        "latestOnly": latest_only,
    }
    with _client() as client:
        resp = client.get(f"{AGENTREGISTRY_URL}/v0/mcpservers", params=params)
        resp.raise_for_status()
        return resp.json().get("items") or []


def list_skills(*, namespace: str | None = None, latest_only: bool = True) -> list[dict[str, Any]]:
    params: dict[str, str | int | bool] = {
        "namespace": namespace or AGENTREGISTRY_NAMESPACE,
        "limit": 100,
        "latestOnly": latest_only,
    }
    with _client() as client:
        resp = client.get(f"{AGENTREGISTRY_URL}/v0/skills", params=params)
        resp.raise_for_status()
        return resp.json().get("items") or []


def get_agent(name: str, *, namespace: str | None = None) -> dict[str, Any] | None:
    ns = namespace or AGENTREGISTRY_NAMESPACE
    with _client() as client:
        resp = client.get(f"{AGENTREGISTRY_URL}/v0/agents/{name}", params={"namespace": ns})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


def get_mcp_server(name: str, *, namespace: str | None = None) -> dict[str, Any] | None:
    ns = namespace or AGENTREGISTRY_NAMESPACE
    with _client() as client:
        resp = client.get(f"{AGENTREGISTRY_URL}/v0/mcpservers/{name}", params={"namespace": ns})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


def get_skill(name: str, *, namespace: str | None = None) -> dict[str, Any] | None:
    ns = namespace or AGENTREGISTRY_NAMESPACE
    with _client() as client:
        resp = client.get(f"{AGENTREGISTRY_URL}/v0/skills/{name}", params={"namespace": ns})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


def apply_yaml(yaml_body: str, *, dry_run: bool = False) -> dict[str, Any]:
    params = {"dryRun": "true"} if dry_run else {}
    with _client(timeout=60.0) as client:
        resp = client.post(
            f"{AGENTREGISTRY_URL}/v0/apply",
            params=params,
            content=yaml_body,
            headers={**_headers(), "Content-Type": "application/yaml"},
        )
        resp.raise_for_status()
        return resp.json()
