"""Skills catalog — agentregistry-backed with bundled SKILL.md + demo scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from shared import agentregistry_client as ar

LABEL_PREFIX = "design1.io/"
DEFAULT_NAMESPACE = os.getenv("AGENTREGISTRY_NAMESPACE", "design1")
SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"

DEFAULT_SKILLS: list[dict[str, Any]] = [
    {
        "slug": "checkout-redis-triage",
        "name": "Checkout Redis Pool Triage",
        "category": "triage",
        "description": "Heuristic triage for checkout Redis pool exhaustion using sample metrics + runbook mapping.",
        "scripts": ["check_redis_pool.py"],
        "when_to_use": "Teaching capstone pattern; offline checks before calling live MCP metrics.",
        "use_mcp_instead": "Production incident — call MCP get_metrics and query_logs on real Loki/Prometheus.",
        "related_mcp_tools": ["get_metrics", "retrieve_runbooks", "query_logs"],
    },
    {
        "slug": "severity-classifier",
        "name": "Severity Classifier",
        "category": "classification",
        "description": "Rule-based P1/P2/P3 mapping from alert text — deterministic eval baseline.",
        "scripts": ["classify_severity.py"],
        "when_to_use": "Golden-alert evals, fast pre-filter, CI regression without LLM.",
        "use_mcp_instead": "Ambiguous alerts needing log/metric context from live observability stack.",
        "related_mcp_tools": ["query_logs", "get_metrics"],
    },
    {
        "slug": "runbook-recall-check",
        "name": "Runbook Recall Check",
        "category": "evaluation",
        "description": "Assert retrieved runbook ID matches golden expectations per service.",
        "scripts": ["verify_runbook_id.py"],
        "when_to_use": "MLflow eval gate, RAG regression tests, pre-deploy confidence.",
        "use_mcp_instead": "Runtime RAG retrieval from Chroma during live triage.",
        "related_mcp_tools": ["retrieve_runbooks"],
    },
    {
        "slug": "hitl-approval-checklist",
        "name": "HITL Approval Checklist",
        "category": "guardrails",
        "description": "Operator checklist before approving destructive remediation — procedural knowledge only.",
        "scripts": [],
        "when_to_use": "Human-in-the-loop Simulation tab; training new operators.",
        "use_mcp_instead": "Creating tickets or executing remediation — MCP create_ticket after approve.",
        "related_mcp_tools": ["create_ticket"],
    },
]

_local_skills: dict[str, dict[str, Any]] = {}


def registry_backend() -> str:
    return "agentregistry" if _use_agentregistry() else "local-fallback"


def _use_agentregistry() -> bool:
    if not ar.AGENTREGISTRY_ENABLED:
        return False
    return ar.ping()


def _label(labels: dict[str, str] | None, key: str, default: str = "") -> str:
    if not labels:
        return default
    return labels.get(f"{LABEL_PREFIX}{key}", labels.get(key, default))


def _annotation(annotations: dict[str, str] | None, key: str, default: str = "") -> str:
    if not annotations:
        return default
    return annotations.get(f"{LABEL_PREFIX}{key}", annotations.get(key, default))


def _skill_dir(slug: str) -> Path:
    return SKILLS_ROOT / slug


def read_skill_markdown(slug: str) -> str:
    path = _skill_dir(slug) / "SKILL.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def list_skill_scripts(slug: str) -> list[str]:
    scripts_dir = _skill_dir(slug) / "scripts"
    if not scripts_dir.is_dir():
        return []
    return sorted(p.name for p in scripts_dir.glob("*.py"))


def _catalog_item(item: dict[str, Any]) -> dict[str, Any]:
    scripts = item.get("scripts") or list_skill_scripts(item["slug"])
    return {
        "slug": item["slug"],
        "name": item["name"],
        "category": item.get("category", "general"),
        "description": item.get("description", ""),
        "scripts": scripts,
        "when_to_use": item.get("when_to_use", ""),
        "use_mcp_instead": item.get("use_mcp_instead", ""),
        "related_mcp_tools": item.get("related_mcp_tools") or [],
        "has_skill_md": (_skill_dir(item["slug"]) / "SKILL.md").is_file(),
        "registry": "local-fallback",
    }


def _resource_to_skill(resource: dict[str, Any]) -> dict[str, Any]:
    meta = resource.get("metadata") or {}
    spec = resource.get("spec") or {}
    labels = meta.get("labels") or {}
    annotations = meta.get("annotations") or {}
    slug = meta.get("name") or ""
    scripts_raw = _annotation(annotations, "scripts")
    scripts = [s.strip() for s in scripts_raw.split(",") if s.strip()] if scripts_raw else list_skill_scripts(slug)
    mcp_tools_raw = _annotation(annotations, "related-mcp-tools")
    return {
        "slug": slug,
        "name": spec.get("title") or slug.replace("-", " ").title(),
        "category": _label(labels, "category", "general"),
        "description": spec.get("description") or "",
        "scripts": scripts,
        "when_to_use": _annotation(annotations, "when-to-use"),
        "use_mcp_instead": _annotation(annotations, "use-mcp-instead"),
        "related_mcp_tools": [t.strip() for t in mcp_tools_raw.split(",") if t.strip()] if mcp_tools_raw else [],
        "has_skill_md": (_skill_dir(slug) / "SKILL.md").is_file(),
        "registry": "agentregistry",
        "namespace": meta.get("namespace") or DEFAULT_NAMESPACE,
        "tag": meta.get("tag") or "latest",
    }


def _yaml_map_block(key: str, values: dict[str, str]) -> str:
    if not values:
        return f"  {key}: {{}}"
    lines = [f"  {key}:"]
    for map_key, value in sorted(values.items()):
        safe = str(value).replace('"', '\\"')
        lines.append(f'    {map_key}: "{safe}"')
    return "\n".join(lines)


def _item_to_yaml(item: dict[str, Any], *, namespace: str = DEFAULT_NAMESPACE) -> str:
    scripts = item.get("scripts") or []
    mcp_tools = item.get("related_mcp_tools") or []
    labels = {
        f"{LABEL_PREFIX}category": item.get("category", "general"),
        f"{LABEL_PREFIX}builtin": "true",
    }
    annotations = {
        f"{LABEL_PREFIX}scripts": ",".join(scripts),
        f"{LABEL_PREFIX}when-to-use": item.get("when_to_use", ""),
        f"{LABEL_PREFIX}use-mcp-instead": item.get("use_mcp_instead", ""),
        f"{LABEL_PREFIX}related-mcp-tools": ",".join(mcp_tools),
        f"{LABEL_PREFIX}skill-path": item["slug"],
    }
    desc = (item.get("description") or "").replace('"', '\\"')
    title = item["name"].replace('"', '\\"')
    return f"""apiVersion: ar.dev/v1alpha1
kind: Skill
metadata:
  name: {item["slug"]}
  namespace: {namespace}
  tag: latest
{_yaml_map_block("labels", labels)}
{_yaml_map_block("annotations", annotations)}
spec:
  title: "{title}"
  description: "{desc}"
"""


def build_skills_yaml(*, namespace: str = DEFAULT_NAMESPACE) -> str:
    docs = [_item_to_yaml(item, namespace=namespace) for item in DEFAULT_SKILLS]
    return "---\n".join(docs) + "\n"


def _fetch_from_agentregistry() -> list[dict[str, Any]]:
    items = [_resource_to_skill(r) for r in ar.list_skills()]
    items.sort(key=lambda s: (s["category"], s["name"]))
    return items


def seed_skills_registry() -> None:
    if not _use_agentregistry():
        for item in DEFAULT_SKILLS:
            slug = item["slug"]
            if slug not in _local_skills:
                _local_skills[slug] = _catalog_item(item)
        return
    try:
        existing = {s["slug"] for s in _fetch_from_agentregistry()}
    except Exception:
        existing = set()
    missing = [item for item in DEFAULT_SKILLS if item["slug"] not in existing]
    if not missing:
        return
    ar.apply_yaml(build_skills_yaml())


def list_skills(*, category: str | None = None) -> list[dict[str, Any]]:
    seed_skills_registry()
    if not _use_agentregistry():
        items = list(_local_skills.values()) or [_catalog_item(i) for i in DEFAULT_SKILLS]
    else:
        items = _fetch_from_agentregistry()
    if category:
        items = [s for s in items if s["category"] == category]
    return items


def get_skill(slug: str) -> dict[str, Any] | None:
    seed_skills_registry()
    if not _use_agentregistry():
        if slug in _local_skills:
            skill = dict(_local_skills[slug])
        else:
            match = next((i for i in DEFAULT_SKILLS if i["slug"] == slug), None)
            if not match:
                return None
            skill = _catalog_item(match)
    else:
        resource = ar.get_skill(slug)
        if not resource:
            return None
        skill = _resource_to_skill(resource)
    skill["skill_md"] = read_skill_markdown(slug)
    skill["script_files"] = list_skill_scripts(slug)
    return skill


def mcp_vs_skills_guide() -> dict[str, Any]:
    return {
        "summary": "MCP = live tools with side effects · Skills = packaged knowledge + optional scripts",
        "mcp": {
            "what": "Model Context Protocol servers expose callable tools over HTTP/stdio (query_logs, get_metrics, create_ticket).",
            "when": [
                "Agent must read live Loki/Prometheus/Chroma at runtime",
                "Side effects after HITL (tickets, webhooks)",
                "Shared tool farm across teams with auth at the MCP edge",
            ],
            "design1": "Ops MCP Server on :8081 — Basic Auth, Playground Inspector, MCP agent mode.",
        },
        "skills": {
            "what": "SKILL.md + optional scripts — procedural knowledge, eval helpers, checklists stored in agentregistry.",
            "when": [
                "Teach procedures and golden-alert evals without network calls",
                "Deterministic scripts for CI/MLflow gates",
                "Operator checklists (HITL) with no API surface",
            ],
            "design1": f"{len(DEFAULT_SKILLS)} skills in namespace design1 — bundled under platform/skills/.",
        },
        "decision_matrix": [
            {"scenario": "Fetch live error logs", "use": "MCP", "tool": "query_logs"},
            {"scenario": "Classify alert text in CI eval", "use": "Skill", "tool": "severity-classifier"},
            {"scenario": "Retrieve runbook chunks at runtime", "use": "MCP", "tool": "retrieve_runbooks"},
            {"scenario": "Verify runbook ID in golden test", "use": "Skill", "tool": "runbook-recall-check"},
            {"scenario": "Operator approval checklist", "use": "Skill", "tool": "hitl-approval-checklist"},
            {"scenario": "Open ticket after HITL", "use": "MCP", "tool": "create_ticket"},
        ],
    }


def run_skill_script(slug: str, script: str, params: list[str] | None = None) -> dict[str, Any]:
    skill = get_skill(slug)
    if not skill:
        raise ValueError(f"Unknown skill: {slug}")
    allowed = set(skill.get("scripts") or []) | set(skill.get("script_files") or [])
    if script not in allowed:
        raise ValueError(f"Script not allowed for skill {slug}: {script}")

    script_path = _skill_dir(slug) / "scripts" / script
    if not script_path.is_file():
        raise ValueError(f"Script missing on disk: {script}")

    argv = [sys.executable, str(script_path), *(params or [])]
    env = os.environ.copy()
    env.setdefault(
        "METRICS_FIXTURE",
        str(Path(__file__).resolve().parents[2] / "agent" / "sample_data" / "metrics" / "services.json"),
    )
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    parsed: Any = stdout
    try:
        parsed = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        parsed = {"output": stdout}

    return {
        "slug": slug,
        "script": script,
        "exit_code": proc.returncode,
        "result": parsed,
        "stderr": stderr or None,
    }
