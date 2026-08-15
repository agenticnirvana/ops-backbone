CREATE DATABASE langfuse;

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY,
    job_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    triggered_by VARCHAR(128) NOT NULL DEFAULT 'system',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    index_version VARCHAR(64),
    documents_indexed INT DEFAULT 0,
    runbooks_changed INT DEFAULT 0,
    drive_files_synced INT DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS runbook_sources (
    source_key VARCHAR(512) PRIMARY KEY,
    source_type VARCHAR(32) NOT NULL,
    file_name VARCHAR(256) NOT NULL,
    remote_modified_at TIMESTAMPTZ,
    content_hash VARCHAR(64),
    local_path VARCHAR(512),
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs (status, started_at DESC);

CREATE TABLE IF NOT EXISTS agent_runs (
    id VARCHAR(36) PRIMARY KEY,
    thread_id VARCHAR(64) NOT NULL UNIQUE,
    mode VARCHAR(32) NOT NULL DEFAULT 'standalone',
    domain VARCHAR(32) NOT NULL DEFAULT 'sre',
    service VARCHAR(128),
    severity VARCHAR(16),
    status VARCHAR(32) NOT NULL,
    runbook_id VARCHAR(128),
    triggered_by VARCHAR(128),
    source VARCHAR(64),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    duration_seconds INT,
    hitl_required BOOLEAN NOT NULL DEFAULT FALSE,
    ticket_id VARCHAR(64),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs (status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_severity ON agent_runs (severity, status);

CREATE TABLE IF NOT EXISTS metric_snapshots (
    id SERIAL PRIMARY KEY,
    captured_at TIMESTAMPTZ NOT NULL,
    active_pipelines INT NOT NULL,
    p1_alerts INT NOT NULL,
    agents_online INT NOT NULL,
    success_rate_pct NUMERIC(5, 2) NOT NULL,
    mttr_seconds INT
);

CREATE INDEX IF NOT EXISTS idx_metric_snapshots_captured ON metric_snapshots (captured_at DESC);

CREATE TABLE IF NOT EXISTS opa_evaluations (
    id VARCHAR(36) PRIMARY KEY,
    evaluated_at TIMESTAMPTZ NOT NULL,
    allowed BOOLEAN NOT NULL,
    reason VARCHAR(64) NOT NULL,
    matched_rule VARCHAR(64) NOT NULL,
    destructive BOOLEAN NOT NULL DEFAULT FALSE,
    service VARCHAR(128),
    severity VARCHAR(16),
    recommendation TEXT NOT NULL,
    thread_id VARCHAR(64),
    evaluated_by VARCHAR(128),
    source VARCHAR(32) NOT NULL DEFAULT 'ui_preview'
);

CREATE INDEX IF NOT EXISTS idx_opa_evaluations_at ON opa_evaluations (evaluated_at DESC);
CREATE INDEX IF NOT EXISTS idx_opa_evaluations_verdict ON opa_evaluations (allowed, evaluated_at DESC);

CREATE TABLE IF NOT EXISTS opa_policy_revisions (
    id VARCHAR(36) PRIMARY KEY,
    saved_at TIMESTAMPTZ NOT NULL,
    saved_by VARCHAR(128) NOT NULL,
    rego TEXT NOT NULL,
    note VARCHAR(256)
);

CREATE INDEX IF NOT EXISTS idx_opa_policy_revisions_at ON opa_policy_revisions (saved_at DESC);
