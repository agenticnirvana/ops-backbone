"""Governance service — GitHub webhook ingest + promotion audit API.

GitHub org/repo stay placeholders (YOUR_GITHUB_ORG / YOUR_GITHUB_REPO) until wired.
The gateway UI also talks to the same Postgres tables via platform/shared/governance.py.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from shared.governance import (
    decide_promotion,
    ensure_governance_tables,
    github_config,
    ingest_github_event,
    list_audit,
    list_pipeline_runs,
    list_promotions,
    overview,
    request_promotion,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("governance")

WEBHOOK_TOKEN = os.getenv("GOVERNANCE_WEBHOOK_TOKEN", "")


class PromotionCreate(BaseModel):
    environment: str = "staging"
    requested_by: str
    reason: str = ""
    sha: str = ""
    eval_run_id: str | None = None


class PromotionDecide(BaseModel):
    approved: bool
    decided_by: str
    note: str = ""
    actor_role: str = "operator"


class PipelineIngest(BaseModel):
    workflow: str
    check_name: str
    conclusion: str
    triggered_by: str = "ci"
    summary: str = ""
    sha: str = ""
    branch: str = "main"
    details: dict[str, Any] = Field(default_factory=dict)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_governance_tables()
    logger.info("Governance service ready · github=%s/%s", github_config()["org"], github_config()["repo"])
    yield


app = FastAPI(title="AgentOps Governance", version="1.0.0", lifespan=lifespan)


def _check_webhook_token(authorization: str | None, x_governance_token: str | None) -> None:
    if not WEBHOOK_TOKEN:
        return
    bearer = (authorization or "").removeprefix("Bearer ").strip()
    token = x_governance_token or bearer
    if token != WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid governance webhook token")


@app.get("/health")
def health() -> dict[str, Any]:
    gh = github_config()
    return {"status": "ok", "github_wired": gh["wired"], "org": gh["org"], "repo": gh["repo"]}


@app.get("/v1/overview")
def get_overview() -> dict[str, Any]:
    return overview()


@app.get("/v1/pipelines")
def get_pipelines(limit: int = 30) -> dict[str, Any]:
    return {"runs": list_pipeline_runs(limit=limit)}


@app.get("/v1/promotions")
def get_promotions(limit: int = 20) -> dict[str, Any]:
    return {"promotions": list_promotions(limit=limit)}


@app.get("/v1/audit")
def get_audit(limit: int = 40) -> dict[str, Any]:
    return {"events": list_audit(limit=limit)}


@app.post("/v1/promotions")
def create_promotion(body: PromotionCreate) -> dict[str, Any]:
    return request_promotion(
        environment=body.environment,
        requested_by=body.requested_by,
        reason=body.reason,
        sha=body.sha,
        eval_run_id=body.eval_run_id,
    )


@app.post("/v1/promotions/{promotion_id}/decide")
def decide(promotion_id: str, body: PromotionDecide) -> dict[str, Any]:
    try:
        return decide_promotion(
            promotion_id=promotion_id,
            approved=body.approved,
            decided_by=body.decided_by,
            note=body.note,
            actor_role=body.actor_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v1/github/webhook")
def github_webhook(
    payload: dict[str, Any],
    authorization: str | None = Header(default=None),
    x_governance_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_webhook_token(authorization, x_governance_token)
    sender = ((payload.get("sender") or {}).get("login")) or "github"
    row = ingest_github_event(payload, triggered_by=sender)
    logger.info("Ingested GitHub event %s → %s", row.get("check_name"), row.get("conclusion"))
    return row


@app.post("/v1/pipelines")
def ingest_pipeline(
    body: PipelineIngest,
    authorization: str | None = Header(default=None),
    x_governance_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_webhook_token(authorization, x_governance_token)
    from shared.governance import record_pipeline_run

    return record_pipeline_run(
        workflow=body.workflow,
        check_name=body.check_name,
        conclusion=body.conclusion,
        triggered_by=body.triggered_by,
        source="ci",
        summary=body.summary,
        details=body.details,
        sha=body.sha,
        branch=body.branch,
    )
