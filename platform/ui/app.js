const API = '';
const GRAPH_STEPS = [
  { id: 'classify', label: 'classify', icon: 'classify', sub: 'Intent classified', result: (d) => (d.classification ? 'Service Degradation' : '—') },
  { id: 'retrieve_runbook', label: 'retrieve_runbook', icon: 'retrieve_runbook', sub: 'Runbook retrieved', result: (d) => (d.runbook_id || '—') },
  { id: 'query_logs', label: 'query_logs', icon: 'query_logs', sub: 'Relevant logs found', result: () => '128 entries' },
  { id: 'query_metrics', label: 'query_metrics', icon: 'query_metrics', sub: 'Metrics anomaly', result: () => 'p95 latency spike' },
  { id: 'recommend', label: 'recommend', icon: 'recommend', sub: 'Recommendations ready', result: (d) => (d.recommendation ? '3 actions' : '—') },
  { id: 'hitl_gate', label: 'hitl_gate', icon: 'hitl_gate', sub: 'Human approval', result: (d) => (d.status === 'awaiting_hitl' ? 'Awaiting approval' : 'Cleared') },
];

const MULTI_GRAPH_STEPS = [
  { id: 'supervisor', label: 'supervisor', icon: 'sparkles', sub: 'Orchestrator routing', result: (d) => (d.route ? d.route.replace('supervisor:', '') : 'full_pipeline') },
  { id: 'triage_worker', label: 'triage_worker', icon: 'classify', sub: 'Alert classified', result: (d) => (d.classification || '—') },
  { id: 'runbook_worker', label: 'runbook_worker', icon: 'retrieve_runbook', sub: 'Runbook RAG', result: (d) => (d.runbook_id || '—') },
  { id: 'logs_worker', label: 'logs_worker', icon: 'query_logs', sub: 'Loki investigation', result: () => 'Log patterns found' },
  { id: 'metrics_worker', label: 'metrics_worker', icon: 'query_metrics', sub: 'Prometheus metrics', result: () => 'Anomaly confirmed' },
  { id: 'remediation_worker', label: 'remediation_worker', icon: 'recommend', sub: 'Remediation plan', result: (d) => (d.recommendation ? 'Plan ready' : '—') },
  { id: 'hitl_gate', label: 'hitl_gate', icon: 'hitl_gate', sub: 'Human approval', result: (d) => (d.status === 'awaiting_hitl' ? 'Awaiting approval' : 'Cleared') },
  { id: 'incident_worker', label: 'incident_worker', icon: 'actions', sub: 'Ticket created', result: (d) => (d.ticket?.ticket_id || d.ticket?.status || '—') },
];

const MCP_GRAPH_STEPS = [
  { id: 'classify', label: 'classify', icon: 'classify', sub: 'Intent classified', result: (d) => (d.classification || '—') },
  { id: 'retrieve', label: 'retrieve_runbooks', icon: 'retrieve_runbook', sub: 'MCP · retrieve_runbooks', result: (d) => (d.runbook_id || '—') },
  { id: 'metrics', label: 'query_tools', icon: 'query_metrics', sub: 'MCP · get_metrics + query_logs', result: () => 'Tools invoked' },
  { id: 'recommend', label: 'recommend', icon: 'recommend', sub: 'Recommendations ready', result: (d) => (d.recommendation ? '3 actions' : '—') },
  { id: 'hitl', label: 'hitl_gate', icon: 'hitl_gate', sub: 'Human approval', result: (d) => (d.status === 'awaiting_hitl' ? 'Awaiting approval' : 'Cleared') },
  { id: 'execute', label: 'create_ticket', icon: 'actions', sub: 'MCP · create_ticket', result: (d) => (d.ticket?.ticket_id || d.ticket?.status || '—') },
];

const ORCH_WORKERS = [
  { id: 'triage_worker', label: 'Triage', role: 'Classify severity' },
  { id: 'runbook_worker', label: 'Runbook', role: 'Chroma RAG' },
  { id: 'logs_worker', label: 'Logs', role: 'Loki query' },
  { id: 'metrics_worker', label: 'Metrics', role: 'Prometheus' },
  { id: 'remediation_worker', label: 'Remediation', role: 'LLM plan' },
  { id: 'incident_worker', label: 'Incident', role: 'Ticket API' },
];

const MULTI_AGENT_TREE = [
  { id: 'supervisor', label: 'Supervisor', role: 'Orchestrator · routes delegation', icon: 'sparkles', kind: 'orchestrator' },
  { id: 'triage_worker', label: 'Triage Worker', role: 'Classify severity · set HITL flag', icon: 'classify', kind: 'worker' },
  { id: 'runbook_worker', label: 'Runbook Worker', role: 'Chroma RAG retrieval', icon: 'retrieve_runbook', kind: 'worker' },
  { id: 'logs_worker', label: 'Logs Worker', role: 'Loki error patterns', icon: 'query_logs', kind: 'worker' },
  { id: 'metrics_worker', label: 'Metrics Worker', role: 'Prometheus CPU / latency', icon: 'query_metrics', kind: 'worker' },
  { id: 'remediation_worker', label: 'Remediation Worker', role: 'LLM action plan', icon: 'recommend', kind: 'worker' },
  { id: 'hitl_gate', label: 'HITL Gate', role: 'Human approval (conditional)', icon: 'hitl_gate', kind: 'gate', branch: true },
  { id: 'incident_worker', label: 'Incident Worker', role: 'Ticket API · execute', icon: 'actions', kind: 'worker' },
];

const MCP_ARCH_TREE = {
  id: 'mcp-agent', label: 'MCP Agent Runner', role: 'LangGraph orchestrator', icon: 'sparkles', kind: 'orchestrator',
  children: [{
    id: 'mcp-http', label: 'HTTP Client', role: 'httpx · Basic Auth', kind: 'transport',
    children: [{
      id: 'mcp-server', label: 'Ops MCP Server', role: 'FastAPI :8081', kind: 'host',
      children: [
        { id: 'tool-logs', label: 'query_logs', role: '→ Loki', kind: 'tool' },
        { id: 'tool-runbooks', label: 'retrieve_runbooks', role: '→ Chroma RAG', kind: 'tool' },
        { id: 'tool-metrics', label: 'get_metrics', role: '→ Prometheus', kind: 'tool' },
        { id: 'tool-ticket', label: 'create_ticket', role: '→ Ticket API', kind: 'tool' },
      ],
    }],
  }],
};

const MCP_TOOL_META = {
  query_logs: { backend: 'Loki', desc: 'Fetch error log lines for the alert service' },
  retrieve_runbooks: { backend: 'Chroma', desc: 'Vector search over ingested runbooks' },
  get_metrics: { backend: 'Prometheus', desc: 'CPU, p95 latency, error rate' },
  create_ticket: { backend: 'Ticket API', desc: 'Create remediation ticket after HITL' },
  check_opa_policy: { backend: 'OPA', desc: 'Evaluate recommendation against Rego policy' },
  list_policy_rules: { backend: 'OPA', desc: 'List Design 1 guardrail rules' },
  preview_hitl_gate: { backend: 'OPA + HITL', desc: 'Preview whether HITL would pause the graph' },
  list_runbooks: { backend: 'Filesystem', desc: 'Catalog markdown runbooks on disk' },
  get_runbook_by_id: { backend: 'Filesystem', desc: 'Fetch a runbook snippet by ID' },
};

const MULTI_DELEGATION_PREVIEW = [
  { from: 'supervisor', to: 'triage_worker', message: 'Delegate classification for alert' },
  { from: 'triage_worker', to: 'runbook_worker', message: 'Fetch runbook context via Chroma RAG' },
  { from: 'runbook_worker', to: 'logs_worker', message: 'Investigate logs in Loki' },
  { from: 'logs_worker', to: 'metrics_worker', message: 'Pull Prometheus metrics for anomaly confirmation' },
  { from: 'metrics_worker', to: 'remediation_worker', message: 'Synthesize remediation plan from runbook + observability' },
  { from: 'remediation_worker', to: 'hitl_gate', message: 'Route to HITL or ticket creation' },
];

const MCP_TOOL_PREVIEW = [
  { tool: 'retrieve_runbooks', transport: 'mcp_http', input: { query: 'checkout-service redis pool', top_k: 3 }, summary: 'invoking…' },
  { tool: 'get_metrics', transport: 'mcp_http', input: { service: 'checkout-service' }, summary: 'invoking…' },
  { tool: 'query_logs', transport: 'mcp_http', input: { service: 'checkout-service', limit: 5 }, summary: 'invoking…' },
  { tool: 'create_ticket', transport: 'mcp_http', input: { service: 'checkout-service', severity: 'P1' }, summary: 'pending HITL…' },
];

const SECTION_ICONS = {
  operations: 'operations',
  simulation: 'automation',
  guardrails: 'guardrails',
  ingestion: 'ingestion',
  learning: 'learning',
  observability: 'observability',
  evaluation: 'evaluation',
  actions: 'actions',
  admin: 'admin',
  mcp: 'evaluation',
};

const MCP_PLAYGROUND_STORAGE = 'agentops-mcp-custom-servers';
const MCP_PLAYGROUND_CREDS = 'agentops-mcp-session-creds';

const SECTIONS = {
  operations: {
    title: 'Operations',
    subtitle: 'Simulate production alerts · LangGraph agent triage',
    breadcrumb: 'Platform › Operations',
    tabs: [
      { id: 'ops-incident', label: 'Incident' },
      { id: 'ops-pipeline', label: 'Agent Run' },
      { id: 'ops-multi', label: 'Multi-Agent Flow' },
      { id: 'ops-mcp', label: 'MCP Server' },
      { id: 'ops-response', label: 'Response JSON' },
    ],
  },
  mcp: {
    title: 'MCP & Skills',
    subtitle: 'MCP Inspector · agentregistry skills · when to use each',
    breadcrumb: 'Platform › MCP & Skills',
    tabs: [
      { id: 'mcp-playground', label: 'MCP Inspector' },
      { id: 'mcp-skills', label: 'Skills Catalog' },
      { id: 'mcp-vs-skills', label: 'MCP vs Skills' },
    ],
    onEnter: () => {
      if (currentTab === 'mcp-skills') initSkillsCatalog();
      else if (currentTab === 'mcp-vs-skills') renderMcpVsSkillsGuide();
      else initMcpPlayground();
    },
  },
  simulation: {
    title: 'Simulation',
    subtitle: 'Simulated alert remediation · OPA policy · HITL gate',
    breadcrumb: 'Platform › Simulation › HITL Review',
    tabs: [
      { id: 'auto-change', label: 'HITL Review' },
      { id: 'auto-opa', label: 'OPA Policy' },
      { id: 'auto-history', label: 'History' },
      { id: 'auto-logs', label: 'Logs' },
    ],
    onEnter: () => { if (lastOpaEvaluation) renderOpaPanel(lastOpaEvaluation); },
  },
  guardrails: {
    title: 'Guardrails',
    subtitle: 'OPA policy console · audit log · live Rego editor',
    breadcrumb: 'Platform › Guardrails › Policy Overview',
    tabs: [
      { id: 'grd-overview', label: 'Policy Overview' },
      { id: 'grd-audit', label: 'Audit Log' },
      { id: 'grd-editor', label: 'Policy Editor' },
    ],
    onEnter: () => loadGuardrailsSection(currentTab),
  },
  ingestion: {
    title: 'Ingestion',
    subtitle: 'Runbook pipeline · Drive sync · Chroma reindex',
    breadcrumb: 'Platform › Ingestion',
    tabs: [
      { id: 'ing-pipeline', label: 'Pipeline' },
      { id: 'ing-status', label: 'Status & Actions' },
      { id: 'ing-jobs', label: 'Chroma Explorer' },
    ],
    onEnter: () => loadIngestStatus(),
  },
  learning: {
    title: 'Learning',
    subtitle: 'Notebook · hardcover · Kindle · Stories',
    breadcrumb: 'Platform › Learning › Notebook',
    tabs: [
      { id: 'learn-notebook', label: 'Notebook' },
      { id: 'learn-designs', label: 'Designs' },
      { id: 'learn-bookmarks', label: 'Bookmarks' },
      { id: 'learn-notes', label: 'Notes' },
      { id: 'learn-highlights', label: 'Highlights' },
    ],
    onEnter: () => initLearningSection(currentTab),
  },
  observability: {
    title: 'Observability',
    subtitle: 'Full alert journey · signals → Chroma RAG → OPA → HITL',
    breadcrumb: 'Platform › Observability',
    tabs: [
      { id: 'obs-simulator', label: 'Alert Flow' },
      { id: 'obs-alert', label: 'Alerts' },
      { id: 'obs-logs', label: 'Logs' },
      { id: 'obs-metrics', label: 'Metrics' },
    ],
    onEnter: () => loadAlertFlowCatalog(),
  },
  evaluation: {
    title: 'Evaluation',
    subtitle: 'Langfuse analytics · traces · MLflow eval gate',
    breadcrumb: 'Platform › Evaluation',
    tabs: [
      { id: 'eval-analytics', label: 'Agent Analytics' },
      { id: 'eval-trace', label: 'Langfuse Trace' },
      { id: 'eval-gate', label: 'Eval & Scores' },
      { id: 'eval-tools', label: 'External Tools' },
    ],
    onEnter: () => {
      loadLangfuseDashboard();
      loadEvalDashboard();
      if (lastThreadId) updateTraceLinks(lastThreadId);
    },
  },
  governance: {
    title: 'Governance',
    subtitle: 'CI checks · eval gate · promotions · four-eyes',
    breadcrumb: 'Platform › Governance',
    tabs: [
      { id: 'gov-overview', label: 'Overview' },
      { id: 'gov-pipelines', label: 'Pipelines' },
      { id: 'gov-promotions', label: 'Promotions' },
      { id: 'gov-controls', label: 'Controls' },
      { id: 'gov-github', label: 'GitHub' },
    ],
    onEnter: () => loadGovernanceSection(currentTab),
  },
  actions: {
    title: 'Actions',
    subtitle: 'Remediation tickets after HITL approval',
    breadcrumb: 'Platform › Actions › Tickets',
    tabs: [
      { id: 'act-detail', label: 'Record' },
      { id: 'act-list', label: 'All Tickets' },
    ],
    onEnter: () => loadTickets(),
  },
  admin: {
    title: 'Admin',
    subtitle: 'Platform overview · user directory · audit activity',
    breadcrumb: 'Platform › Admin › Overview',
    tabs: [
      { id: 'adm-overview', label: 'Overview' },
      { id: 'adm-agents', label: 'Agent Registry' },
      { id: 'adm-users', label: 'Users' },
      { id: 'adm-activity', label: 'Activity' },
    ],
    onEnter: () => loadAdminSection(currentTab),
  },
};

const RUNBOOK_UI = {};

function getActiveScenario() {
  return scenarios[activeScenarioIndex] || null;
}

function scenarioByRunbookId(runbookId) {
  return scenarios.find((s) => s.runbook_id === runbookId) || null;
}

function renderScenarioOverview(scenario) {
  const dash = $('scenario-dashboard');
  if (!scenario || !dash) return;
  const p = scenario.payload || {};
  $('sc-title').textContent = scenario.label || 'Scenario overview';
  $('sc-summary').textContent = scenario.summary || p.error_summary || '—';
  $('sc-service').textContent = p.service || '—';
  $('sc-dependency').textContent = scenario.dependency || '—';
  $('sc-blast').textContent = scenario.blast_radius || '—';
  $('sc-runbook-file').textContent = `${scenario.runbook_id || '—'}.md`;
  const vector = (typeof getArchDesign === 'function' && getArchDesign().vector) || 'Chroma';
  $('sc-rationale').textContent = `Runbook ${scenario.runbook_id} will be retrieved via ${vector} RAG when the pipeline runs.`;

  const sevBadge = $('sc-severity-badge');
  if (sevBadge) {
    sevBadge.textContent = p.severity || 'P1';
    sevBadge.className = `badge ${p.severity === 'P2' ? 'p2' : 'p1'}`;
  }
  const rbBadge = $('sc-runbook-badge');
  if (rbBadge) rbBadge.textContent = scenario.runbook_id || '—';

  const plan = scenario.plan || [];
  $('sc-plan').innerHTML = plan.length
    ? plan.map((c) => `<li>${c}</li>`).join('')
    : '<li class="muted">Plan populated after agent retrieves runbook</li>';

  const sections = scenario.runbook_sections || [];
  $('sc-runbook-sections').innerHTML = sections.map((s) => `<li>${s}</li>`).join('');
  const tags = scenario.tags || [];
  $('sc-runbook-tags').innerHTML = tags.map((t) => `<span>${t}</span>`).join('');

  dash.classList.remove('scenario-reveal');
  void dash.offsetWidth;
  dash.classList.add('scenario-reveal');
}

function renderLogPreview(logText, containerId = 'cr-log-preview') {
  const el = $(containerId);
  if (!el) return;
  const lines = (logText || '').split('\n').filter(Boolean);
  if (!lines.length) {
    el.innerHTML = '<div class="log-line muted">No log snippet for this scenario.</div>';
    return;
  }
  el.innerHTML = lines.map((line) => {
    const tsMatch = line.match(/^(\d{4}-\d{2}-\d{2}T[\d:]+Z)\s+(\w+)\s+/);
    const level = (tsMatch?.[2] || 'info').toLowerCase();
    const cls = level.includes('error') ? 'error' : level.includes('warn') ? 'warn' : 'info';
    const body = tsMatch ? line.slice(tsMatch[0].length) : line;
    const shortTs = tsMatch ? tsMatch[1].slice(11, 19) : '—';
    return `<div class="log-line ${cls}"><span class="log-ts">${shortTs}</span> ${escapeHtml(body)}</div>`;
  }).join('');
}

let token = localStorage.getItem('aiops_token');
let currentUser = null;
let userMenuOpen = false;
let admUserEditEmail = '';
let currentMode = 'standalone';
let agentModesCache = [];
let mcpRuntimeConfig = null;
let mcpPlaygroundState = {
  servers: [],
  customServers: [],
  activeServerId: null,
  sessions: {},
  selectedTool: null,
  invokeHistory: [],
};
let lastPipelineResult = null;
let currentDomain = 'sre';
let currentSection = 'operations';
let currentTab = 'ops-incident';
let pendingThread = null;
let pendingMode = null;
let pendingDomain = null;
let pendingChangeRun = null;
let hitlResolved = false;
let opaEvalSeq = 0;
let hitlHistoryFilter = '';
let scenarios = [];
let activeScenarioIndex = 0;
let pipelineStart = null;
let timerInterval = null;
let observabilityLinks = {};
let selectedTicket = null;
let lastOpaEvaluation = null;
let opaPolicyLoaded = false;
let grdAuditVerdict = '';
let grdPolicyDraft = '';
let notifications = [];
let notifPanelOpen = false;

const NOTIF_ICONS = { success: '✓', error: '✕', warning: '!', info: 'i' };

const FLOW_NODES = [
  { id: 'ingestion', label: 'Ingestion', color: 'blue' },
  { id: 'triage', label: 'Triage', color: 'indigo' },
  { id: 'investigation', label: 'Investigation', color: 'cyan' },
  { id: 'hitl', label: 'HITL', color: 'orange' },
  { id: 'remediation', label: 'Remediation', color: 'green' },
];

let DASHBOARD_STATS = {
  pipelines: 0,
  alerts: 0,
  agents: 0,
  success: '—',
  mttr: '—',
  trends: {
    pipelines: '—',
    alerts: '—',
    agents: '—',
    success: '—',
    mttr: '—',
  },
};

let pipelineAnimToken = 0;

const TOOL_TILES = [
  { id: 'link-grafana', key: 'grafana', label: 'Grafana' },
  { id: 'link-prometheus', key: 'prometheus', label: 'Prometheus' },
  { id: 'link-langfuse', key: 'langfuse', label: 'Langfuse' },
  { id: 'link-mlflow', key: 'mlflow', label: 'MLflow' },
];

const $ = (id) => document.getElementById(id);

function show(el) { if (el) el.classList.remove('hidden'); }
function hide(el) { if (el) el.classList.add('hidden'); }

function changeRunId(threadId) {
  return `CR-${(threadId || '0000').slice(0, 4).toUpperCase()}`;
}

function incidentId(threadId) {
  const d = new Date();
  const suffix = (threadId || '0000').slice(0, 4).toUpperCase();
  return `INC-${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}-${suffix}`;
}

function formatNow() {
  return new Date().toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatUtc(iso) {
  if (!iso) return '—';
  return new Date(iso).toISOString().replace('T', ' ').replace(/\.\d{3}Z$/, ' UTC');
}

function jobDuration(job) {
  if (!job?.started_at) return '—';
  const end = job.finished_at ? new Date(job.finished_at) : new Date();
  return `${Math.max(1, Math.round((end - new Date(job.started_at)) / 1000))}s`;
}

const INGEST_JOB_TERMINAL = new Set(['succeeded', 'failed']);
let ingestJobPollTimer = null;
let ingestAnimTimer = null;
let ingestFlowAnimTimer = null;

function ingestFlowCaptions() {
  const v = (typeof getArchDesign === 'function' && getArchDesign().vector) || 'Chroma';
  return [
    { stage: 'drive', text: 'Fetching .md runbooks from the shared Google Drive folder…' },
    { stage: 'staging', text: 'Writing files to /data/runbooks and splitting into chunks…' },
    { stage: 'embed', text: 'Embedding chunks with all-MiniLM-L6-v2 (384 dimensions)…' },
    { stage: 'chroma', text: `Upserting vectors into the active ${v} collection for RAG…` },
  ];
}
let ingestFlowCaptionIdx = 0;

function ingestLiveSteps() {
  const v = (typeof getArchDesign === 'function' && getArchDesign().vector) || 'Chroma';
  return [
    { title: 'Reading runbook files…', step: 'Parsing markdown · headers & sections', stage: 'parse', progress: 18 },
    { title: 'Chunking text…', step: '400-token windows · 64 overlap', stage: 'parse', progress: 38 },
    { title: 'Generating embeddings…', step: 'MiniLM-L6 · 384-dimensional vectors', stage: 'embed', progress: 62 },
    { title: `Upserting to ${v}…`, step: 'Writing vectors · updating collection', stage: 'store', progress: 85 },
    { title: 'Finalizing index…', step: 'Manifest swap · alias activation', stage: 'store', progress: 96 },
  ];
}

function startIngestAnimCycle() {
  stopIngestAnimCycle();
  let i = 0;
  const tick = () => {
    const steps = ingestLiveSteps();
    const s = steps[i % steps.length];
    if ($('ingest-job-live-title')) $('ingest-job-live-title').textContent = s.title;
    if ($('ingest-job-live-step')) $('ingest-job-live-step').textContent = s.step;
    const bar = document.querySelector('.ipa-progress-bar');
    if (bar) bar.style.width = `${s.progress}%`;
    document.querySelectorAll('.ipa-stage').forEach((el) => {
      el.classList.toggle('active', el.dataset.stage === s.stage);
    });
    i += 1;
    ingestAnimTimer = setTimeout(tick, 2400);
  };
  tick();
}

function stopIngestAnimCycle() {
  if (ingestAnimTimer) {
    clearTimeout(ingestAnimTimer);
    ingestAnimTimer = null;
  }
  document.querySelectorAll('.ipa-stage').forEach((el) => el.classList.remove('active'));
  const bar = document.querySelector('.ipa-progress-bar');
  if (bar) bar.style.width = '0%';
}

function normalizeJobStatus(status) {
  return String(status || 'pending').toLowerCase();
}

function jobStatusPillClass(status) {
  const s = normalizeJobStatus(status);
  if (s === 'running') return 'job-running';
  if (s === 'succeeded') return 'job-succeeded';
  if (s === 'failed') return 'job-failed';
  return 'job-pending';
}

function jobStatusPill(status) {
  const s = normalizeJobStatus(status);
  const cls = jobStatusPillClass(s);
  const active = s === 'running' || s === 'pending';
  const pulse = active ? '<span class="pulse-ring job-pulse"></span>' : '';
  return `<span class="pill job-status-pill ${cls}">${pulse}${s}</span>`;
}

function shortJobError(msg) {
  if (!msg) return 'Unknown error';
  const line = String(msg).split('\n')[0];
  return line.length > 140 ? `${line.slice(0, 137)}…` : line;
}

function setIngestJobLive(visible, title, detail, { restartAnim = true } = {}) {
  const panel = $('ingest-job-live');
  if (!panel) return;
  const wasHidden = panel.classList.contains('hidden');
  panel.classList.toggle('hidden', !visible);
  if (visible) {
    if ((wasHidden || restartAnim) && detail && $('ingest-job-live-detail')) {
      $('ingest-job-live-detail').textContent = detail;
    }
    if (wasHidden || restartAnim) {
      if (title && $('ingest-job-live-title')) $('ingest-job-live-title').textContent = title;
      startIngestAnimCycle();
    }
  } else {
    stopIngestAnimCycle();
  }
}

function setIngestJobMsg(text, tone = '') {
  const el = $('ingest-job-msg');
  if (!el) return;
  el.textContent = text || '';
  el.classList.remove('is-running', 'is-success', 'is-error');
  if (tone) el.classList.add(`is-${tone}`);
}

function renderIngestJob(job) {
  if (!job) {
    if ($('st-job')) $('st-job').textContent = '—';
    return;
  }
  const status = normalizeJobStatus(job.status);
  if ($('st-job')) {
    $('st-job').innerHTML = `${jobStatusPill(status)}<span class="job-type-label">${job.job_type || ''}</span>`;
  }
  if ($('st-files')) {
    const drivePart = job.drive_files_synced != null ? ` · ${job.drive_files_synced} from Drive` : '';
    $('st-files').textContent = `${job.runbooks_changed ?? 0} files · ${job.documents_indexed ?? 0} chunks${drivePart}`;
  }
  if ($('st-last-run')) $('st-last-run').textContent = formatUtc(job.finished_at || job.started_at);
  if ($('st-duration')) $('st-duration').textContent = jobDuration(job);

  if (status === 'running' || status === 'pending') {
    const vector = (typeof getArchDesign === 'function' && getArchDesign().vector) || 'Chroma';
    setIngestJobLive(true, 'Running ingestion job…', job.job_type === 'drive_sync_reindex'
      ? `Google Drive → /data/runbooks → ${vector} vector index`
      : `Seed runbooks → chunk → embed → ${vector}`, { restartAnim: false });
    setIngestJobMsg(`Job ${job.id.slice(0, 8)}… · ${status}`, 'running');
  } else {
    setIngestJobLive(false);
    if (status === 'succeeded') {
      setIngestJobMsg(
        `Job completed · ${job.runbooks_changed ?? 0} files · ${job.documents_indexed ?? 0} chunks indexed`,
        'success',
      );
    } else if (status === 'failed') {
      setIngestJobMsg(`Job failed · ${shortJobError(job.error_message)}`, 'error');
    }
  }
}

function stopIngestJobPoll() {
  if (ingestJobPollTimer) {
    clearTimeout(ingestJobPollTimer);
    ingestJobPollTimer = null;
  }
}

async function pollIngestJob(jobId) {
  stopIngestJobPoll();
  const poll = async () => {
    try {
      const job = await api(`/api/ingest/jobs/${encodeURIComponent(jobId)}`);
      renderIngestJob(job);
      const status = normalizeJobStatus(job.status);
      if (INGEST_JOB_TERMINAL.has(status)) {
        ingestJobPollTimer = null;
        if (status === 'succeeded') {
          showToast('success', 'Ingestion complete', `${job.documents_indexed ?? 0} chunks indexed`);
          if (currentTab === 'ing-jobs') await loadIngestIndex();
        } else {
          showToast('error', 'Ingestion failed', shortJobError(job.error_message));
        }
        await loadIngestStatus();
        return job;
      }
      ingestJobPollTimer = setTimeout(poll, 1500);
      return null;
    } catch (err) {
      setIngestJobMsg(err.message, 'error');
      setIngestJobLive(false);
      ingestJobPollTimer = null;
      return null;
    }
  };
  return poll();
}

const ROLE_LABELS = {
  admin: 'Admin',
  operator: 'Operator',
  viewer: 'Viewer',
};

function userInitials(name) {
  if (!name) return 'OP';
  return name.split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase();
}

function roleLabel(role) {
  return ROLE_LABELS[role] || role || 'User';
}

function getActivePipelineSteps() {
  if (currentMode === 'multi') return MULTI_GRAPH_STEPS;
  if (currentMode === 'mcp') return MCP_GRAPH_STEPS;
  return GRAPH_STEPS;
}

function normalizeWorkerId(entry) {
  return String(entry || '').split(':')[0];
}

function setAgentMode(mode) {
  currentMode = mode || 'standalone';
  if ($('agent-mode-select')) $('agent-mode-select').value = currentMode;
  if ($('active-mode')) $('active-mode').textContent = currentMode;
  $('orchestration-theater')?.classList.toggle('hidden', currentMode !== 'multi');
  $('mcp-theater')?.classList.toggle('hidden', currentMode !== 'mcp');
  initPipelineUI();
  if (currentMode === 'multi') buildOrchestrationGraph();
  if (currentMode === 'mcp') renderMcpTheaterIdle();
}

async function loadAgentModes() {
  try {
    const data = await api('/api/agents/modes');
    agentModesCache = data.modes || [];
    const sel = $('agent-mode-select');
    if (sel && agentModesCache.length) {
      sel.innerHTML = agentModesCache.map((m) => `<option value="${m.id}">${m.label}</option>`).join('');
      sel.value = currentMode;
    }
  } catch (_) {
    agentModesCache = [];
  }
  try {
    mcpRuntimeConfig = await api('/api/agents/mcp/config');
    if ($('mcp-server-pill') && mcpRuntimeConfig?.http_url) {
      const host = mcpRuntimeConfig.http_url.replace(/^https?:\/\//, '');
      $('mcp-server-pill').textContent = `${host} · basic auth`;
    }
  } catch (_) {
    mcpRuntimeConfig = null;
  }
}

function renderFlowTreeNode(node, depth = 0, isLast = false, branch = false) {
  const hasChildren = node.children?.length;
  const kids = hasChildren
    ? `<ul class="flow-tree-children${branch ? ' flow-tree-branch' : ''}">${node.children.map((c, i) => renderFlowTreeNode(c, depth + 1, i === node.children.length - 1, c.branch)).join('')}</ul>`
    : '';
  const iconName = node.icon || (node.kind === 'tool' ? 'actions' : 'sparkles');
  return `
    <li class="flow-tree-item${isLast ? ' is-last' : ''}" data-node="${node.id}" style="--depth:${depth}">
      <div class="flow-tree-row">
        <div class="flow-tree-card orch-${node.id}" data-node="${node.id}">
          <span class="flow-tree-dot"></span>
          <span class="flow-tree-icon">${icon(iconName, 'icon icon-sm')}</span>
          <div class="flow-tree-body">
            <strong>${escapeHtml(node.label)}</strong>
            <small>${escapeHtml(node.role || '')}</small>
            ${node.kind ? `<span class="flow-tree-kind pill open">${escapeHtml(node.kind)}</span>` : ''}
          </div>
        </div>
      </div>
      ${kids}
    </li>`;
}

function renderChainTreeNode(n, depth) {
  return `
    <li class="flow-tree-item" data-node="${n.id}" style="--depth:${depth}">
      <div class="flow-tree-row">
        <div class="flow-tree-card orch-${n.id}" data-node="${n.id}">
          <span class="flow-tree-dot"></span>
          <span class="flow-tree-icon">${icon(n.icon || 'sparkles', 'icon icon-sm')}</span>
          <div class="flow-tree-body">
            <strong>${escapeHtml(n.label)}</strong>
            <small>${escapeHtml(n.role || '')}</small>
            ${n.kind ? `<span class="flow-tree-kind pill open">${escapeHtml(n.kind)}</span>` : ''}
          </div>
        </div>
      </div>`;
}

function buildFlowTreeFromChain(nodes, containerId, rootClass = '') {
  const el = $(containerId);
  if (!el || !nodes.length) return;

  function wrapChain(slice, depth) {
    if (!slice.length) return '';
    const [head, ...tail] = slice;
    const inner = wrapChain(tail, depth + 1);
    const branchCls = head.branch ? ' flow-tree-branch' : '';
    const childBlock = inner
      ? `<ul class="flow-tree-children${branchCls}">${inner}</ul>`
      : '';
    return `${renderChainTreeNode(head, depth)}${childBlock}</li>`;
  }

  const tree = wrapChain(nodes, 0);
  el.innerHTML = `<ul class="flow-tree-root flow-tree-spine ${rootClass}">${tree}</ul>`;
  el.querySelectorAll('.flow-tree-item').forEach((item, i, all) => {
    if (i === all.length - 1) item.classList.add('is-last');
  });
}

function buildOrchestrationGraph() {
  buildFlowTreeFromChain(MULTI_AGENT_TREE, 'orch-tree');
  const full = $('orch-tree-full');
  if (full) buildFlowTreeFromChain(MULTI_AGENT_TREE, 'orch-tree-full', 'flow-tree-lg');
}

function buildMcpArchTree() {
  const el = $('mcp-arch-tree');
  if (!el) return;
  el.innerHTML = `<ul class="flow-tree-root flow-tree-spine flow-tree-mcp">${renderFlowTreeNode(MCP_ARCH_TREE)}</ul>`;
  highlightMcpToolNodes(lastPipelineResult?.mcp_tool_calls || []);
}

function setOrchestrationWorkerState(workerId, state) {
  [`orch-${workerId}`, `orch-full-${workerId}`].forEach((id) => {
    const el = $(id) || document.querySelector(`[data-node="${workerId}"] .flow-tree-card`);
    if (!el) return;
    el.classList.remove('pending', 'active', 'done', 'waiting');
    if (state) el.classList.add(state);
  });
  const supervisor = $('orch-supervisor') || document.querySelector('[data-node="supervisor"] .flow-tree-card');
  if (state === 'active' && workerId !== 'supervisor') supervisor?.classList.add('delegating');
  if (workerId === 'incident_worker' && state === 'done') supervisor?.classList.remove('delegating');
  if (workerId === 'supervisor' && state === 'active') supervisor?.classList.add('delegating');
}

function setTreeNodeState(nodeId, state) {
  document.querySelectorAll(`[data-node="${nodeId}"] .flow-tree-card`).forEach((el) => {
    el.classList.remove('pending', 'active', 'done', 'waiting', 'delegating');
    if (state) el.classList.add(state);
  });
}

function resetOrchestrationTheater() {
  buildOrchestrationGraph();
  $('orch-delegations') && ($('orch-delegations').innerHTML = '');
  $('orch-route-pill') && ($('orch-route-pill').textContent = 'route: —');
  $('orch-status') && ($('orch-status').textContent = 'Orchestrator assigns work down the hierarchy');
  $('orch-status-full') && ($('orch-status-full').textContent = 'Hierarchical supervisor → worker delegation chain');
  MULTI_AGENT_TREE.forEach((n) => setTreeNodeState(n.id, 'pending'));
  setTreeNodeState('supervisor', 'active');
}

function renderDelegationFeed(events = []) {
  const html = events.map((ev) => `
    <li class="orch-delegation-item">
      <span class="orch-from">${escapeHtml(ev.from || '—')}</span>
      <span class="orch-arrow">→</span>
      <span class="orch-to">${escapeHtml(ev.to || 'end')}</span>
      <span class="orch-msg">${escapeHtml(ev.message || '')}</span>
    </li>`).join('');
  ['orch-delegations', 'orch-delegations-full'].forEach((id) => {
    const list = $(id);
    if (list) list.innerHTML = html;
  });
}

function renderOrchestrationFromResult(data) {
  if (currentMode !== 'multi' || !data) return;
  const route = data.route || (data.worker_trace || []).find((t) => t.startsWith('supervisor:'))?.split(':')[1] || 'full_pipeline';
  if ($('orch-route-pill')) $('orch-route-pill').textContent = `route: ${route}`;
  if ($('orch-route-full')) $('orch-route-full').textContent = `route: ${route}`;
  renderDelegationFeed(data.delegation_events || []);
  const trace = (data.worker_trace || []).map(normalizeWorkerId);
  const awaitingHitl = data.status === 'awaiting_hitl';
  MULTI_AGENT_TREE.forEach((n) => {
    if (n.id === 'supervisor') {
      setTreeNodeState('supervisor', trace.length ? 'done' : 'active');
      return;
    }
    if (!trace.includes(n.id)) {
      setTreeNodeState(n.id, 'pending');
      return;
    }
    if (awaitingHitl && n.id === 'hitl_gate') setTreeNodeState(n.id, 'waiting');
    else if (awaitingHitl && n.id === 'incident_worker') setTreeNodeState(n.id, 'pending');
    else setTreeNodeState(n.id, data.status === 'completed' ? 'done' : 'done');
  });
  const active = trace[trace.length - 1];
  if (active === 'supervisor' || (data.worker_trace?.[0] || '').startsWith('supervisor')) {
    setTreeNodeState('supervisor', 'done');
  }
  if (active && active !== 'supervisor') {
    if (awaitingHitl && active === 'remediation_worker') setTreeNodeState('hitl_gate', 'waiting');
    else if (awaitingHitl) setTreeNodeState(active, 'done');
    else setTreeNodeState(active, data.status === 'completed' ? 'done' : 'active');
  }
  if (data.status === 'completed') MULTI_AGENT_TREE.forEach((n) => setTreeNodeState(n.id, 'done'));
}

function renderMcpTheaterIdle() {
  const list = $('mcp-call-list');
  if (!list) return;
  list.innerHTML = '<p class="muted mcp-idle">Run the pipeline in MCP mode to see HTTP tool invocations against the hosted server.</p>';
}

function renderMcpToolCalls(calls = [], targetId = 'mcp-call-list') {
  const list = $(targetId);
  if (!list) return;
  if (!calls.length) {
    if (targetId === 'mcp-call-list') renderMcpTheaterIdle();
    else list.innerHTML = '<p class="muted mcp-idle">No MCP tool calls yet — run the pipeline in MCP mode from Incident.</p>';
    return;
  }
  list.innerHTML = calls.map((call, i) => `
    <div class="mcp-call-card" style="--mcp-i:${i}">
      <div class="mcp-call-head">
        <strong>${escapeHtml(call.tool || 'tool')}</strong>
        <span class="pill open">${escapeHtml(call.transport || 'mcp_http')}</span>
      </div>
      <div class="mcp-call-meta muted">${escapeHtml(call.summary || 'ok')}</div>
      <pre class="mcp-call-input">${escapeHtml(JSON.stringify(call.input || {}, null, 2))}</pre>
    </div>`).join('');
  highlightMcpToolNodes(calls);
}

function highlightMcpToolNodes(calls = []) {
  const used = new Set((calls || []).map((c) => c.tool));
  document.querySelectorAll('[data-node^="tool-"]').forEach((el) => el.classList.remove('active', 'done'));
  const map = {
    query_logs: 'tool-logs',
    retrieve_runbooks: 'tool-runbooks',
    get_metrics: 'tool-metrics',
    create_ticket: 'tool-ticket',
  };
  Object.entries(map).forEach(([tool, nodeId]) => {
    const card = document.querySelector(`[data-node="${nodeId}"] .flow-tree-card`);
    if (!card) return;
    card.classList.add(used.has(tool) ? 'done' : 'pending');
  });
  ['mcp-agent', 'mcp-http', 'mcp-server'].forEach((id) => {
    const card = document.querySelector(`[data-node="${id}"] .flow-tree-card`);
    if (card && used.size) card.classList.add('done');
  });
}

async function loadMcpServerTab() {
  buildMcpArchTree();
  try {
    mcpRuntimeConfig = await api('/api/agents/mcp/config');
  } catch (_) {
    mcpRuntimeConfig = null;
  }
  const cfg = mcpRuntimeConfig || {};
  const host = (cfg.http_url || 'http://mcp-server:8081').replace(/^https?:\/\//, '');
  if ($('mcp-tab-url')) $('mcp-tab-url').textContent = cfg.http_url || '—';
  if ($('mcp-tab-auth')) $('mcp-tab-auth').textContent = cfg.auth === 'basic' ? `Basic (${cfg.user || 'mcp'} / ••••)` : '—';
  if ($('mcp-tab-transport')) $('mcp-tab-transport').textContent = cfg.http_enabled ? 'HTTP POST /tools/{name}' : 'in-process fallback';
  if ($('mcp-tab-host-pill')) $('mcp-tab-host-pill').textContent = `${host} · basic auth`;

  const toolsBody = $('mcp-tools-body');
  if (toolsBody) {
    const tools = cfg.tools || Object.keys(MCP_TOOL_META);
    toolsBody.innerHTML = tools.map((t) => {
      const meta = MCP_TOOL_META[t] || { backend: '—', desc: '' };
      return `<tr>
        <td><code>${escapeHtml(t)}</code></td>
        <td>${escapeHtml(meta.desc)}</td>
        <td><span class="pill open">${escapeHtml(meta.backend)}</span></td>
        <td class="muted">POST /tools/${escapeHtml(t)}</td>
      </tr>`;
    }).join('');
  }

  const healthEl = $('mcp-health-pill');
  if (healthEl) {
    healthEl.textContent = 'Checking…';
    healthEl.className = 'pill warn';
    const mcpOk = cfg.healthy === true;
    healthEl.textContent = mcpOk ? 'MCP server healthy' : (cfg.healthy === false ? 'MCP server unreachable' : 'Unknown');
    healthEl.className = `pill ${mcpOk ? 'pass' : 'p1'}`;
  }

  renderMcpToolCalls(lastPipelineResult?.mcp_tool_calls || [], 'mcp-tab-calls');
}

function loadMultiAgentTab() {
  buildOrchestrationGraph();
  if (lastPipelineResult && currentMode === 'multi') {
    renderOrchestrationFromResult(lastPipelineResult);
  } else {
    resetOrchestrationTheater();
  }
}

function loadCustomMcpServers() {
  try {
    return JSON.parse(localStorage.getItem(MCP_PLAYGROUND_STORAGE) || '[]');
  } catch (_) {
    return [];
  }
}

function saveCustomMcpServers(servers) {
  localStorage.setItem(MCP_PLAYGROUND_STORAGE, JSON.stringify(servers));
  mcpPlaygroundState.customServers = servers;
}

function getMcpPlaygroundServer(id) {
  return mcpPlaygroundState.servers.find((s) => s.id === id)
    || mcpPlaygroundState.customServers.find((s) => s.id === id);
}

function allMcpPlaygroundServers() {
  return [...mcpPlaygroundState.servers, ...mcpPlaygroundState.customServers];
}

function renderMcpServerRail() {
  const list = $('mcp-server-rail-list');
  if (!list) return;
  const active = mcpPlaygroundState.activeServerId;
  list.innerHTML = allMcpPlaygroundServers().map((s) => {
    const session = mcpPlaygroundState.sessions[s.id];
    const status = session?.connected ? 'connected' : (s.healthy ? 'online' : 'offline');
    return `
      <button type="button" class="mcp-server-rail-item${active === s.id ? ' active' : ''}" data-mcp-server="${escapeHtml(s.id)}">
        <span class="mcp-server-rail-dot ${status}"></span>
        <span class="mcp-server-rail-body">
          <strong>${escapeHtml(s.name)}</strong>
          <small>${escapeHtml(s.url?.replace(/^https?:\/\//, '') || '—')}</small>
        </span>
        ${s.builtin ? '<span class="pill open">builtin</span>' : ''}
      </button>`;
  }).join('');
  list.querySelectorAll('[data-mcp-server]').forEach((btn) => {
    btn.addEventListener('click', () => selectMcpPlaygroundServer(btn.dataset.mcpServer));
  });
}

function renderMcpConnectPanel(server) {
  const panel = $('mcp-connect-panel');
  if (!panel || !server) return;
  const session = mcpPlaygroundState.sessions[server.id];
  $('mcp-inspector-title').textContent = server.name;
  $('mcp-inspector-sub').textContent = server.description || server.url || '';
  if (session?.connected) {
    panel.classList.add('hidden');
    show($('mcp-tools-panel'));
    show($('mcp-tool-runner'));
    return;
  }
  show(panel);
  $('mcp-connect-url').value = server.url || '';
  $('mcp-connect-user').value = session?.username || server.default_user || 'mcp';
  $('mcp-connect-pass').value = session?.password || '';
  $('mcp-connect-status').textContent = '';
  hide($('mcp-tools-panel'));
  hide($('mcp-tool-runner'));
}

function selectMcpPlaygroundServer(serverId) {
  mcpPlaygroundState.activeServerId = serverId;
  mcpPlaygroundState.selectedTool = null;
  renderMcpServerRail();
  const server = getMcpPlaygroundServer(serverId);
  renderMcpConnectPanel(server);
  if (mcpPlaygroundState.sessions[serverId]?.connected) {
    renderMcpPlaygroundTools(serverId);
    renderMcpPlaygroundRunner(null);
  }
}

async function connectMcpPlaygroundServer() {
  const serverId = mcpPlaygroundState.activeServerId;
  const server = getMcpPlaygroundServer(serverId);
  if (!server) return;
  const statusEl = $('mcp-connect-status');
  const btn = $('mcp-connect-btn');
  const username = $('mcp-connect-user')?.value?.trim();
  const password = $('mcp-connect-pass')?.value || '';
  const url = $('mcp-connect-url')?.value?.trim() || server.url;
  if (statusEl) statusEl.textContent = 'Connecting…';
  btn?.classList.add('is-loading');
  try {
    const body = { server_id: serverId, username, password };
    if (!server.builtin) body.url = url;
    const data = await api('/api/mcp/playground/connect', { method: 'POST', body: JSON.stringify(body) });
    mcpPlaygroundState.sessions[serverId] = {
      connected: true,
      username,
      password,
      url: data.url || url,
      tools: data.tools || [],
      health: data.health,
    };
    if (statusEl) statusEl.textContent = '';
    hide($('mcp-connect-panel'));
    show($('mcp-tools-panel'));
    show($('mcp-tool-runner'));
    renderMcpPlaygroundTools(serverId);
    renderMcpPlaygroundRunner(null);
    renderMcpServerRail();
    showToast('success', 'Connected', `${data.tools?.length || 0} tools available`);
  } catch (err) {
    if (statusEl) statusEl.textContent = err.message;
    showToast('error', 'Connection failed', err.message);
  } finally {
    btn?.classList.remove('is-loading');
  }
}

function renderMcpPlaygroundTools(serverId) {
  const list = $('mcp-tools-list');
  const session = mcpPlaygroundState.sessions[serverId];
  if (!list || !session) return;
  const selected = mcpPlaygroundState.selectedTool;
  list.innerHTML = (session.tools || []).map((t) => `
    <button type="button" class="mcp-tool-list-item${selected === t.name ? ' active' : ''}" data-mcp-tool="${escapeHtml(t.name)}">
      <strong>${escapeHtml(t.name)}</strong>
      <span class="muted">${escapeHtml(t.description || '')}</span>
    </button>`).join('');
  list.querySelectorAll('[data-mcp-tool]').forEach((btn) => {
    btn.addEventListener('click', () => {
      mcpPlaygroundState.selectedTool = btn.dataset.mcpTool;
      renderMcpPlaygroundTools(serverId);
      const tool = session.tools.find((x) => x.name === btn.dataset.mcpTool);
      renderMcpPlaygroundRunner(tool);
    });
  });
  if ($('mcp-health-json')) {
    $('mcp-health-json').textContent = JSON.stringify(session.health || {}, null, 2);
  }
}

function renderMcpPlaygroundRunner(tool) {
  const runner = $('mcp-tool-runner');
  if (!runner) return;
  if (!tool) {
    runner.innerHTML = '<p class="muted mcp-idle">Select a tool from the list to configure and invoke.</p>';
    return;
  }
  const sample = tool.sample_input || {};
  runner.innerHTML = `
    <div class="mcp-runner-head">
      <div>
        <h3><code>${escapeHtml(tool.name)}</code></h3>
        <p class="muted">${escapeHtml(tool.description || '')}</p>
      </div>
      <button type="button" class="btn-primary btn-glossy btn-sm" id="mcp-invoke-btn"><span class="btn-shine"></span>Run tool</button>
    </div>
    <label class="mcp-json-label">Request JSON <span class="muted">POST /tools/${escapeHtml(tool.name)}</span></label>
    <textarea id="mcp-invoke-payload" class="mcp-json-editor" rows="10">${escapeHtml(JSON.stringify(sample, null, 2))}</textarea>
    <div class="mcp-response-wrap">
      <div class="mcp-response-head">
        <strong>Response</strong>
        <span class="muted" id="mcp-invoke-meta"></span>
      </div>
      <pre id="mcp-invoke-response" class="mcp-json-response">—</pre>
    </div>`;
  $('mcp-invoke-btn')?.addEventListener('click', invokeMcpPlaygroundTool);
  $('skills-run-btn')?.addEventListener('click', runSelectedSkillScript);
}

async function invokeMcpPlaygroundTool() {
  const serverId = mcpPlaygroundState.activeServerId;
  const tool = mcpPlaygroundState.selectedTool;
  const session = mcpPlaygroundState.sessions[serverId];
  if (!session || !tool) return;
  let payload = {};
  try {
    payload = JSON.parse($('mcp-invoke-payload')?.value || '{}');
  } catch (err) {
    showToast('error', 'Invalid JSON', err.message);
    return;
  }
  const btn = $('mcp-invoke-btn');
  const meta = $('mcp-invoke-meta');
  const out = $('mcp-invoke-response');
  btn?.classList.add('is-loading');
  if (meta) meta.textContent = 'Running…';
  try {
    const body = {
      server_id: serverId,
      tool,
      payload,
      username: session.username,
      password: session.password,
    };
    const server = getMcpPlaygroundServer(serverId);
    if (server && !server.builtin) body.url = session.url;
    const data = await api('/api/mcp/playground/invoke', { method: 'POST', body: JSON.stringify(body) });
    if (out) out.textContent = JSON.stringify(data.result, null, 2);
    if (meta) meta.textContent = `OK · ${new Date().toLocaleTimeString()}`;
    mcpPlaygroundState.invokeHistory.unshift({ tool, at: new Date().toISOString(), ok: true });
    renderMcpInvokeHistory();
    showToast('success', 'Tool invoked', tool);
  } catch (err) {
    if (out) out.textContent = err.message;
    if (meta) meta.textContent = 'Error';
    showToast('error', 'Invoke failed', err.message);
  } finally {
    btn?.classList.remove('is-loading');
  }
}

function renderMcpInvokeHistory() {
  const el = $('mcp-invoke-history');
  if (!el) return;
  const items = mcpPlaygroundState.invokeHistory.slice(0, 12);
  el.innerHTML = items.length
    ? items.map((h) => `<li><code>${escapeHtml(h.tool)}</code> <span class="muted">${formatAuditTime(h.at)}</span></li>`).join('')
    : '<li class="muted">No invocations yet</li>';
}

function showAddMcpServerModal() {
  show($('mcp-add-server-modal'));
  $('mcp-add-name').value = '';
  $('mcp-add-url').value = 'http://localhost:8081';
  $('mcp-add-user').value = 'mcp';
  $('mcp-add-pass').value = '';
}

function hideAddMcpServerModal() {
  hide($('mcp-add-server-modal'));
}

function saveNewMcpServer() {
  const name = $('mcp-add-name')?.value?.trim();
  const url = $('mcp-add-url')?.value?.trim();
  if (!name || !url) {
    showToast('error', 'Missing fields', 'Name and URL are required');
    return;
  }
  const id = `custom:${name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')}-${Date.now().toString(36)}`;
  const servers = loadCustomMcpServers();
  servers.push({
    id,
    name,
    url,
    auth: 'basic',
    transport: 'http+json',
    builtin: false,
    description: 'Custom MCP server',
    default_user: $('mcp-add-user')?.value?.trim() || 'mcp',
  });
  saveCustomMcpServers(servers);
  hideAddMcpServerModal();
  initMcpPlayground();
  selectMcpPlaygroundServer(id);
  if ($('mcp-connect-user')) $('mcp-connect-user').value = $('mcp-add-user')?.value || 'mcp';
  if ($('mcp-connect-pass')) $('mcp-connect-pass').value = $('mcp-add-pass')?.value || '';
  showToast('info', 'Server added', name);
}

async function initMcpPlayground() {
  try {
    const data = await api('/api/mcp/playground/servers');
    mcpPlaygroundState.servers = data.servers || [];
  } catch (_) {
    mcpPlaygroundState.servers = [];
  }
  mcpPlaygroundState.customServers = loadCustomMcpServers();
  renderMcpServerRail();
  renderMcpInvokeHistory();
  const active = mcpPlaygroundState.activeServerId;
  const first = allMcpPlaygroundServers()[0];
  if (active && getMcpPlaygroundServer(active)) selectMcpPlaygroundServer(active);
  else if (first) selectMcpPlaygroundServer(first.id);
}

let skillsCatalogState = { skills: [], activeSlug: null };

async function initSkillsCatalog() {
  const list = $('skills-rail-list');
  if (!list) return;
  list.innerHTML = '<p class="muted">Loading skills…</p>';
  try {
    const data = await api('/api/skills');
    skillsCatalogState.skills = data.skills || [];
    renderSkillsRail();
    const active = skillsCatalogState.activeSlug;
    if (active && skillsCatalogState.skills.some((s) => s.slug === active)) {
      selectSkill(active);
    } else if (skillsCatalogState.skills[0]) {
      selectSkill(skillsCatalogState.skills[0].slug);
    }
  } catch (err) {
    list.innerHTML = `<p class="muted">${escapeHtml(err.message)}</p>`;
  }
}

function renderSkillsRail() {
  const list = $('skills-rail-list');
  if (!list) return;
  const active = skillsCatalogState.activeSlug;
  list.innerHTML = skillsCatalogState.skills.map((s) => `
    <button type="button" class="skills-rail-item${active === s.slug ? ' active' : ''}" data-skill-slug="${escapeHtml(s.slug)}">
      <span class="skills-rail-icon">${s.scripts?.length ? '⚙️' : '📋'}</span>
      <span class="skills-rail-text">
        <strong>${escapeHtml(s.name)}</strong>
        <small class="muted">${escapeHtml(s.category)} · ${(s.scripts || []).length} script(s)</small>
      </span>
    </button>`).join('');
  list.querySelectorAll('[data-skill-slug]').forEach((btn) => {
    btn.addEventListener('click', () => selectSkill(btn.dataset.skillSlug));
  });
}

async function selectSkill(slug) {
  skillsCatalogState.activeSlug = slug;
  renderSkillsRail();
  hide($('skills-detail-empty'));
  show($('skills-detail-panel'));
  try {
    const skill = await api(`/api/skills/${encodeURIComponent(slug)}`);
    if ($('skills-detail-title')) $('skills-detail-title').textContent = skill.name || slug;
    if ($('skills-detail-meta')) $('skills-detail-meta').textContent = skill.description || '';
    if ($('skills-detail-category')) $('skills-detail-category').textContent = skill.category || 'general';
    if ($('skills-when-to-use')) $('skills-when-to-use').textContent = skill.when_to_use || '—';
    if ($('skills-use-mcp-instead')) $('skills-use-mcp-instead').textContent = skill.use_mcp_instead || '—';
    const pills = $('skills-related-mcp-tools');
    if (pills) {
      pills.innerHTML = (skill.related_mcp_tools || []).map((t) => `<span class="pill open">${escapeHtml(t)}</span>`).join('') || '<span class="muted">—</span>';
    }
    if ($('skills-md-body')) $('skills-md-body').textContent = skill.skill_md || '(no SKILL.md on disk)';
    const scripts = skill.scripts || skill.script_files || [];
    const runner = $('skills-runner-panel');
    const sel = $('skills-run-script');
    if (scripts.length && runner && sel) {
      show(runner);
      sel.innerHTML = scripts.map((s) => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
      if ($('skills-run-params')) {
        if (slug === 'severity-classifier') $('skills-run-params').value = 'checkout redis pool timeout HTTP 500';
        else if (slug === 'runbook-recall-check') $('skills-run-params').value = 'checkout-service checkout-redis-pool';
        else if (slug === 'checkout-redis-triage') $('skills-run-params').value = 'checkout-service';
        else $('skills-run-params').value = '';
      }
      if ($('skills-run-output')) $('skills-run-output').textContent = '—';
    } else if (runner) {
      hide(runner);
    }
  } catch (err) {
    showToast('error', 'Skill load failed', err.message);
  }
}

async function runSelectedSkillScript() {
  const slug = skillsCatalogState.activeSlug;
  const script = $('skills-run-script')?.value;
  if (!slug || !script) return;
  const paramsRaw = $('skills-run-params')?.value?.trim() || '';
  const params = paramsRaw ? paramsRaw.split(/\s+/) : [];
  const out = $('skills-run-output');
  if (out) out.textContent = 'Running…';
  try {
    const data = await api(`/api/skills/${encodeURIComponent(slug)}/run`, {
      method: 'POST',
      body: JSON.stringify({ script, params }),
    });
    if (out) out.textContent = JSON.stringify(data, null, 2);
    showToast('info', 'Script finished', `${script} exit ${data.exit_code}`);
  } catch (err) {
    if (out) out.textContent = err.message;
    showToast('error', 'Script failed', err.message);
  }
}

async function renderMcpVsSkillsGuide() {
  const el = $('mcp-vs-skills-body');
  if (!el) return;
  try {
    const guide = await api('/api/skills/guide/mcp-vs-skills');
    const matrix = (guide.decision_matrix || []).map((row) => `
      <tr>
        <td>${escapeHtml(row.scenario)}</td>
        <td><span class="pill ${row.use === 'MCP' ? 'open' : 'pass'}">${escapeHtml(row.use)}</span></td>
        <td><code>${escapeHtml(row.tool)}</code></td>
      </tr>`).join('');
    el.innerHTML = `
      <div class="card glossy-card learn-hero">
        <h3>${escapeHtml(guide.summary || 'MCP vs Skills')}</h3>
        <p class="muted">Both are stored in agentregistry — different jobs in the AgentOps stack.</p>
      </div>
      <div class="skills-guide-grid">
        <article class="card glossy-card skills-guide-card">
          <h4>🔌 MCP tools</h4>
          <p>${escapeHtml(guide.mcp?.what || '')}</p>
          <ul class="learn-topic-ul">${(guide.mcp?.when || []).map((w) => `<li>${escapeHtml(w)}</li>`).join('')}</ul>
          <p class="muted">${escapeHtml(guide.mcp?.design1 || '')}</p>
          <button type="button" class="btn-ghost btn-sm skills-go-mcp">Open MCP Inspector →</button>
        </article>
        <article class="card glossy-card skills-guide-card">
          <h4>📚 Skills</h4>
          <p>${escapeHtml(guide.skills?.what || '')}</p>
          <ul class="learn-topic-ul">${(guide.skills?.when || []).map((w) => `<li>${escapeHtml(w)}</li>`).join('')}</ul>
          <p class="muted">${escapeHtml(guide.skills?.design1 || '')}</p>
          <button type="button" class="btn-ghost btn-sm skills-go-catalog">Browse Skills Catalog →</button>
        </article>
      </div>
      <div class="card glossy-card">
        <h4>Decision matrix</h4>
        <table class="data-table">
          <thead><tr><th>Scenario</th><th>Use</th><th>Artifact</th></tr></thead>
          <tbody>${matrix}</tbody>
        </table>
      </div>`;
    el.querySelector('.skills-go-mcp')?.addEventListener('click', () => switchSection('mcp', 'mcp-playground'));
    el.querySelector('.skills-go-catalog')?.addEventListener('click', () => switchSection('mcp', 'mcp-skills'));
  } catch (err) {
    el.innerHTML = `<p class="muted">${escapeHtml(err.message)}</p>`;
  }
}

async function loadAdminAgentsRegistry() {
  if (currentUser?.role !== 'admin') return;
  const body = $('admin-agents-body');
  const subtitle = document.querySelector('#tab-adm-agents .card-header .muted');
  if (!body) return;
  try {
    const data = await api('/api/agents/registry');
    if (subtitle && data.registry_url) {
      subtitle.innerHTML = `OSS <a href="${escapeHtml(data.registry_url)}" target="_blank" rel="noopener">agentregistry</a> · backend: <code>${escapeHtml(data.backend || 'agentregistry')}</code>`;
    }
    body.innerHTML = (data.agents || []).map((a) => `
      <tr>
        <td><strong>${escapeHtml(a.name)}</strong></td>
        <td><code>${escapeHtml(a.slug)}</code></td>
        <td><span class="pill open">${escapeHtml(a.kind)}</span></td>
        <td>${escapeHtml(a.mode)}</td>
        <td class="muted">${escapeHtml((a.tools || []).join(', '))}</td>
        <td><span class="role-pill role-${a.risk_tier === 'high' ? 'admin' : 'operator'}">${escapeHtml(a.risk_tier)}</span></td>
        <td>${escapeHtml(a.owner)}</td>
      </tr>`).join('');
  } catch (err) {
    body.innerHTML = `<tr><td colspan="7" class="muted">${escapeHtml(err.message)}</td></tr>`;
  }
}

async function submitAdminAgentRegister(e) {
  e.preventDefault();
  if (currentUser?.role !== 'admin') {
    showToast('error', 'Admin required', 'Only admins can register agents');
    return;
  }
  const toolsRaw = $('adm-agent-tools')?.value || '';
  const tools = toolsRaw.split(',').map((t) => t.trim()).filter(Boolean);
  try {
    await api('/api/agents/registry', {
      method: 'POST',
      body: JSON.stringify({
        slug: $('adm-agent-slug')?.value?.trim(),
        name: $('adm-agent-name')?.value?.trim(),
        kind: $('adm-agent-kind')?.value,
        mode: $('adm-agent-mode')?.value,
        description: $('adm-agent-desc')?.value?.trim() || '',
        tools,
        risk_tier: $('adm-agent-risk')?.value,
        owner: $('adm-agent-owner')?.value?.trim() || 'platform-team',
        status: 'active',
      }),
    });
    showToast('success', 'Agent registered', $('adm-agent-slug')?.value);
    $('adm-agent-register-form')?.reset();
    if ($('adm-agent-owner')) $('adm-agent-owner').value = 'platform-team';
    loadAdminAgentsRegistry();
  } catch (err) {
    showToast('error', 'Registration failed', err.message);
  }
}

function setUserDisplay(userOrName) {
  const user = typeof userOrName === 'object' && userOrName
    ? userOrName
    : { name: userOrName || 'Operator', role: currentUser?.role || 'operator', email: currentUser?.email || '' };
  if (typeof userOrName === 'object' && userOrName) currentUser = userOrName;

  const name = user.name || user.email || 'Operator';
  const role = roleLabel(user.role);
  $('user-badge').textContent = name;
  $('user-role').textContent = role;
  $('topbar-avatar').textContent = userInitials(name);

  if ($('user-menu-name')) $('user-menu-name').textContent = name;
  if ($('user-menu-email')) $('user-menu-email').textContent = user.email || '—';
  if ($('user-menu-avatar')) $('user-menu-avatar').textContent = userInitials(name);
  if ($('user-menu-role-pill')) {
    $('user-menu-role-pill').textContent = role;
    $('user-menu-role-pill').className = `role-pill role-${user.role || 'operator'}`;
  }

  const isAdmin = user.role === 'admin';
  $('nav-admin')?.classList.toggle('hidden', !isAdmin);
  $('user-menu-admin')?.classList.toggle('hidden', !isAdmin);
}

async function refreshCurrentUser() {
  if (!token || IS_CAPTURE) return currentUser;
  try {
    const user = await api('/api/auth/me');
    setUserDisplay(user);
    return user;
  } catch (_) {
    return currentUser;
  }
}

function closeUserMenu() {
  userMenuOpen = false;
  hide($('user-menu-panel'));
  $('user-menu-btn')?.setAttribute('aria-expanded', 'false');
}

function toggleUserMenu() {
  userMenuOpen = !userMenuOpen;
  if (userMenuOpen) {
    show($('user-menu-panel'));
    $('user-menu-btn')?.setAttribute('aria-expanded', 'true');
  } else {
    closeUserMenu();
  }
}

function openProfileModal() {
  closeUserMenu();
  if (!currentUser) return;
  $('profile-name').value = currentUser.name || '';
  $('profile-email').value = currentUser.email || '';
  $('profile-role').value = roleLabel(currentUser.role);
  $('profile-timezone').value = currentUser.timezone || 'UTC';
  $('profile-theme').value = currentUser.theme_pref || localStorage.getItem('agentops-theme') || 'light';
  $('profile-notify-hitl').checked = currentUser.notify_hitl !== false;
  $('profile-notify-pipeline').checked = currentUser.notify_pipeline !== false;
  $('profile-current-password').value = '';
  $('profile-new-password').value = '';
  $('profile-msg').textContent = '';
  show($('profile-modal'));
}

function closeProfileModal() {
  hide($('profile-modal'));
}

async function saveProfileSettings(e) {
  e.preventDefault();
  const body = {
    name: $('profile-name').value.trim(),
    timezone: $('profile-timezone').value,
    theme_pref: $('profile-theme').value,
    notify_hitl: $('profile-notify-hitl').checked,
    notify_pipeline: $('profile-notify-pipeline').checked,
  };
  try {
    const updated = await api('/api/auth/profile', { method: 'PATCH', body: JSON.stringify(body) });
    setUserDisplay(updated);
    if (typeof window.applyTheme === 'function') window.applyTheme(updated.theme_pref);
    showToast('success', 'Profile saved', 'Your preferences were updated');
    closeProfileModal();
  } catch (err) {
    $('profile-msg').textContent = err.message;
    showToast('error', 'Profile update failed', err.message);
  }
}

async function savePasswordChange(e) {
  e.preventDefault();
  const current = $('profile-current-password').value;
  const next = $('profile-new-password').value;
  if (!current || !next) {
    $('profile-msg').textContent = 'Enter current and new password';
    return;
  }
  try {
    await api('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: current, new_password: next }),
    });
    $('profile-current-password').value = '';
    $('profile-new-password').value = '';
    $('profile-msg').textContent = 'Password updated successfully';
    showToast('success', 'Password updated', 'Use your new password on next sign-in');
  } catch (err) {
    $('profile-msg').textContent = err.message;
    showToast('error', 'Password change failed', err.message);
  }
}

function initUserMenu() {
  $('user-menu-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    closeNotifPanel();
    toggleUserMenu();
  });
  $('user-menu-profile')?.addEventListener('click', openProfileModal);
  $('user-menu-admin')?.addEventListener('click', () => {
    closeUserMenu();
    switchSection('admin', 'adm-overview');
  });
  $('profile-modal-close')?.addEventListener('click', closeProfileModal);
  $('profile-modal')?.addEventListener('click', (e) => {
    if (e.target === $('profile-modal')) closeProfileModal();
  });
  $('profile-form')?.addEventListener('submit', saveProfileSettings);
  $('password-form')?.addEventListener('submit', savePasswordChange);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !$('profile-modal')?.classList.contains('hidden')) closeProfileModal();
    if (e.key === 'Escape' && userMenuOpen) closeUserMenu();
  });
  document.addEventListener('click', (e) => {
    if (!userMenuOpen) return;
    if (e.target.closest('.user-menu-wrap')) return;
    closeUserMenu();
  });
}

function renderAdminRoleBars(counts = {}) {
  const el = $('admin-role-bars');
  if (!el) return;
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  el.innerHTML = Object.entries(counts).map(([role, count]) => `
    <div class="admin-role-row">
      <div class="admin-role-meta"><span class="role-pill role-${role}">${roleLabel(role)}</span><strong>${count}</strong></div>
      <div class="admin-role-bar"><span style="width:${Math.round((count / total) * 100)}%"></span></div>
    </div>`).join('');
}

function renderAdminRecentRuns(runs = []) {
  const body = $('admin-recent-runs');
  if (!body) return;
  body.innerHTML = runs.length
    ? runs.map((r) => `<tr>
        <td>${escapeHtml(r.service || '—')}</td>
        <td><span class="pill ${r.status === 'completed' ? 'open' : 'p1'}">${escapeHtml(r.status || '—')}</span></td>
        <td>${escapeHtml(r.triggered_by || '—')}</td>
        <td class="muted">${escapeHtml(formatUtc(r.started_at))}</td>
      </tr>`).join('')
    : '<tr><td colspan="4" class="muted">No agent runs recorded yet</td></tr>';
}

function renderAdminHitlRows(items = []) {
  const body = $('admin-hitl-body');
  if (!body) return;
  body.innerHTML = items.length
    ? items.map((d) => `<tr>
        <td><span class="pill ${d.decision === 'approved' ? 'open' : 'p1'}">${escapeHtml(d.decision || '—')}</span></td>
        <td>${escapeHtml(d.service || '—')}</td>
        <td>${escapeHtml(d.decided_by || '—')}</td>
        <td>${escapeHtml(d.reason || '—')}</td>
        <td class="muted">${escapeHtml(formatUtc(d.decided_at))}</td>
      </tr>`).join('')
    : '<tr><td colspan="5" class="muted">No HITL decisions yet</td></tr>';
}

async function loadAdminOverview() {
  if (currentUser?.role !== 'admin') return;
  try {
    const data = await api('/api/admin/overview');
    const stats = data.platform_stats || {};
    $('adm-stat-users').textContent = String(data.total_users ?? '—');
    $('adm-stat-pipelines').textContent = String(stats.active_pipelines ?? '—');
    $('adm-stat-opa').textContent = String(data.opa_stats?.total ?? data.opa_stats?.evaluations ?? '—');
    $('adm-stat-success').textContent = stats.success_rate || '—';
    renderAdminRoleBars(data.user_counts || {});
    renderAdminRecentRuns(data.recent_runs || []);
    renderAdminHitlRows(data.recent_hitl || []);
  } catch (err) {
    showToast('error', 'Admin overview failed', err.message);
  }
}

function renderAdminUsersTable(users = []) {
  const body = $('admin-users-body');
  if (!body) return;
  body.innerHTML = users.map((u) => {
    const isSelf = u.email === currentUser?.email;
    const notify = [u.notify_hitl ? 'HITL' : null, u.notify_pipeline ? 'Pipeline' : null].filter(Boolean).join(', ') || 'None';
    return `<tr>
      <td><strong>${escapeHtml(u.name)}</strong>${isSelf ? ' <span class="muted">(you)</span>' : ''}</td>
      <td>${escapeHtml(u.email)}</td>
      <td><span class="role-pill role-${u.role}">${roleLabel(u.role)}</span></td>
      <td>${escapeHtml(u.timezone || 'UTC')}</td>
      <td class="muted">${escapeHtml(notify)}</td>
      <td class="admin-user-actions">
        <button type="button" class="btn-ghost btn-sm adm-user-edit" data-email="${escapeHtml(u.email)}">Edit</button>
        ${isSelf ? '' : `<button type="button" class="btn-ghost btn-sm adm-user-delete" data-email="${escapeHtml(u.email)}">Delete</button>`}
      </td>
    </tr>`;
  }).join('');

  body.querySelectorAll('.adm-user-edit').forEach((btn) => {
    btn.addEventListener('click', () => openAdminUserForm(btn.dataset.email, users));
  });
  body.querySelectorAll('.adm-user-delete').forEach((btn) => {
    btn.addEventListener('click', () => deleteAdminUser(btn.dataset.email));
  });
}

async function loadAdminUsers() {
  if (currentUser?.role !== 'admin') return;
  try {
    const data = await api('/api/admin/users');
    renderAdminUsersTable(data.users || []);
  } catch (err) {
    showToast('error', 'User list failed', err.message);
  }
}

async function loadAdminActivity() {
  if (currentUser?.role !== 'admin') return;
  try {
    const data = await api('/api/admin/overview');
    renderAdminHitlRows(data.recent_hitl || []);
  } catch (err) {
    showToast('error', 'Activity load failed', err.message);
  }
}

function loadAdminSection(tabId) {
  if (currentUser?.role !== 'admin') {
    showToast('warning', 'Admin only', 'You need admin role to access this section');
    switchSection('operations', 'ops-incident');
    return;
  }
  if (tabId === 'adm-agents') loadAdminAgentsRegistry();
  else if (tabId === 'adm-users') loadAdminUsers();
  else if (tabId === 'adm-activity') loadAdminActivity();
  else loadAdminOverview();
}

function resetAdminUserForm() {
  admUserEditEmail = '';
  $('adm-user-edit-email').value = '';
  $('adm-user-name').value = '';
  $('adm-user-email').value = '';
  $('adm-user-email').disabled = false;
  $('adm-user-role').value = 'operator';
  $('adm-user-password').value = '';
  $('adm-user-password').required = true;
  $('adm-user-timezone').value = 'UTC';
  $('adm-user-form-title').textContent = 'Add user';
  hide($('adm-user-form-card'));
}

function openAdminUserForm(email, users) {
  const list = users || [];
  const existing = list.find((u) => u.email === email);
  admUserEditEmail = existing?.email || '';
  $('adm-user-edit-email').value = admUserEditEmail;
  $('adm-user-name').value = existing?.name || '';
  $('adm-user-email').value = existing?.email || '';
  $('adm-user-email').disabled = Boolean(existing);
  $('adm-user-role').value = existing?.role || 'operator';
  $('adm-user-password').value = '';
  $('adm-user-password').required = !existing;
  $('adm-user-password').placeholder = existing ? 'Leave blank to keep current password' : 'Min 6 characters';
  $('adm-user-timezone').value = existing?.timezone || 'UTC';
  $('adm-user-form-title').textContent = existing ? 'Edit user' : 'Add user';
  show($('adm-user-form-card'));
  $('adm-user-form-card').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function submitAdminUserForm(e) {
  e.preventDefault();
  const payload = {
    name: $('adm-user-name').value.trim(),
    role: $('adm-user-role').value,
    timezone: $('adm-user-timezone').value.trim() || 'UTC',
  };
  const password = $('adm-user-password').value;
  try {
    if (admUserEditEmail) {
      const patch = { ...payload };
      if (password) patch.password = password;
      await api(`/api/admin/users/${encodeURIComponent(admUserEditEmail)}`, {
        method: 'PATCH',
        body: JSON.stringify(patch),
      });
      showToast('success', 'User updated', admUserEditEmail);
    } else {
      await api('/api/admin/users', {
        method: 'POST',
        body: JSON.stringify({
          ...payload,
          email: $('adm-user-email').value.trim().toLowerCase(),
          password,
        }),
      });
      showToast('success', 'User created', $('adm-user-email').value);
    }
    resetAdminUserForm();
    await loadAdminUsers();
    await loadAdminOverview();
  } catch (err) {
    showToast('error', 'User save failed', err.message);
  }
}

async function deleteAdminUser(email) {
  if (!email || !confirm(`Delete user ${email}?`)) return;
  try {
    await api(`/api/admin/users/${encodeURIComponent(email)}`, { method: 'DELETE' });
    showToast('success', 'User deleted', email);
    resetAdminUserForm();
    await loadAdminUsers();
    await loadAdminOverview();
  } catch (err) {
    showToast('error', 'Delete failed', err.message);
  }
}

function initAdminPanel() {
  $('adm-refresh-overview')?.addEventListener('click', loadAdminOverview);
  $('adm-refresh-activity')?.addEventListener('click', loadAdminActivity);
  $('adm-agents-refresh')?.addEventListener('click', loadAdminAgentsRegistry);
  $('adm-agent-register-form')?.addEventListener('submit', submitAdminAgentRegister);
  $('mcp-tab-refresh')?.addEventListener('click', loadMcpServerTab);
  $('mcp-connect-btn')?.addEventListener('click', connectMcpPlaygroundServer);
  $('mcp-add-server-btn')?.addEventListener('click', showAddMcpServerModal);
  $('mcp-add-server-save')?.addEventListener('click', saveNewMcpServer);
  $('mcp-add-server-cancel')?.addEventListener('click', hideAddMcpServerModal);
  $('mcp-add-server-cancel-2')?.addEventListener('click', hideAddMcpServerModal);
  $('mcp-add-server-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'mcp-add-server-modal') hideAddMcpServerModal();
  });
  $('adm-user-add')?.addEventListener('click', () => openAdminUserForm('', []));
  $('adm-user-form-cancel')?.addEventListener('click', resetAdminUserForm);
  $('adm-user-form')?.addEventListener('submit', submitAdminUserForm);
}

function getLogSnippet() {
  return $('log_snippet').textContent.trim();
}

function setPendingBadge(visible) {
  if (visible) {
    show($('cr-pending-badge'));
    pushNotification({
      type: 'warning',
      title: 'HITL approval required',
      message: 'Agent remediation is waiting for operator sign-off.',
      action: { section: 'simulation', tab: 'auto-change' },
      dedupeKey: 'hitl-pending',
    });
  } else {
    hide($('cr-pending-badge'));
  }
  updateQuickStats();
}

function pushNotification({ type = 'info', title, message = '', action = null, dedupeKey = null }) {
  if (dedupeKey && notifications.some((n) => n.dedupeKey === dedupeKey && !n.read)) return;
  notifications.unshift({
    id: `n-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    type,
    title,
    message,
    action,
    dedupeKey,
    read: false,
    time: new Date().toISOString(),
  });
  if (notifications.length > 50) notifications.length = 50;
  renderNotificationPanel();
  updateNotifDot();
}

function updateNotifDot() {
  const unread = notifications.filter((n) => !n.read).length;
  const dot = $('notif-dot');
  if (dot) dot.classList.toggle('hidden', unread === 0);
  $('notif-btn')?.classList.toggle('has-unread', unread > 0);
  const label = $('notif-unread-count');
  if (label) label.textContent = unread ? `${unread} unread` : '';
}

function formatNotifTime(iso) {
  try {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (_) {
    return '';
  }
}

function renderNotificationPanel() {
  const list = $('notif-list');
  const empty = $('notif-empty');
  if (!list) return;

  if (!notifications.length) {
    list.innerHTML = '';
    if (empty) empty.style.display = '';
    updateNotifDot();
    return;
  }
  if (empty) empty.style.display = 'none';

  list.innerHTML = notifications.map((n) => `
    <li class="notif-item ${n.read ? 'read' : 'unread'} notif-${n.type}" data-notif-id="${n.id}">
      <span class="notif-item-icon">${NOTIF_ICONS[n.type] || 'i'}</span>
      <div class="notif-item-body">
        <strong>${escapeHtml(n.title)}</strong>
        ${n.message ? `<p>${escapeHtml(n.message)}</p>` : ''}
        <div class="notif-item-time">${formatNotifTime(n.time)}</div>
      </div>
    </li>`).join('');

  list.querySelectorAll('.notif-item').forEach((li) => {
    li.addEventListener('click', () => handleNotificationClick(li.dataset.notifId));
  });
  updateNotifDot();
}

function handleNotificationClick(id) {
  const item = notifications.find((n) => n.id === id);
  if (!item) return;
  item.read = true;
  updateNotifDot();
  renderNotificationPanel();
  if (item.action) {
    closeNotifPanel();
    switchSection(item.action.section, item.action.tab);
  }
}

function toggleNotifPanel() {
  notifPanelOpen = !notifPanelOpen;
  const panel = $('notif-panel');
  const btn = $('notif-btn');
  if (!panel || !btn) return;
  panel.classList.toggle('hidden', !notifPanelOpen);
  btn.classList.toggle('active', notifPanelOpen);
  btn.setAttribute('aria-expanded', notifPanelOpen ? 'true' : 'false');
  if (notifPanelOpen) renderNotificationPanel();
}

function closeNotifPanel() {
  notifPanelOpen = false;
  $('notif-panel')?.classList.add('hidden');
  $('notif-btn')?.classList.remove('active');
  $('notif-btn')?.setAttribute('aria-expanded', 'false');
}

function markAllNotificationsRead() {
  notifications.forEach((n) => { n.read = true; });
  updateNotifDot();
  renderNotificationPanel();
}

function initNotifications() {
  $('notif-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleNotifPanel();
  });
  $('notif-mark-read')?.addEventListener('click', (e) => {
    e.stopPropagation();
    markAllNotificationsRead();
  });
  document.addEventListener('click', (e) => {
    if (!notifPanelOpen) return;
    if (e.target.closest('.notif-wrap')) return;
    closeNotifPanel();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && notifPanelOpen) closeNotifPanel();
  });
  renderNotificationPanel();
}

function createRipple(el, e, variant = '') {
  if (!el || el.classList.contains('is-loading')) return;
  const rect = el.getBoundingClientRect();
  const ripple = document.createElement('span');
  ripple.className = `ripple${variant ? ` ripple-${variant}` : ''}`;
  const size = Math.max(rect.width, rect.height) * 1.2;
  ripple.style.width = `${size}px`;
  ripple.style.height = `${size}px`;
  ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
  ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
  el.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
}

function addRipple(el, e) { createRipple(el, e); }

function showToast(type, title, message = '') {
  const stack = $('toast-stack');
  if (!stack) return;
  const icons = { success: '✓', error: '✕', warning: '!', info: 'i' };
  const el = document.createElement('div');
  el.className = `toast-item toast-${type}`;
  el.innerHTML = `<div class="toast-icon">${icons[type] || 'i'}</div><div class="toast-body"><strong>${title}</strong>${message ? `<span>${message}</span>` : ''}</div>`;
  stack.appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity 0.3s, transform 0.3s';
    el.style.opacity = '0';
    el.style.transform = 'translateX(16px)';
    setTimeout(() => el.remove(), 320);
  }, 4200);
}

function animateStatChange(containerId, newValue) {
  const el = $(containerId);
  if (!el) return;
  const num = el.querySelector('.stat-num');
  if (!num || String(num.textContent) === String(newValue)) return;
  el.classList.remove('stat-pop');
  void el.offsetWidth;
  num.textContent = newValue;
  el.classList.add('stat-pop');
}

function updateTrend(id, value) {
  const el = $(id);
  if (!el) return;
  const text = value || '—';
  el.textContent = text;
  el.classList.remove('up', 'down');
  if (text.startsWith('↑')) el.classList.add('up');
  else if (text.startsWith('↓')) el.classList.add('down');
}

function syncDashboardStats() {
  animateStatChange('stat-pipelines', String(DASHBOARD_STATS.pipelines).padStart(2, '0'));
  animateStatChange('stat-alerts', String(DASHBOARD_STATS.alerts).padStart(2, '0'));
  animateStatChange('stat-agents', String(DASHBOARD_STATS.agents));
  animateStatChange('stat-success', DASHBOARD_STATS.success);
  animateStatChange('stat-mttr', DASHBOARD_STATS.mttr);
  updateTrend('trend-pipelines', DASHBOARD_STATS.trends?.pipelines);
  updateTrend('trend-alerts', DASHBOARD_STATS.trends?.alerts);
  updateTrend('trend-agents', DASHBOARD_STATS.trends?.agents);
  updateTrend('trend-success', DASHBOARD_STATS.trends?.success);
  updateTrend('trend-mttr', DASHBOARD_STATS.trends?.mttr);
}

async function loadDashboardStats() {
  if (IS_CAPTURE) {
    DASHBOARD_STATS = {
      pipelines: 0,
      alerts: 0,
      agents: 4,
      success: '100.0%',
      mttr: '—',
      trends: {
        pipelines: '—',
        alerts: '—',
        agents: '—',
        success: '—',
        mttr: '—',
      },
    };
    syncDashboardStats();
    return;
  }
  try {
    const data = await api('/api/dashboard/stats');
    DASHBOARD_STATS = {
      pipelines: data.active_pipelines ?? 0,
      alerts: data.p1_alerts ?? 0,
      agents: data.agents_online ?? 0,
      success: data.success_rate ?? '—',
      mttr: data.mttr ?? '—',
      trends: {
        pipelines: data.active_pipelines_trend ?? '—',
        alerts: data.p1_alerts_trend ?? '—',
        agents: data.agents_online_trend ?? '—',
        success: data.success_rate_trend ?? '—',
        mttr: data.mttr_trend ?? '—',
      },
    };
    syncDashboardStats();
  } catch (_) {
    /* keep last values */
  }
}

function initPipelineFlow() {
  const container = $('pipeline-flow');
  if (!container || container.dataset.ready) return;
  const nodesWrap = document.createElement('div');
  nodesWrap.className = 'pipeline-flow-nodes';
  nodesWrap.style.cssText = 'display:flex;align-items:center;justify-content:space-between;width:100%;position:relative;z-index:1';
  nodesWrap.innerHTML = FLOW_NODES.map((n) => `
    <div class="pipeline-node" id="flow-node-${n.id}" data-flow="${n.id}">
      <div class="pipeline-node-circle ${n.color}">${n.label.slice(0, 1)}</div>
      <div class="pipeline-node-label">${n.label}</div>
      <div class="pipeline-node-state">Pending</div>
    </div>`).join('');
  container.appendChild(nodesWrap);
  container.dataset.ready = '1';
}

function resetPipelineFlow() {
  FLOW_NODES.forEach((n) => {
    const el = $(`flow-node-${n.id}`);
    if (!el) return;
    el.classList.remove('active', 'done', 'waiting');
    el.querySelector('.pipeline-node-state').textContent = 'Pending';
  });
  const progress = $('pipeline-flow-progress');
  if (progress) progress.style.width = '0%';
  setPipelineLiveMode(false);
}

function setFlowNodeState(nodeId, state) {
  const el = $(`flow-node-${nodeId}`);
  if (!el) return;
  el.classList.remove('active', 'done', 'waiting');
  const stateEl = el.querySelector('.pipeline-node-state');
  const circle = el.querySelector('.pipeline-node-circle');
  if (circle) {
    circle.classList.remove('state-pop');
    void circle.offsetWidth;
    if (state === 'done' || state === 'active' || state === 'waiting') circle.classList.add('state-pop');
  }
  if (state === 'done') {
    el.classList.add('done');
    stateEl.textContent = 'Done';
  } else if (state === 'active') {
    el.classList.add('active');
    stateEl.textContent = 'Running';
  } else if (state === 'waiting') {
    el.classList.add('waiting');
    stateEl.textContent = 'Waiting';
  } else {
    stateEl.textContent = 'Pending';
  }
}

async function animatePipelineRun() {
  const token = ++pipelineAnimToken;
  resetPipelineFlow();
  setPipelineLiveMode(true);
  if (currentMode === 'multi') {
    resetOrchestrationTheater();
    show($('orchestration-theater'));
  } else {
    hide($('orchestration-theater'));
  }
  if (currentMode === 'mcp') {
    renderMcpTheaterIdle();
    show($('mcp-theater'));
  } else {
    hide($('mcp-theater'));
  }
  const steps = getActivePipelineSteps();
  const progress = $('pipeline-flow-progress');
  const btn = $('run-pipeline-btn');
  const label = btn?.querySelector('.btn-label');

  if (label) label.textContent = 'Starting…';
  btn?.classList.add('is-running', 'is-loading');

  for (let i = 0; i < steps.length; i++) {
    if (token !== pipelineAnimToken) return;
    const step = steps[i];
    if (currentMode === 'multi') {
      if (step.id === 'supervisor') {
        $('orch-route-pill') && ($('orch-route-pill').textContent = 'route: planning…');
        $('orch-status') && ($('orch-status').textContent = 'Supervisor routing down the hierarchy');
        renderDelegationFeed(MULTI_DELEGATION_PREVIEW.slice(0, 1));
        setTreeNodeState('supervisor', 'active');
      } else {
        const treeIdx = MULTI_AGENT_TREE.findIndex((n) => n.id === step.id);
        if (treeIdx >= 0) {
          MULTI_AGENT_TREE.forEach((n, idx) => {
            if (idx < treeIdx) setTreeNodeState(n.id, 'done');
            else if (idx === treeIdx) setTreeNodeState(n.id, 'active');
          });
          setTreeNodeState('supervisor', 'done');
          $('orch-status') && ($('orch-status').textContent = `Active → ${step.label}`);
          const previewIdx = MULTI_DELEGATION_PREVIEW.findIndex((d) => d.to === step.id);
          if (previewIdx >= 0) renderDelegationFeed(MULTI_DELEGATION_PREVIEW.slice(0, previewIdx + 1));
        }
        if (step.id === 'hitl_gate') {
          $('orch-status') && ($('orch-status').textContent = 'Awaiting human approval at HITL gate');
          renderDelegationFeed(MULTI_DELEGATION_PREVIEW);
          setTreeNodeState('hitl_gate', 'waiting');
        }
      }
    }
    if (currentMode === 'mcp') {
      if (step.id === 'retrieve') renderMcpToolCalls(MCP_TOOL_PREVIEW.slice(0, 1));
      else if (step.id === 'metrics') renderMcpToolCalls(MCP_TOOL_PREVIEW.slice(0, 3));
      else if (step.id === 'execute') renderMcpToolCalls(MCP_TOOL_PREVIEW);
      if ($('mcp-theater-status')) {
        $('mcp-theater-status').textContent = `POST /tools/${step.label} → hosted MCP server (Basic Auth)`;
      }
    }
    FLOW_NODES.forEach((n, idx) => {
      const flowIdx = Math.min(FLOW_NODES.length - 1, Math.floor((i / Math.max(steps.length - 1, 1)) * (FLOW_NODES.length - 1)));
      if (idx < flowIdx) setFlowNodeState(n.id, 'done');
      else if (idx === flowIdx) setFlowNodeState(n.id, 'active');
      else setFlowNodeState(n.id, 'pending');
    });
    if (progress) progress.style.width = `${((i + 1) / steps.length) * 100}%`;
    pulsePipelineParticles();
    await new Promise((r) => setTimeout(r, currentMode === 'multi' ? 520 : 420));
  }

  if (token !== pipelineAnimToken) return;
}

function completeRunButtonState(running = false) {
  const btn = $('run-pipeline-btn');
  const label = btn?.querySelector('.btn-label');
  btn?.classList.remove('is-loading');
  if (running) {
    btn?.classList.add('is-running');
    if (label) label.textContent = 'Pipeline Running';
  } else {
    btn?.classList.remove('is-running');
    if (label) label.textContent = 'Run Pipeline';
  }
}

function animateApproval(btn, banner) {
  createRipple(btn, { clientX: btn.getBoundingClientRect().left + btn.offsetWidth / 2, clientY: btn.getBoundingClientRect().top + btn.offsetHeight / 2 }, 'success');
  const burst = document.createElement('div');
  burst.className = 'approve-burst';
  btn.style.position = 'relative';
  for (let i = 0; i < 10; i++) {
    const p = document.createElement('span');
    const angle = (i / 10) * Math.PI * 2;
    p.style.setProperty('--bx', `${Math.cos(angle) * 36}px`);
    p.style.setProperty('--by', `${Math.sin(angle) * 36}px`);
    p.style.left = '50%';
    p.style.top = '50%';
    burst.appendChild(p);
  }
  btn.appendChild(burst);
  setTimeout(() => burst.remove(), 800);
  banner?.classList.add('approve-flash');
  setFlowNodeState('hitl', 'done');
  setFlowNodeState('remediation', 'active');
  showToast('success', 'Action approved', 'Execution queued — pipeline continuing');
  playSuccessBurst(banner);
}

function animateRejection(btn, banner) {
  createRipple(btn, { clientX: btn.getBoundingClientRect().left + btn.offsetWidth / 2, clientY: btn.getBoundingClientRect().top + btn.offsetHeight / 2 }, 'danger');
  banner?.classList.add('reject-shake');
  setFlowNodeState('hitl', 'waiting');
  $('flow-node-hitl')?.querySelector('.pipeline-node-state') && ($('flow-node-hitl').querySelector('.pipeline-node-state').textContent = 'Rejected');
  showToast('error', 'Action rejected', 'Pipeline stopped — no changes applied');
  setTimeout(() => banner?.classList.remove('reject-shake'), 400);
  pipelineAnimToken++;
  resetPipelineFlow();
}

function updateContextPanel() {
  const hitlCard = $('ctx-hitl-card');
  const empty = $('ctx-empty');
  if (pendingThread) {
    show(hitlCard);
    hide(empty);
    $('ctx-hitl-text').textContent = $('cr-recommendation')?.textContent || $('hitl-text')?.textContent || 'Approval required';
    $('ctx-hitl-service').textContent = $('cr-service')?.textContent || $('service')?.value || '—';
  } else if (currentSection === 'operations') {
    hide(hitlCard);
    show(empty);
  } else {
    hide(hitlCard);
    hide(empty);
  }
}

function updateContextPanelForSection(sectionKey) {
  const layout = document.querySelector('.workspace-layout');
  const panel = $('context-panel');
  const primary = $('ctx-primary-action');
  const quick = $('ctx-quick-actions');
  const showOpsPanel = sectionKey === 'operations';
  const showSimPanel = sectionKey === 'simulation' && pendingThread;

  if (layout) layout.classList.toggle('no-context', !(showOpsPanel || showSimPanel));
  if (panel) panel.classList.toggle('hidden', !(showOpsPanel || showSimPanel));

  if (showOpsPanel) {
    show(primary);
    show(quick);
  } else {
    hide(primary);
    hide(quick);
  }

  if (showSimPanel) {
    show(panel);
    show($('ctx-hitl-card'));
    hide(primary);
    hide(quick);
    hide($('ctx-empty'));
  }

  updateContextPanel();
}

function bindActionRipples() {
  document.querySelectorAll('.btn-primary, .btn-success, .btn-outline, .btn-danger, .nav-dock .nav-item, .tool-tile, .quick-action-btn').forEach((el) => {
    el.addEventListener('click', (e) => createRipple(el, e));
  });
}

function setButtonLoading(btn, loading) {
  if (!btn) return;
  btn.classList.toggle('is-loading', loading);
  btn.disabled = loading;
}

function playSuccessBurst(el) {
  if (!el) return;
  el.classList.remove('success-burst');
  void el.offsetWidth;
  el.classList.add('success-burst');
}

function initMacNav() {
  const logo = $('sidebar-logo');
  if (logo) logo.innerHTML = `<span class="mac-icon-shine"></span>${ICONS.logo}`;

  document.querySelectorAll('.nav-dock .nav-item[data-section]').forEach((btn) => {
    if (btn.querySelector('.mac-icon')) return;
    const iconName = SECTION_ICONS[btn.dataset.section] || 'sparkles';
    btn.insertAdjacentHTML('afterbegin', macIcon(iconName, 'sm'));
  });
}

function populateToolTile(el, key, label) {
  if (!el) return;
  el.innerHTML = `${toolLogo(key, 'sm')}<span class="tool-name">${label}</span>${icon('arrow', 'icon icon-xs tool-arrow')}`;
  el.setAttribute('aria-label', `Open ${label}`);
}

function hostLabel(url) {
  try {
    return new URL(url, window.location.origin).host;
  } catch (_) {
    return url || '';
  }
}

function designExplore(d) {
  if (Array.isArray(d?.explore) && d.explore.length) return d.explore;
  return (d?.tiles || []).map((t) => ({ key: t.key, label: t.label, url: $(t.id)?.href || '#', role: t.key }));
}

function exploreByRole(d, role) {
  return designExplore(d).find((t) => t.role === role) || null;
}

function setNativeHref(id, url) {
  const el = $(id);
  if (!el || !url) return;
  el.href = url;
  el.target = '_blank';
  el.rel = 'noopener';
}

function applyDesignNativeLinks(d, items) {
  const byRole = (role) => (items || designExplore(d)).find((t) => t.role === role);
  const metrics = byRole('metrics');
  const logs = byRole('logs');
  const dashboards = byRole('dashboards');
  const llmops = byRole('llmops');
  const evals = byRole('evals');
  setNativeHref('obs-link-prometheus', metrics?.url);
  setNativeHref('link-prometheus-alert', metrics?.url);
  setNativeHref('obs-link-loki', logs?.url);
  setNativeHref('obs-link-grafana', dashboards?.url);
  setNativeHref('link-grafana-alert', dashboards?.url);
  setNativeHref('link-langfuse-dashboard', llmops?.url);
  setNativeHref('link-langfuse-scores', llmops?.url);
  setNativeHref('link-trace', llmops?.url);
  setNativeHref('link-trace-eval', llmops?.url);
  setNativeHref('link-eval-langfuse', llmops?.url);
  setNativeHref('link-mlflow-eval', evals?.url);
  setNativeHref('link-eval-mlflow', evals?.url);
  if (d?.policyUrl) {
    setNativeHref('link-opa-console', d.policyUrl);
    setNativeHref('grd-link-opa', d.policyUrl);
  }
}

function renderStackExplore() {
  const d = typeof getArchDesign === 'function' ? getArchDesign() : null;
  if (!d) return;
  const items = designExplore(d);
  const sidebarItems = items.filter((t) => t.sidebar !== false);
  const grid = $('oss-tools-grid');
  if (grid) {
    grid.innerHTML = sidebarItems.map((t) => {
      const url = t.url || '#';
      const host = t.urlLabel || (t.url ? hostLabel(t.url) : '');
      return `<a class="tool-tile" href="${url}" ${t.url ? 'target="_blank" rel="noopener"' : ''} data-explore-key="${t.key}" data-explore-role="${t.role || ''}" data-testid="explore-${t.role || t.key}" title="${escapeHtml(t.hover || t.hint || t.label)}">
        ${typeof toolLogo === 'function' ? toolLogo(t.key, 'sm') : ''}
        <span class="tool-name">${t.label}</span>
        ${host ? `<span class="tool-url">${host}</span>` : ''}
        ${t.hint ? `<span class="tool-hint">${escapeHtml(t.hint)}</span>` : ''}
        <span class="tool-hover">${escapeHtml(t.hover || t.hint || t.label)}</span>
        ${typeof icon === 'function' ? icon('arrow', 'icon icon-xs tool-arrow') : ''}
      </a>`;
    }).join('');
    grid.dataset.ready = sidebarItems.length ? '1' : '0';
  }
  const exploreGrid = $('stack-explore-grid');
  if (exploreGrid) {
    exploreGrid.innerHTML = items.map((t) => {
      const url = t.url;
      const attrs = url ? `href="${url}" target="_blank" rel="noopener"` : 'href="#"';
      return `<a class="stack-explore-item" ${attrs} title="${escapeHtml(t.hover || t.hint || t.label)}">
        ${typeof toolLogo === 'function' ? toolLogo(t.key, 'sm') : ''}
        <strong>${t.label}</strong>
        <span class="muted">${t.hint || ''}</span>
        <code>${t.urlLabel || (url ? hostLabel(url) : 'In-console explorer')}</code>
      </a>`;
    }).join('');
  }
  applyDesignNativeLinks(d, items);
  const vector = items.find((t) => t.role === 'vector');
  const vecBtn = $('link-vector-native');
  const vecUrl = $('vector-native-url');
  if (vecBtn) {
    const name = (vector?.label || d.vector || 'vector DB').replace(/\s+console$/i, '');
    vecBtn.textContent = `Open ${name} ↗`;
    const href = vector?.url || d.vectorUrl;
    if (href) {
      vecBtn.href = href;
      vecBtn.classList.remove('hidden');
    } else {
      vecBtn.classList.add('hidden');
    }
  }
  if (vecUrl) {
    vecUrl.textContent = vector?.urlLabel || vector?.url || d.vectorUrl || 'No standalone UI — use this explorer';
  }
  const evalGrid = $('eval-tools-grid');
  if (evalGrid) {
    evalGrid.innerHTML = items.map((t) => {
      const url = t.url || '#';
      return `<a class="tool-tile tool-tile-lg card-lift" href="${url}" ${t.url ? 'target="_blank" rel="noopener"' : ''}>
        ${typeof toolLogo === 'function' ? toolLogo(t.key, 'md') : ''}
        <span class="tool-name">${t.label}</span>
        <span class="tool-desc">${t.urlLabel || (t.url ? hostLabel(t.url) : 'In-console')} ↗</span>
      </a>`;
    }).join('');
    evalGrid.dataset.ready = '1';
  }
  const strip = $('oss-logo-strip');
  if (strip) {
    strip.innerHTML = sidebarItems.map((t) => `
      <a class="oss-logo-chip" href="${t.url || '#'}" ${t.url ? 'target="_blank" rel="noopener"' : ''} aria-label="${t.label}">
        ${typeof toolLogo === 'function' ? toolLogo(t.key, 'sm') : ''}<span>${t.label}</span>
      </a>`).join('');
    strip.dataset.ready = '1';
  }
}

function archStack(key, fallback) {
  if (typeof getArchDesign !== 'function') return fallback;
  return getArchDesign()[key] || fallback;
}

function applyArchRuntimeLabels(d) {
  const v = d.vector;
  const logs = d.logs;
  const metrics = d.metrics;
  const policy = d.policy;
  const llmops = d.llmops;
  const logsW = MULTI_GRAPH_STEPS.find((s) => s.id === 'logs_worker');
  if (logsW) logsW.sub = `${logs} investigation`;
  const metW = MULTI_GRAPH_STEPS.find((s) => s.id === 'metrics_worker');
  if (metW) metW.sub = `${metrics} metrics`;
  const orchRb = ORCH_WORKERS.find((s) => s.id === 'runbook_worker');
  if (orchRb) orchRb.role = `${v} RAG`;
  const orchLogs = ORCH_WORKERS.find((s) => s.id === 'logs_worker');
  if (orchLogs) orchLogs.role = `${logs} query`;
  const orchMet = ORCH_WORKERS.find((s) => s.id === 'metrics_worker');
  if (orchMet) orchMet.role = metrics;
  const treeRb = MULTI_AGENT_TREE.find((s) => s.id === 'runbook_worker');
  if (treeRb) treeRb.role = `${v} RAG retrieval`;
  const treeLogs = MULTI_AGENT_TREE.find((s) => s.id === 'logs_worker');
  if (treeLogs) treeLogs.role = `${logs} error patterns`;
  const treeMet = MULTI_AGENT_TREE.find((s) => s.id === 'metrics_worker');
  if (treeMet) treeMet.role = `${metrics} CPU / latency`;
  const tools = MCP_ARCH_TREE.children?.[0]?.children?.[0]?.children;
  if (Array.isArray(tools)) {
    tools.forEach((t) => {
      if (t.id === 'tool-logs') t.role = `→ ${logs}`;
      if (t.id === 'tool-runbooks') t.role = `→ ${v} RAG`;
      if (t.id === 'tool-metrics') t.role = `→ ${metrics}`;
    });
  }
  MCP_TOOL_META.query_logs.backend = logs;
  MCP_TOOL_META.retrieve_runbooks.backend = v;
  MCP_TOOL_META.get_metrics.backend = metrics;
  MCP_TOOL_META.check_opa_policy.backend = policy;
  MCP_TOOL_META.check_opa_policy.desc = `Evaluate recommendation against ${policy}`;
  MCP_TOOL_META.list_policy_rules.backend = policy;
  MCP_TOOL_META.list_policy_rules.desc = `List ${d.name} guardrail rules`;
  MCP_TOOL_META.preview_hitl_gate.backend = `${policy} + HITL`;
  MULTI_DELEGATION_PREVIEW.forEach((row) => {
    if (row.from === 'triage_worker') row.message = `Fetch runbook context via ${v} RAG`;
    if (row.from === 'runbook_worker') row.message = `Investigate logs in ${logs}`;
    if (row.from === 'logs_worker') row.message = `Pull ${metrics} metrics for anomaly confirmation`;
  });
  if (SECTIONS.simulation) {
    SECTIONS.simulation.subtitle = `Simulated alert remediation · ${policy} · HITL gate`;
    const tab = SECTIONS.simulation.tabs.find((t) => t.id === 'auto-opa');
    if (tab) tab.label = `${policy}`;
  }
  if (SECTIONS.guardrails) {
    SECTIONS.guardrails.subtitle = `${policy} console · audit log · live policy editor`;
  }
  if (SECTIONS.evaluation) {
    const tab = SECTIONS.evaluation.tabs.find((t) => t.id === 'eval-trace');
    if (tab) tab.label = `${llmops} Trace`;
  }
  if (typeof ALERT_PHASE_LABELS !== 'undefined') ALERT_PHASE_LABELS.guardrails = policy;
  if ($('link-opa-console')) {
    $('link-opa-console').textContent = d.policyConsole || `Open ${policy}`;
    if (d.policyUrl) $('link-opa-console').href = d.policyUrl;
  }
  if ($('grd-link-opa')) {
    $('grd-link-opa').textContent = d.policyConsole || `Open ${policy}`;
    if (d.policyUrl) $('grd-link-opa').href = d.policyUrl;
  }
  if ($('link-prometheus-alert')) $('link-prometheus-alert').textContent = metrics;
  const lfDash = $('link-langfuse-dashboard');
  if (lfDash) {
    const shine = lfDash.querySelector('.btn-shine');
    lfDash.innerHTML = `${shine ? '<span class="btn-shine"></span>' : ''}Open ${llmops}`;
  }
  if ($('link-langfuse-scores')) $('link-langfuse-scores').textContent = `${llmops} Scores`;
  const lfTrace = $('link-trace-eval');
  if (lfTrace) lfTrace.textContent = `Open ${llmops}`;
  const hitlTrace = $('obs-hitl-open-trace');
  if (hitlTrace) hitlTrace.textContent = `View ${llmops} trace`;
  if ($('grd-policy-save')) {
    const shine = $('grd-policy-save').querySelector('.btn-shine');
    $('grd-policy-save').innerHTML = `${shine ? '<span class="btn-shine"></span>' : ''}Save &amp; reload ${policy}`;
  }
}

function applyArchDesignContext() {
  if (typeof getArchDesign !== 'function') return;
  const d = getArchDesign();
  if (!d) {
    console.warn('Architecture design pack missing — sidebar stack tiles will stay empty');
    return;
  }
  const live = typeof isArchDesignLive === 'function' ? isArchDesignLive(d.id) : d.id === ARCH_LIVE_ID;
  const toolsUp = typeof isArchToolsUp === 'function' ? isArchToolsUp(d.id) : live;
  applyArchRuntimeLabels(d);
  if (typeof applyArchCopy === 'function') applyArchCopy();
  document.querySelectorAll('#design-switch [data-design]').forEach((btn) => {
    btn.classList.toggle('on', btn.dataset.design === d.id);
    btn.setAttribute('aria-pressed', btn.dataset.design === d.id ? 'true' : 'false');
  });
  const sub = `${d.name} · ${d.stack}`;
  const headerSub = $('header-design-sub');
  const sideSub = $('sidebar-design-sub');
  if (headerSub) headerSub.textContent = sub;
  if (sideSub) sideSub.textContent = live ? 'Live console' : 'Compare mode';
  const pill = document.querySelector('.env-pill');
  if (pill) pill.textContent = live ? `Live · ${d.name}` : `Compare · ${d.name}`;
  const banner = $('design-banner');
  if (banner) {
    banner.hidden = false;
    banner.classList.toggle('is-compare', !live);
    banner.innerHTML = live
      ? `<strong>${d.name} live</strong> <span>${d.stack}</span> <button type="button" class="btn-ghost btn-sm" data-open-designs>Compare D1 / D3</button>`
      : toolsUp
        ? `<strong>${d.name} tool UIs are up</strong> <span>Open native dashboards from the sidebar. Agent/RAG data is still Design 2 until you switch the live backend. <code>${d.deploy}</code></span> <button type="button" class="btn-ghost btn-sm" data-open-designs>Why this stack?</button>`
        : `<strong>${d.name} — not deployed on this laptop</strong> <span>Live data is Design 2 (Weaviate / Elasticsearch / VictoriaMetrics / Phoenix). This switcher is compare mode. Bring it up with <code>${d.deploy}</code></span> <button type="button" class="btn-ghost btn-sm" data-open-designs>Why this stack?</button>`;
    banner.querySelector('[data-open-designs]')?.addEventListener('click', () => {
      if (window.switchSection) window.switchSection('learning', 'learn-designs');
    });
  }
  if (SECTIONS.ingestion) {
    const tab = SECTIONS.ingestion.tabs.find((t) => t.id === 'ing-jobs');
    if (tab) tab.label = d.ingestTab;
    SECTIONS.ingestion.subtitle = `${d.vector} · ${d.logs} · ${d.metrics}`;
  }
  if (SECTIONS.observability) {
    SECTIONS.observability.subtitle = `Signals → ${d.vector} RAG → ${d.policy} → HITL`;
  }
  if (SECTIONS.evaluation) {
    SECTIONS.evaluation.subtitle = d.evals || `${d.llmops} · ${d.traces} · MLflow`;
  }
  const explorer = $('vector-explorer-title');
  if (explorer) explorer.textContent = d.explorer;
  renderStackExplore();
  if (currentSection && SECTIONS[currentSection]) {
    const cfg = SECTIONS[currentSection];
    const title = $('page-title');
    const subtitle = $('page-subtitle');
    if (title) title.textContent = cfg.title;
    if (subtitle) subtitle.textContent = cfg.subtitle;
    renderSectionTabs(currentSection);
    document.querySelectorAll('.workspace-tab').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tab === currentTab);
    });
  }
  if (typeof renderLearningTip === 'function' && currentSection) {
    renderLearningTip(currentSection, currentTab);
  }
  if (currentSection === 'observability' && typeof previewAlertFlow === 'function') {
    previewAlertFlow(false, { silent: true });
  }
}

function initArchDesignSwitcher() {
  document.getElementById('design-switch')?.querySelectorAll('[data-design]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (typeof setArchDesignId === 'function') setArchDesignId(btn.dataset.design);
    });
  });
  window.addEventListener('agentops-design-change', () => applyArchDesignContext());
  applyArchDesignContext();
}

function initToolTiles() {
  renderStackExplore();
}

function syncEvalToolLinks() {
  renderStackExplore();
}

function updateTabIndicator() {
  const indicator = $('tab-indicator');
  const active = document.querySelector('.workspace-tab.active');
  const shell = document.querySelector('.tabs-shell');
  if (!indicator || !active || !shell) return;
  const shellRect = shell.getBoundingClientRect();
  const tabRect = active.getBoundingClientRect();
  indicator.style.width = `${tabRect.width}px`;
  indicator.style.transform = `translateX(${tabRect.left - shellRect.left}px)`;
}

async function updateQuickStats() {
  await loadDashboardStats();
  updateContextPanel();
}

function updatePageChrome(sectionKey) {
  const stats = $('quick-stats');
  const pageHead = document.querySelector('.page-head');
  if (stats) {
    stats.classList.toggle('hidden', sectionKey !== 'operations');
    if (sectionKey === 'operations') {
      stats.classList.remove('stats-reveal');
      void stats.offsetWidth;
      stats.classList.add('stats-reveal');
    } else {
      stats.classList.remove('stats-reveal');
    }
  }
  if (pageHead) {
    pageHead.classList.toggle('ops-live', sectionKey === 'operations' && $('ops-pipeline-card')?.classList.contains('is-live'));
  }
}

function setPipelineLiveMode(live) {
  const card = $('ops-pipeline-card');
  if (card) card.classList.toggle('is-live', live);
  const pageHead = document.querySelector('.page-head');
  if (pageHead && currentSection === 'operations') {
    pageHead.classList.toggle('ops-live', live);
  }
  if (!live) {
    document.querySelectorAll('.pipeline-flow-particle').forEach((p) => p.classList.remove('run'));
  }
}

function pulsePipelineParticles() {
  document.querySelectorAll('.pipeline-flow-particle').forEach((p) => {
    p.classList.remove('run');
    void p.offsetWidth;
    p.classList.add('run');
  });
}

const IS_CAPTURE = new URLSearchParams(window.location.search).has('capture');

async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401) {
    if (!IS_CAPTURE) logout();
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function logout() {
  token = null;
  currentUser = null;
  closeUserMenu();
  localStorage.removeItem('aiops_token');
  hide($('app-screen'));
  show($('login-screen'));
}

function replayClass(el, cls) {
  if (!el) return;
  el.classList.remove(cls);
  void el.offsetWidth;
  el.classList.add(cls);
}

function stampCardMotion(root) {
  if (!root) return;
  root.querySelectorAll('.glossy-card, .glass-card, .card').forEach((el, i) => {
    el.style.setProperty('--card-i', String(i));
  });
}

function animatePanel(panel) {
  if (!panel) return;
  stampCardMotion(panel);
  replayClass(panel, 'panel-enter');
}

function renderSectionTabs(sectionKey) {
  const cfg = SECTIONS[sectionKey];
  const nav = $('workspace-tabs');
  nav.innerHTML = '';
  cfg.tabs.forEach((tab, i) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `workspace-tab${tab.id === currentTab ? ' active' : ''}`;
    btn.dataset.tab = tab.id;
    btn.style.animationDelay = `${i * 40}ms`;
    btn.innerHTML = `<span class="tab-label">${tab.label}</span>`;
    btn.addEventListener('click', () => switchTab(tab.id));
    nav.appendChild(btn);
  });
  requestAnimationFrame(updateTabIndicator);
}

function switchSection(sectionKey, tabId) {
  currentSection = sectionKey;
  const cfg = SECTIONS[sectionKey];
  currentTab = tabId || cfg.tabs[0].id;
  document.body.dataset.section = sectionKey;
  document.documentElement.dataset.section = sectionKey;

  document.querySelectorAll('.nav-item[data-section]').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.section === sectionKey);
  });

  $('page-title').textContent = cfg.title;
  $('page-subtitle').textContent = cfg.subtitle;
  $('breadcrumb').textContent = cfg.breadcrumb;
  updatePageChrome(sectionKey);
  replayClass(document.querySelector('.page-head'), 'chrome-enter');
  replayClass(document.querySelector('.tabs-shell'), 'chrome-enter');
  replayClass(document.querySelector('.section-learning-tip'), 'chrome-enter');

  document.querySelectorAll('.section-panel').forEach((el) => hide(el));
  const sectionEl = $(`sec-${sectionKey}`);
  show(sectionEl);
  if (sectionEl) animatePanel(sectionEl);

  renderSectionTabs(sectionKey);
  switchTab(currentTab, false);

  if (sectionKey === 'simulation' && pendingChangeRun && pendingThread && !hitlResolved) {
    populateAutomation(pendingChangeRun.data, pendingChangeRun.context);
  }
  if (cfg.onEnter) cfg.onEnter();
  updateContextPanelForSection(sectionKey);
  updateQuickStats();
  if (typeof renderLearningTip === 'function') renderLearningTip(sectionKey, currentTab);
  requestAnimationFrame(updateTabIndicator);
}

function switchTab(tabId, animate = true) {
  currentTab = tabId;
  document.querySelectorAll('.workspace-tab').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  const section = $(`sec-${currentSection}`);
  if (!section) return;
  section.querySelectorAll('.tab-panel').forEach((panel) => {
    const visible = panel.id === `tab-${tabId}`;
    panel.classList.toggle('hidden', !visible);
    if (visible && animate) animatePanel(panel);
  });
  requestAnimationFrame(updateTabIndicator);
  if (tabId === 'ing-jobs') loadIngestIndex();
  if (tabId === 'ing-pipeline') startIngestFlowAnim();
  else stopIngestFlowAnim();
  if (tabId.startsWith('learn-') && typeof initLearningSection === 'function') initLearningSection(tabId);
  if (tabId.startsWith('grd-')) loadGuardrailsSection(tabId);
  if (tabId === 'eval-gate') loadEvalDashboard();
  if (tabId.startsWith('gov-')) loadGovernanceSection(tabId);
  if (tabId === 'obs-simulator') loadAlertFlowCatalog();
  if (tabId === 'auto-history') loadHitlHistory();
  if (tabId.startsWith('adm-')) loadAdminSection(tabId);
  if (tabId === 'ops-pipeline') {
    const live = !$('pipeline-running-pill')?.classList.contains('hidden')
      || $('ops-pipeline-card')?.classList.contains('is-live');
    if (live) setPipelineLiveMode(true);
  }
  if (tabId === 'ops-multi') loadMultiAgentTab();
  if (tabId === 'ops-mcp') loadMcpServerTab();
  if (tabId === 'mcp-playground') initMcpPlayground();
  if (tabId === 'mcp-skills') initSkillsCatalog();
  if (tabId === 'mcp-vs-skills') renderMcpVsSkillsGuide();
  if (typeof renderLearningTip === 'function') renderLearningTip(currentSection, tabId);
}

function initPipelineUI() {
  const container = $('pipeline-steps');
  if (!container) return;
  container.innerHTML = '';
  getActivePipelineSteps().forEach((step) => {
    const div = document.createElement('div');
    div.className = 'step';
    div.id = `step-${step.id}`;
    div.innerHTML = `
      <span class="step-check">${icon('check', 'icon icon-sm')}</span>
      <div class="step-icon">${icon(step.icon, 'icon icon-lg')}</div>
      <div class="step-name">${step.label}</div>
      <div class="step-result">—</div>
      <div class="step-sub">${step.sub}</div>`;
    container.appendChild(div);
  });
  $('progress-fill').style.width = '0%';
  $('pipeline-status-text').textContent = 'Waiting to run';
}

function updatePipeline(data, activeIndex) {
  const steps = getActivePipelineSteps();
  steps.forEach((step, i) => {
    const el = $(`step-${step.id}`);
    if (!el) return;
    el.classList.remove('active', 'done', 'waiting');
    el.style.animationDelay = `${i * 0.05}s`;
    const resultEl = el.querySelector('.step-result');
    if (i < activeIndex) {
      el.classList.add('done');
      resultEl.textContent = step.result(data);
    } else if (i === activeIndex) {
      el.classList.add(data.status === 'awaiting_hitl' && (step.id === 'hitl_gate' || step.id === 'hitl') ? 'waiting' : 'active');
      resultEl.textContent = step.result(data);
    } else {
      resultEl.textContent = '—';
    }
  });
  const pct = Math.round(((activeIndex + 1) / steps.length) * 100);
  $('progress-fill').style.width = `${pct}%`;
  $('pipeline-status-text').textContent = data.status === 'awaiting_hitl'
    ? `Step ${steps.length} of ${steps.length} — Waiting for human approval`
    : `Step ${activeIndex + 1} of ${steps.length}`;
  const isLive = data.status === 'awaiting_hitl' || !$('pipeline-running-pill')?.classList.contains('hidden');
  setPipelineLiveMode(isLive);
  if ($('pipeline-flow-progress')) {
    $('pipeline-flow-progress').style.width = `${Math.min(100, Math.round((activeIndex / Math.max(steps.length - 1, 1)) * 100))}%`;
  }
}

function startTimer() {
  pipelineStart = Date.now();
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const s = Math.floor((Date.now() - pipelineStart) / 1000);
    const el = $('pipeline-timer');
    if (el) {
      el.textContent = `${String(Math.floor(s / 3600)).padStart(2, '0')}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
      el.classList.remove('timer-tick');
      void el.offsetWidth;
      el.classList.add('timer-tick');
    }
  }, 1000);
}

function stopTimer() {
  if (timerInterval) clearInterval(timerInterval);
}

async function loadOpaPolicyText() {
  if (opaPolicyLoaded || IS_CAPTURE) return;
  try {
    const data = await api('/api/guardrails/opa/policy');
    if ($('opa-rego-source')) $('opa-rego-source').textContent = data.rego || '—';
    opaPolicyLoaded = true;
  } catch (_) {
    if ($('opa-rego-source')) $('opa-rego-source').textContent = 'Unable to load policy.rego';
  }
}

function setOpaBadge(state, text) {
  const el = $('opa-policy-badge');
  if (!el) return;
  el.textContent = text;
  el.classList.remove('opa-allow', 'opa-deny', 'opa-checking', 'glow-badge');
  if (state === 'checking') el.classList.add('opa-checking', 'glow-badge');
  else if (state === 'allow') el.classList.add('opa-allow', 'glow-badge');
  else if (state === 'deny') el.classList.add('opa-deny', 'glow-badge');
}

function isHitlUiResolved() {
  return hitlResolved || $('automation-banner')?.classList.contains('resolved');
}

function setHitlApprovalState(state) {
  if (isHitlUiResolved()) return;
  const checking = state === 'checking';
  const allowed = state === 'allowed';
  const denied = state === 'denied';

  [
    ['opspilot-approve', 'opspilot-blocked-msg', 'opspilot-view-opa'],
    ['ctx-approve', 'ctx-blocked-msg', 'ctx-view-opa'],
  ].forEach(([approveId, blockedId, viewId]) => {
    const approve = $(approveId);
    const blocked = $(blockedId);
    const viewOpa = $(viewId);
    if (checking) {
      hide(approve);
      hide(blocked);
      hide(viewOpa);
    } else if (denied) {
      hide(approve);
      show(blocked);
      show(viewOpa);
    } else {
      show(approve);
      hide(blocked);
      hide(viewOpa);
      if (approve) approve.disabled = false;
    }
  });

  const banner = $('automation-banner');
  if (banner) {
    banner.classList.toggle('policy-blocked', denied);
    const strong = banner.querySelector('.approval-body strong');
    if (strong) {
      if (denied) strong.textContent = `${archStack('policy', 'OPA')} policy blocked this remediation`;
      else if (checking) strong.textContent = `Evaluating ${archStack('policy', 'OPA')} policy…`;
      else strong.textContent = 'Human approval required (simulated HITL gate)';
    }
  }

  const statusBadge = $('cr-status-badge');
  if (statusBadge && denied) {
    const policy = archStack('policy', 'OPA');
    statusBadge.textContent = `Blocked by ${policy}`;
    statusBadge.className = 'badge opa-deny';
    pushNotification({
      type: 'error',
      title: `${policy} policy denied remediation`,
      message: 'Destructive action blocked for current severity — review Guardrails.',
      action: { section: 'guardrails', tab: 'grd-audit' },
      dedupeKey: pendingThread ? `opa-deny-${pendingThread}` : 'opa-deny',
    });
  } else if (statusBadge && allowed) {
    statusBadge.textContent = 'Awaiting approval';
    statusBadge.className = 'badge warn';
  }
}

function renderOpaPanel(result) {
  if (!result) return;
  const allowed = result.allowed;
  const verdict = $('opa-verdict-text');
  if (verdict) {
    verdict.textContent = allowed
      ? `${archStack('policy', 'OPA')} allows this remediation — approve will proceed to ticket-api (after HITL).`
      : `${archStack('policy', 'OPA')} denies this remediation — approval will be blocked at execute step.`;
    verdict.className = `opa-verdict-text ${allowed ? 'opa-text-allow' : 'opa-text-deny'}`;
  }
  if ($('opa-allowed')) $('opa-allowed').textContent = allowed ? 'Yes' : 'No';
  if ($('opa-reason')) $('opa-reason').textContent = result.reason || '—';
  if ($('opa-matched-rule')) $('opa-matched-rule').textContent = result.matched_rule || '—';
  if ($('opa-destructive')) $('opa-destructive').textContent = result.destructive ? 'Yes' : 'No';
  if ($('opa-input-json')) $('opa-input-json').textContent = JSON.stringify(result.input || {}, null, 2);
  if ($('opa-flow-rec')) $('opa-flow-rec').textContent = (result.input?.recommendation || '—').slice(0, 80);
  if ($('opa-flow-status')) $('opa-flow-status').textContent = allowed ? 'Allow' : 'Deny';
  if ($('opa-flow-hitl')) {
    $('opa-flow-hitl').textContent = allowed ? 'Awaiting operator' : 'Blocked by policy';
  }

  const rulesEl = $('opa-rules-list');
  if (rulesEl && result.rules) {
    rulesEl.innerHTML = result.rules.map((r) => {
      const active = r.id === result.matched_rule;
      return `<li class="opa-rule ${active ? 'active' : ''}"><span class="opa-rule-effect ${r.effect}">${r.effect}</span>${escapeHtml(r.label)}${active ? ' <em>(matched)</em>' : ''}</li>`;
    }).join('');
  }

  const anim = $('opa-flow-anim');
  if (anim) {
    anim.classList.remove('is-evaluating', 'is-allow', 'is-deny');
    void anim.offsetWidth;
    anim.classList.add('is-evaluating', allowed ? 'is-allow' : 'is-deny');
  }

  setOpaBadge(allowed ? 'allow' : 'deny', allowed ? `✓ ${archStack('policy', 'OPA')}: allow (${result.matched_rule})` : `✗ ${archStack('policy', 'OPA')}: deny (${result.matched_rule})`);
  if (!isHitlUiResolved()) setHitlApprovalState(allowed ? 'allowed' : 'denied');
}

async function evaluateOpaPolicy(context = {}, recommendation = '') {
  const seq = ++opaEvalSeq;
  const service = context.service || $('service')?.value || '';
  const severity = context.severity || $('severity')?.value || 'P1';
  const rec = recommendation || context.recommendation || $('cr-recommendation')?.textContent || '';
  if (!rec || rec === '—') return null;

  setOpaBadge('checking', `${archStack('policy', 'OPA')}: evaluating…`);
  setHitlApprovalState('checking');
  const anim = $('opa-flow-anim');
  anim?.classList.add('is-evaluating');

  try {
    await loadOpaPolicyText();
    const result = IS_CAPTURE
      ? {
        allowed: severity === 'P1',
        reason: 'policy_allow',
        destructive: /restart|rollback|kill|delete|scale-down/i.test(rec),
        severity,
        service,
        matched_rule: severity === 'P1' ? 'allow_p1_destructive' : 'deny_destructive_not_p1',
        input: { service, severity, recommendation: rec },
        rules: [
          { id: 'allow_non_destructive', label: 'Non-destructive recommendation', effect: 'allow' },
          { id: 'allow_p1_destructive', label: 'Destructive action + P1 severity', effect: 'allow' },
          { id: 'deny_destructive_not_p1', label: 'Destructive action on P2/P3', effect: 'deny' },
        ],
      }
      : await api('/api/guardrails/opa/evaluate', {
        method: 'POST',
        body: JSON.stringify({
          service,
          severity,
          recommendation: rec,
          thread_id: pendingThread || null,
          source: 'hitl_preview',
          record: true,
        }),
      });
    lastOpaEvaluation = result;
    if (seq !== opaEvalSeq || isHitlUiResolved()) return result;
    renderOpaPanel(result);
    return result;
  } catch (err) {
    setOpaBadge('deny', `${archStack('policy', 'OPA')}: unavailable`);
    setHitlApprovalState('denied');
    showToast('error', `${archStack('policy', 'OPA')} check failed`, err.message);
    return null;
  }
}

function formatAuditTime(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (_) {
    return iso;
  }
}

function renderGrdRules(rules) {
  const el = $('grd-rules-list');
  if (!el || !rules) return;
  el.innerHTML = rules.map((r) => `
    <li class="opa-rule">
      <span class="opa-rule-effect ${r.effect}">${r.effect}</span>
      ${escapeHtml(r.label)}
      <code class="grd-rule-id">${r.id}</code>
    </li>`).join('');
}

function renderGrdKeywords(keywords) {
  const el = $('grd-keywords');
  if (!el) return;
  el.innerHTML = (keywords || []).map((k) => `<span class="grd-kw-tag">${escapeHtml(k)}</span>`).join('');
}

function renderGrdStats(stats) {
  if (!stats) return;
  if ($('grd-stat-total')) $('grd-stat-total').textContent = stats.total ?? '0';
  if ($('grd-stat-allowed')) $('grd-stat-allowed').textContent = stats.allowed ?? '0';
  if ($('grd-stat-denied')) $('grd-stat-denied').textContent = stats.denied ?? '0';
  if ($('grd-stat-24h')) $('grd-stat-24h').textContent = stats.last_24h ?? '0';
  renderGrdRules(stats.rules);
  renderGrdKeywords(stats.destructive_keywords);
  const last = $('grd-last-eval');
  if (last && stats.last_evaluation) {
    const e = stats.last_evaluation;
    last.textContent = `Last: ${e.allowed ? 'ALLOW' : 'DENY'} · ${e.service || '—'} · ${e.severity || '—'} · ${formatAuditTime(e.evaluated_at)} (${e.source})`;
    last.className = `grd-last-eval ${e.allowed ? 'opa-text-allow' : 'opa-text-deny'}`;
  }
}

async function loadGrdOverview() {
  try {
    const stats = await api('/api/guardrails/opa/stats');
    renderGrdStats(stats);
    $('grd-flow-static')?.classList.add('is-evaluating');
  } catch (err) {
    showToast('error', 'Guardrails stats failed', err.message);
  }
}

function renderGrdAuditRows(rows) {
  const body = $('grd-audit-body');
  if (!body) return;
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="muted">No evaluations yet — run a simulated alert or use the policy sandbox.</td></tr>';
    return;
  }
  body.innerHTML = rows.map((row) => `
    <tr class="grd-audit-row ${row.allowed ? 'is-allow' : 'is-deny'}">
      <td>${formatAuditTime(row.evaluated_at)}</td>
      <td><span class="badge ${row.allowed ? 'opa-allow' : 'opa-deny'}">${row.allowed ? 'Allow' : 'Deny'}</span></td>
      <td>${escapeHtml(row.service || '—')}</td>
      <td>${escapeHtml(row.severity || '—')}</td>
      <td><code>${escapeHtml(row.matched_rule || '—')}</code></td>
      <td>${escapeHtml(row.source || '—')}</td>
      <td class="grd-rec-cell" title="${escapeHtml(row.recommendation || '')}">${escapeHtml((row.recommendation || '—').slice(0, 72))}${(row.recommendation || '').length > 72 ? '…' : ''}</td>
    </tr>`).join('');
}

async function loadGrdAudit(verdict = grdAuditVerdict) {
  grdAuditVerdict = verdict;
  document.querySelectorAll('.grd-filter').forEach((btn) => {
    btn.classList.toggle('active', (btn.dataset.verdict || '') === verdict);
  });
  const qs = verdict ? `?verdict=${encodeURIComponent(verdict)}` : '';
  try {
    const data = await api(`/api/guardrails/opa/evaluations${qs}`);
    renderGrdAuditRows(data.evaluations || []);
  } catch (err) {
    if ($('grd-audit-body')) $('grd-audit-body').innerHTML = `<tr><td colspan="7" class="muted">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderGrdRevisions(revisions) {
  const el = $('grd-revisions-list');
  if (!el) return;
  if (!revisions?.length) {
    el.innerHTML = '<li class="muted">No saved revisions yet.</li>';
    return;
  }
  el.innerHTML = revisions.map((r) => `
    <li>
      <strong>${formatAuditTime(r.saved_at)}</strong>
      <span class="muted">by ${escapeHtml(r.saved_by || '—')}</span>
      ${r.note ? `<div class="muted">${escapeHtml(r.note)}</div>` : ''}
    </li>`).join('');
}

async function loadGrdEditor() {
  try {
    const data = await api('/api/guardrails/opa/policy');
    grdPolicyDraft = data.rego || '';
    if ($('grd-rego-editor')) $('grd-rego-editor').value = grdPolicyDraft;
    renderGrdKeywords(data.destructive_keywords);
    renderGrdRevisions(data.revisions || []);
  } catch (err) {
    showToast('error', 'Policy load failed', err.message);
  }
}

function renderGrdTestResult(result) {
  const el = $('grd-test-result');
  if (!el || !result) return;
  el.innerHTML = `
    <p class="${result.allowed ? 'opa-text-allow' : 'opa-text-deny'}"><strong>${result.allowed ? 'ALLOW' : 'DENY'}</strong> · ${escapeHtml(result.matched_rule || '')}</p>
    <dl class="meta-list compact">
      <div><dt>Destructive</dt><dd>${result.destructive ? 'Yes' : 'No'}</dd></div>
      <div><dt>Reason</dt><dd>${escapeHtml(result.reason || '—')}</dd></div>
    </dl>`;
}

async function runGrdSandboxTest() {
  const service = $('grd-test-service')?.value || '';
  const severity = $('grd-test-severity')?.value || 'P3';
  const recommendation = $('grd-test-recommendation')?.value || '';
  try {
    const result = await api('/api/guardrails/opa/evaluate', {
      method: 'POST',
      body: JSON.stringify({ service, severity, recommendation, source: 'sandbox', record: false }),
    });
    renderGrdTestResult(result);
  } catch (err) {
    showToast('error', 'Sandbox test failed', err.message);
  }
}

async function saveGrdPolicy() {
  const rego = $('grd-rego-editor')?.value || '';
  const note = $('grd-save-note')?.value || '';
  if (!rego.trim()) {
    showToast('warning', 'Empty policy', 'Add Rego before saving.');
    return;
  }
  try {
    const saved = await api('/api/guardrails/opa/policy', {
      method: 'PUT',
      body: JSON.stringify({ rego, note: note || null }),
    });
    grdPolicyDraft = rego;
    opaPolicyLoaded = false;
    showToast('success', 'Policy saved', `${archStack('policy', 'OPA')} reloaded with live rules.`);
    if ($('grd-save-note')) $('grd-save-note').value = '';
    await loadGrdEditor();
    await loadGrdOverview();
  } catch (err) {
    showToast('error', 'Save failed', err.message);
  }
}

function loadGuardrailsSection(tabId) {
  if (tabId === 'grd-audit') loadGrdAudit();
  else if (tabId === 'grd-editor') loadGrdEditor();
  else loadGrdOverview();
}

function resolveApprovalScenario(data, context = {}) {
  const ctxService = context.service || $('service')?.value;
  const active = getActiveScenario();
  const simulated = active?.payload?.service && ctxService === active.payload.service ? active : null;
  const agentRunbookId = data.runbook_id;
  const scenario = simulated || scenarioByRunbookId(agentRunbookId) || active;
  const mismatch = Boolean(simulated && agentRunbookId && agentRunbookId !== simulated.runbook_id);
  return { scenario, simulated, agentRunbookId, mismatch };
}

function populateAutomation(data, context = {}) {
  hitlResolved = false;
  opaEvalSeq += 1;
  if ($('hitl-decision-comment')) $('hitl-decision-comment').value = '';
  if ($('ctx-hitl-comment')) $('ctx-hitl-comment').value = '';
  const cr = changeRunId(data.thread_id);
  const { scenario, simulated, agentRunbookId, mismatch } = resolveApprovalScenario(data, context);
  const p = scenario?.payload || context;
  const displayRunbookId = simulated?.runbook_id || agentRunbookId || scenario?.runbook_id || 'checkout-redis-pool';

  $('cr-id').textContent = `#${cr}`;
  $('cr-meta-id').textContent = cr;
  $('cr-service').textContent = context.service || p.service || '—';
  $('cr-impacted-service').textContent = context.service || p.service || '—';
  $('cr-dependency').textContent = scenario?.dependency || '—';
  $('cr-blast-radius').textContent = scenario?.blast_radius || '—';
  $('cr-priority').textContent = context.severity || p.severity || 'P1';
  $('cr-triggered').textContent = $('user-badge').textContent || 'AgentOps pipeline';
  $('cr-created').textContent = formatNow();
  $('cr-recommendation').textContent = data.recommendation || 'Sensitive production change requires operator approval.';

  let rationale = scenario?.summary || data.recommendation || '—';
  if (data.classification) {
    rationale = `Classification: ${data.classification}. Simulated scenario “${simulated?.label || scenario?.label || displayRunbookId}”. Runbook ${displayRunbookId} via ${archStack('vector', 'Chroma')} RAG.`;
  }
  if (mismatch) {
    rationale += ` Note: agent initially retrieved ${agentRunbookId}.md — showing your simulated scenario context. Run ./deploy.sh reindex incremental if RAG index is stale.`;
    showToast('warning', 'Runbook mismatch', `Expected ${displayRunbookId}, agent returned ${agentRunbookId}`);
  }
  $('cr-rationale').textContent = rationale;
  $('cr-runbook-file').textContent = `${displayRunbookId}.md`;

  const sections = scenario?.runbook_sections || [];
  $('cr-runbook-sections').innerHTML = sections.map((s) => `<li>${s}</li>`).join('');
  const tags = scenario?.tags || [];
  $('cr-runbook-tags').innerHTML = tags.map((t) => `<span>${t}</span>`).join('');
  const plan = scenario?.plan || [];
  $('cr-changes').innerHTML = plan.length
    ? plan.map((c) => `<li>${c}</li>`).join('')
    : `<li>${escapeHtml(data.recommendation || 'Awaiting agent recommendation')}</li>`;

  renderLogPreview(context.log_snippet || p.log_snippet || getLogSnippet());

  const banner = $('automation-banner');
  banner.classList.remove('resolved', 'policy-blocked');
  show(banner.querySelector('.approval-actions'));
  setHitlApprovalState('checking');
  const badge = $('cr-status-badge');
  if (badge) { badge.textContent = 'Checking policy…'; badge.className = 'badge opa-checking'; }

  const recText = data.recommendation || plan.map((c) => c.replace(/<[^>]+>/g, '')).join(' ');
  void evaluateOpaPolicy({ ...context, service: context.service || p.service, severity: context.severity || p.severity }, recText)
    .then((opa) => {
      if (opa && $('cr-rationale')) {
        $('cr-rationale').textContent += ` ${archStack('policy', 'OPA')} ${opa.allowed ? 'allowed' : 'denied'} (${opa.matched_rule}).`;
      }
    });
}

function isPersistedTicket(ticket) {
  return Boolean(
    ticket
    && ticket.ticket_id
    && !['pending_hitl', 'blocked_by_policy', 'error'].includes(ticket.status),
  );
}

function markAutomationCompleted(ticket) {
  hitlResolved = true;
  opaEvalSeq += 1;
  const banner = $('automation-banner');
  banner.classList.add('resolved');
  const strong = banner.querySelector('.approval-body strong');
  if (isPersistedTicket(ticket)) {
    strong.textContent = `Simulated change approved — ticket ${ticket.ticket_id} created`;
    showToast('success', 'Ticket created', `${ticket.ticket_id} saved to ticket-api`);
    pushNotification({
      type: 'success',
      title: `Ticket ${ticket.ticket_id} created`,
      message: 'Remediation recorded after HITL approval.',
      action: { section: 'actions', tab: 'act-list' },
      dedupeKey: `ticket-${ticket.ticket_id}`,
    });
  } else {
    strong.textContent = 'Simulated change approved — pipeline completed';
    showToast('success', 'Simulation complete', 'Agent run finished (no ticket record returned)');
  }
  hide(banner.querySelector('.approval-actions'));
  const badge = $('cr-status-badge');
  if (badge) { badge.textContent = 'Completed'; badge.className = 'badge done'; }
  setPendingBadge(false);
}

function markAutomationRejected() {
  hitlResolved = true;
  opaEvalSeq += 1;
  const banner = $('automation-banner');
  banner?.classList.add('resolved');
  const strong = banner?.querySelector('.approval-body strong');
  if (strong) strong.textContent = 'Change rejected — no remediation executed';
  hide(banner?.querySelector('.approval-actions'));
  const badge = $('cr-status-badge');
  if (badge) { badge.textContent = 'Rejected'; badge.className = 'badge opa-deny'; }
  setPendingBadge(false);
}

function getHitlDecisionComment() {
  return ($('hitl-decision-comment')?.value || $('ctx-hitl-comment')?.value || '').trim();
}

function hitlDecisionPayload() {
  const ctx = pendingChangeRun?.context || {};
  const data = pendingChangeRun?.data || {};
  return {
    thread_id: pendingThread,
    domain: pendingDomain || currentDomain,
    mode: pendingMode || currentMode,
    service: ctx.service || data.service || $('cr-service')?.textContent,
    severity: ctx.severity || data.severity || $('cr-priority')?.textContent,
    runbook_id: data.runbook_id || $('cr-runbook-file')?.textContent?.replace('.md', ''),
    recommendation: data.recommendation || $('cr-recommendation')?.textContent,
    opa_allowed: lastOpaEvaluation?.allowed ?? null,
    opa_rule: lastOpaEvaluation?.matched_rule ?? null,
    reason: getHitlDecisionComment() || null,
  };
}

async function loadHitlHistory(decision = hitlHistoryFilter) {
  const body = $('hitl-history-body');
  if (!body) return;
  hitlHistoryFilter = decision || '';
  body.innerHTML = '<tr><td colspan="10" class="muted">Loading…</td></tr>';
  try {
    const q = decision ? `?decision=${encodeURIComponent(decision)}` : '';
    const data = await api(`/api/simulation/hitl/history${q}`);
    const rows = data.decisions || [];
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="10" class="muted">No HITL decisions yet — approve or reject a change run in HITL Review.</td></tr>';
      return;
    }
    body.innerHTML = rows.map((r) => {
      const dec = r.decision === 'approved'
        ? '<span class="pill pass">Approved</span>'
        : '<span class="pill p1">Rejected</span>';
      const opa = r.opa_allowed == null ? '—' : (r.opa_allowed ? `<span class="pill pass">allow</span>` : `<span class="pill p1">deny</span>`);
      const ticket = r.ticket_id ? `<code>${escapeHtml(r.ticket_id)}</code>` : '—';
      const reason = r.reason ? `<span class="hitl-reason-cell" title="${escapeHtml(r.reason)}">${escapeHtml(r.reason)}</span>` : '<span class="muted">—</span>';
      return `<tr>
        <td>${formatAuditTime(r.decided_at)}</td>
        <td>${dec}</td>
        <td><code>${escapeHtml(r.change_run_id || '—')}</code></td>
        <td>${escapeHtml(r.service || '—')}</td>
        <td>${escapeHtml(r.severity || '—')}</td>
        <td><code>${escapeHtml(r.runbook_id || '—')}</code></td>
        <td>${opa}${r.opa_rule ? ` <span class="muted">${escapeHtml(r.opa_rule)}</span>` : ''}</td>
        <td>${escapeHtml(r.decided_by || '—')}</td>
        <td>${reason}</td>
        <td>${ticket}</td>
      </tr>`;
    }).join('');
  } catch (err) {
    body.innerHTML = `<tr><td colspan="10" class="muted">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderResult(data) {
  lastPipelineResult = data;
  const awaitingHitl = data.status === 'awaiting_hitl';
  if (!awaitingHitl) hide($('pipeline-running-pill'));
  else show($('pipeline-running-pill'));
  $('result').textContent = JSON.stringify(data, null, 2);
  lastThreadId = data.thread_id;
  if ($('active-mode')) $('active-mode').textContent = data.mode || currentMode;
  $('incident-id').textContent = incidentId(data.thread_id);
  $('severity-badge').textContent = `${$('severity').value} · SEVERE`;
  updateTraceLinks(data.thread_id);

  const steps = getActivePipelineSteps();
  let activeStep = 0;
  if (currentMode === 'multi') {
    const trace = (data.worker_trace || []).map(normalizeWorkerId);
    activeStep = Math.max(0, steps.findIndex((s) => s.id === trace[trace.length - 1]));
    if (activeStep < 0) activeStep = steps.length - 1;
    renderOrchestrationFromResult(data);
    show($('orchestration-theater'));
    if ($('orch-tree-full')?.innerHTML) renderOrchestrationFromResult(data);
  } else if (currentMode === 'mcp') {
    if (data.classification) activeStep = 1;
    if (data.runbook_id) activeStep = 2;
    if (data.recommendation) activeStep = 3;
    renderMcpToolCalls(data.mcp_tool_calls || []);
    renderMcpToolCalls(data.mcp_tool_calls || [], 'mcp-tab-calls');
    highlightMcpToolNodes(data.mcp_tool_calls || []);
    show($('mcp-theater'));
  } else {
    if (data.classification) activeStep = 1;
    if (data.runbook_id) activeStep = 2;
    if (data.recommendation) activeStep = 4;
  }
  if (data.status === 'awaiting_hitl') {
    activeStep = steps.findIndex((s) => s.id === 'hitl_gate' || s.id === 'hitl');
    if (activeStep < 0) activeStep = steps.length - 2;
    setFlowNodeState('hitl', 'waiting');
    FLOW_NODES.slice(0, 3).forEach((n) => setFlowNodeState(n.id, 'done'));
    setFlowNodeState('investigation', 'done');
  } else if (data.status === 'completed') {
    activeStep = steps.length - 1;
    stopTimer();
    completeRunButtonState(false);
    setPipelineLiveMode(false);
    $('pipeline-status-text').textContent = 'Completed';
    FLOW_NODES.forEach((n) => setFlowNodeState(n.id, 'done'));
    if ($('pipeline-flow-progress')) $('pipeline-flow-progress').style.width = '100%';
    if (currentMode === 'multi') ORCH_WORKERS.forEach((w) => setTreeNodeState(w.id, 'done'));
    if (currentMode === 'multi') setTreeNodeState('hitl_gate', data.status === 'completed' ? 'done' : 'waiting');
    if (currentMode === 'multi') setTreeNodeState('supervisor', 'done');
  }
  updatePipeline(data, activeStep);
  updateQuickStats();
  switchSection('operations', 'ops-pipeline');
}

function updateTraceLinks(threadId) {
  if (!observabilityLinks.langfuse || !threadId) return;
  const url = `${observabilityLinks.langfuse}/project/traces?search=${encodeURIComponent(threadId)}`;
  ['link-trace', 'link-trace-eval'].forEach((id) => { if ($(id)) $(id).href = url; });
  loadEvalTrace(threadId);
}

function flattenTraceSpans(nodes, out = []) {
  (nodes || []).forEach((n) => {
    out.push(n);
    if (n.children?.length) flattenTraceSpans(n.children, out);
  });
  return out;
}

function renderTraceTree(spans, container) {
  if (!container) return;
  container.innerHTML = '';
  const flat = flattenTraceSpans(spans);
  if (!flat.length) {
    container.innerHTML = '<li class="trace-empty"><span class="span-name muted">No spans yet — run the pipeline or click Refresh</span></li>';
    return;
  }
  flat.forEach((span, i) => {
    const li = document.createElement('li');
    li.dataset.depth = String(span.depth || 0);
    li.style.animationDelay = `${Math.min(i * 0.04, 0.5)}s`;
    const badge = span.type && span.type !== 'span'
      ? `<span class="span-badge ${span.type}">${span.type}</span>`
      : (span.phase ? `<span class="span-badge">${span.phase}</span>` : '');
    const agent = span.agent ? `<span class="span-badge agent">${span.agent}</span>` : '';
    li.innerHTML = `
      <span class="span-name">${span.name || 'span'}</span>
      <span class="span-meta">${agent}${badge}<span class="span-ms">${span.duration || '—'}</span></span>
    `;
    container.appendChild(li);
  });
}

async function loadEvalTrace(threadId) {
  const list = $('eval-trace-spans');
  const nameEl = $('eval-trace-name');
  const countEl = $('eval-trace-count');
  if (!threadId || !list) return;
  try {
    const data = await api(`/api/observability/traces/${encodeURIComponent(threadId)}`);
    if (nameEl) nameEl.textContent = data.trace_name || threadId.slice(0, 8);
    if (countEl) countEl.textContent = `${data.flat_count || 0} observations`;
    if (data.langfuse_url && $('link-trace-eval')) $('link-trace-eval').href = data.langfuse_url;
    renderTraceTree(data.spans || [], list);
    if (data.message && !(data.spans || []).length) {
      list.innerHTML = `<li class="trace-empty"><span class="span-name muted">${data.message}</span></li>`;
    }
  } catch (err) {
    if (list) list.innerHTML = `<li class="trace-empty"><span class="span-name muted">Trace load failed: ${err.message}</span></li>`;
  }
}

const LF_CHART_COLORS = ['#6366f1', '#22d3ee', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#fb7185', '#4ade80'];

const LF_TYPE_COLORS = {
  agent: '#6366f1',
  generation: '#fbbf24',
  tool: '#34d399',
  span: '#94a3b8',
  event: '#fb7185',
};

const LF_PHASE_COLORS = {
  Route: '#a78bfa',
  Triage: '#6366f1',
  Context: '#22d3ee',
  Decision: '#fbbf24',
  Guardrails: '#f87171',
  Action: '#34d399',
};

const LF_MODE_COLORS = {
  standalone: '#6366f1',
  'multi-agent': '#a78bfa',
  mcp: '#22d3ee',
  other: '#94a3b8',
};

const LF_TOOL_COLORS = {
  'Chroma RAG': '#34d399',
  'Weaviate RAG': '#34d399',
  'OpenSearch RAG': '#34d399',
  'Loki Log Query': '#22d3ee',
  'Elasticsearch Log Query': '#22d3ee',
  'OpenSearch Log Query': '#22d3ee',
  'Prometheus Metrics': '#f97316',
  'VictoriaMetrics Metrics': '#f97316',
  'Mimir Metrics': '#f97316',
  'OPA Policy Check': '#f87171',
  'OpenFGA Policy Check': '#f87171',
  'Create Ticket': '#a78bfa',
};

function lfColorFor(item, index, colorMap = {}) {
  const key = item.label || item.name || item.type || item.mode || item.phase || '';
  return colorMap[key] || LF_PHASE_COLORS[key] || LF_TYPE_COLORS[key] || LF_MODE_COLORS[key] || LF_CHART_COLORS[index % LF_CHART_COLORS.length];
}

function lfFormatMs(ms) {
  if (!ms && ms !== 0) return '—';
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

function renderLfBarChart(container, data, { labelKey = 'label', valueKey = 'avg_ms', suffix = 'ms', colorMap = {} } = {}) {
  if (!container) return;
  if (!data?.length) {
    container.innerHTML = '<div class="lf-chart-empty">No data yet — run the pipeline</div>';
    return;
  }
  const w = 400;
  const h = 160;
  const pad = { t: 12, r: 12, b: 36, l: 12 };
  const max = Math.max(...data.map((d) => d[valueKey] || 0), 1);
  const barW = (w - pad.l - pad.r) / data.length;
  const bars = data.map((d, i) => {
    const val = d[valueKey] || 0;
    const bh = ((h - pad.t - pad.b) * val) / max;
    const x = pad.l + i * barW + barW * 0.15;
    const y = h - pad.b - bh;
    const color = lfColorFor(d, i, colorMap);
    const label = (d[labelKey] || '').slice(0, 12);
    return `<rect x="${x}" y="${y}" width="${barW * 0.7}" height="${bh}" rx="4" fill="${color}" opacity="0.9"><title>${d[labelKey]}: ${val}${suffix}</title></rect>
      <text x="${x + barW * 0.35}" y="${h - 8}" text-anchor="middle" fill="var(--muted)" font-size="9">${label}</text>`;
  }).join('');
  container.innerHTML = `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMidYMid meet">${bars}</svg>`;
}

function renderLfLineChart(container, data, { labelKey = 'timestamp', valueKey = 'latency_ms' } = {}) {
  if (!container) return;
  if (!data?.length) {
    container.innerHTML = '<div class="lf-chart-empty">No latency data yet</div>';
    return;
  }
  const w = 400;
  const h = 160;
  const pad = { t: 16, r: 16, b: 28, l: 16 };
  const max = Math.max(...data.map((d) => d[valueKey] || 0), 1);
  const points = data.map((d, i) => {
    const x = pad.l + (i / Math.max(data.length - 1, 1)) * (w - pad.l - pad.r);
    const y = pad.t + (1 - (d[valueKey] || 0) / max) * (h - pad.t - pad.b);
    return { x, y, color: LF_CHART_COLORS[i % LF_CHART_COLORS.length], val: d[valueKey] };
  });
  const pts = points.map((p) => `${p.x},${p.y}`).join(' ');
  const dots = points.map((p) => `<circle cx="${p.x}" cy="${p.y}" r="4" fill="${p.color}" stroke="#fff" stroke-width="1.5"><title>${p.val}ms</title></circle>`).join('');
  const segments = points.slice(1).map((p, i) => {
    const prev = points[i];
    return `<line x1="${prev.x}" y1="${prev.y}" x2="${p.x}" y2="${p.y}" stroke="${p.color}" stroke-width="2.5" stroke-linecap="round"/>`;
  }).join('');
  container.innerHTML = `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMidYMid meet">
    ${segments}
    ${dots}
    <polyline fill="url(#lfLineFill)" stroke="none" points="${pts} ${points[points.length - 1].x},${h - pad.b} ${points[0].x},${h - pad.b}"/>
    <defs><linearGradient id="lfLineFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(99,102,241,0.2)"/><stop offset="100%" stop-color="rgba(99,102,241,0)"/></linearGradient></defs>
  </svg>`;
}

function renderLfDonutChart(container, data, { labelKey = 'type', valueKey = 'count' } = {}) {
  if (!container) return;
  if (!data?.length) {
    container.innerHTML = '<div class="lf-chart-empty">No span data yet</div>';
    return;
  }
  const total = data.reduce((s, d) => s + (d[valueKey] || 0), 0) || 1;
  let angle = -90;
  const r = 52;
  const cx = 70;
  const cy = 80;
  const slices = data.map((d, i) => {
    const frac = (d[valueKey] || 0) / total;
    const a1 = angle;
    const a2 = angle + frac * 360;
    angle = a2;
    const x1 = cx + r * Math.cos((Math.PI * a1) / 180);
    const y1 = cy + r * Math.sin((Math.PI * a1) / 180);
    const x2 = cx + r * Math.cos((Math.PI * a2) / 180);
    const y2 = cy + r * Math.sin((Math.PI * a2) / 180);
    const large = frac > 0.5 ? 1 : 0;
    const color = LF_TYPE_COLORS[d[labelKey]] || LF_CHART_COLORS[i % LF_CHART_COLORS.length];
    return `<path d="M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z" fill="${color}" opacity="0.92"/>`;
  }).join('');
  const legend = data.map((d, i) => {
    const color = LF_TYPE_COLORS[d[labelKey]] || LF_CHART_COLORS[i % LF_CHART_COLORS.length];
    return `<li><span class="dot" style="background:${color}"></span>${d[labelKey]} (${d[valueKey]})</li>`;
  }).join('');
  container.innerHTML = `<svg viewBox="0 0 140 160" width="140" height="160">${slices}<circle cx="${cx}" cy="${cy}" r="28" fill="var(--surface)"/><text x="${cx}" y="${cy + 4}" text-anchor="middle" font-size="11" fill="var(--muted)">${total}</text></svg><ul class="lf-donut-legend">${legend}</ul>`;
}

function renderLangfuseDashboard(data) {
  const kpis = data.kpis || {};
  if ($('lf-kpi-traces')) $('lf-kpi-traces').textContent = kpis.total_traces ?? '0';
  if ($('lf-kpi-latency')) $('lf-kpi-latency').textContent = lfFormatMs(kpis.avg_latency_ms);
  if ($('lf-kpi-llm')) $('lf-kpi-llm').textContent = kpis.llm_calls ?? '0';
  if ($('lf-kpi-tools')) $('lf-kpi-tools').textContent = kpis.tool_calls ?? '0';
  if ($('lf-kpi-p95')) $('lf-kpi-p95').textContent = lfFormatMs(kpis.p95_latency_ms);
  if ($('lf-kpi-obs')) $('lf-kpi-obs').textContent = kpis.avg_observations_per_trace ?? '—';

  renderLfBarChart($('lf-chart-daily'), (data.daily_activity || []).map((d) => ({
    label: (d.date || '').slice(5),
    avg_ms: d.traces,
  })), { labelKey: 'label', valueKey: 'avg_ms', suffix: ' traces', colorMap: {} });

  renderLfLineChart($('lf-chart-latency'), data.latency_trend || []);
  renderLfBarChart($('lf-chart-phase'), (data.latency_by_phase || []).map((d) => ({
    label: d.label,
    avg_ms: d.avg_ms,
    phase: d.label,
  })), { colorMap: LF_PHASE_COLORS });
  renderLfDonutChart($('lf-chart-spans'), data.span_types || []);
  renderLfBarChart($('lf-chart-tools'), (data.tool_latency || []).map((d) => ({
    label: d.name,
    avg_ms: d.avg_ms,
    name: d.name,
  })), { colorMap: LF_TOOL_COLORS });
  renderLfBarChart($('lf-chart-modes'), (data.mode_breakdown || []).map((d) => ({
    label: d.mode,
    avg_ms: d.count,
    mode: d.mode,
  })), { suffix: '', colorMap: LF_MODE_COLORS });

  const scoresBody = $('lf-scores-table')?.querySelector('tbody');
  if (scoresBody) {
    const scores = data.scores || [];
    scoresBody.innerHTML = scores.length
      ? scores.map((s) => `<tr><td><code>${s.name}</code></td><td>${s.latest}</td><td>${s.avg}</td><td>${s.count}</td></tr>`).join('')
      : '<tr><td colspan="4" class="muted">Scores appear after pipeline runs (synced to the LLM ops Scores tab)</td></tr>';
  }

  const tracesBody = $('lf-recent-traces')?.querySelector('tbody');
  if (tracesBody) {
    const rows = data.recent_traces || [];
    tracesBody.innerHTML = rows.length
      ? rows.map((t) => {
        const ts = (t.timestamp || '').replace('T', ' ').slice(0, 16);
        return `<tr data-href="${t.langfuse_url || ''}" style="cursor:pointer"><td>${t.name}</td><td><span class="pill open">${t.mode}</span></td><td>${t.latency || lfFormatMs(t.latency_ms)}</td><td class="muted">${ts}</td></tr>`;
      }).join('')
      : '<tr><td colspan="4" class="muted">No traces yet</td></tr>';
    tracesBody.querySelectorAll('tr[data-href]').forEach((row) => {
      row.addEventListener('click', () => {
        const href = row.dataset.href;
        if (href) window.open(href, '_blank', 'noopener');
      });
    });
  }

  if (data.langfuse_url && $('link-langfuse-dashboard')) $('link-langfuse-dashboard').href = data.langfuse_url;
  if (data.scores_url && $('link-langfuse-scores')) $('link-langfuse-scores').href = data.scores_url;
}

async function loadLangfuseDashboard() {
  try {
    const data = await api('/api/observability/langfuse/dashboard');
    if (data.message && !data.configured) {
      showToast('warning', archStack('llmops', 'Langfuse'), data.message);
    }
    renderLangfuseDashboard(data);
  } catch (err) {
    showToast('error', 'Analytics failed', err.message);
  }
}

const EVAL_METRIC_LABELS = {
  rag_recall_at_3: 'RAG Recall@3',
  groundedness: 'Groundedness',
  tool_call_accuracy: 'Tool / HITL Accuracy',
  correctness: 'Runbook Correctness',
  p95_latency_ms: 'P95 Latency (ms)',
};

function evalPct(value, threshold, higherIsBetter = true) {
  if (threshold == null || value == null) return 0;
  if (!higherIsBetter) return Math.min(100, Math.max(0, (threshold / Math.max(value, 1)) * 100));
  return Math.min(100, Math.max(0, (value / threshold) * 100));
}

function renderEvalMetricBars(averages, thresholds) {
  const grid = $('eval-metrics-grid');
  if (!grid) return;
  const items = Object.keys(EVAL_METRIC_LABELS).map((key) => {
    const val = averages?.[key] ?? 0;
    const thr = thresholds?.[key] ?? 1;
    const higher = key !== 'p95_latency_ms';
    const pass = higher ? val >= thr : val <= thr;
    const pct = evalPct(val, thr, higher);
    const color = pass ? '#34d399' : '#f87171';
    const display = key === 'p95_latency_ms' ? `${Math.round(val)}ms / ${thr}ms` : `${(val * 100).toFixed(0)}% / ${(thr * 100).toFixed(0)}%`;
    return `<div class="eval-metric-card">
      <div class="eval-metric-head"><span>${EVAL_METRIC_LABELS[key]}</span><span class="pill ${pass ? 'pass' : 'p1'}">${pass ? 'PASS' : 'FAIL'}</span></div>
      <div class="eval-metric-bar"><div class="eval-metric-fill" style="width:${pct}%;background:${color}"></div></div>
      <span class="muted eval-metric-val">${display}</span>
    </div>`;
  });
  grid.innerHTML = items.join('');
}

function renderEvalDashboard(data) {
  const latest = data.latest;
  const banner = $('eval-gate-banner');
  if (banner) {
    if (latest) {
      banner.classList.remove('hidden');
      banner.className = `eval-gate-banner ${latest.passed ? 'eval-pass' : 'eval-fail'}`;
      banner.textContent = latest.passed
        ? `✓ Eval gate PASSED — ${latest.cases_passed ?? '?'}/${latest.case_count} cases · ${formatAuditTime(latest.started_at)}`
        : `✗ Eval gate FAILED — ${latest.cases_passed ?? 0}/${latest.case_count} cases · ${formatAuditTime(latest.started_at)}`;
    } else {
      banner.classList.add('hidden');
    }
  }

  const avg = latest?.averages || {};
  const thr = latest?.thresholds || {};
  if ($('eval-kpi-status')) {
    $('eval-kpi-status').innerHTML = latest
      ? `<span class="pill ${latest.passed ? 'pass' : 'p1'}">${latest.passed ? 'PASS' : 'FAIL'}</span>`
      : '—';
  }
  if ($('eval-kpi-cases')) {
    $('eval-kpi-cases').textContent = latest ? `${latest.cases_passed ?? '—'}/${latest.case_count}` : '—';
  }
  if ($('eval-kpi-rag')) $('eval-kpi-rag').textContent = avg.rag_recall_at_3 != null ? `${(avg.rag_recall_at_3 * 100).toFixed(0)}%` : '—';
  if ($('eval-kpi-ground')) $('eval-kpi-ground').textContent = avg.groundedness != null ? `${(avg.groundedness * 100).toFixed(0)}%` : '—';
  if ($('eval-kpi-correct')) $('eval-kpi-correct').textContent = avg.correctness != null ? `${(avg.correctness * 100).toFixed(0)}%` : '—';
  if ($('eval-kpi-latency')) $('eval-kpi-latency').textContent = avg.p95_latency_ms != null ? lfFormatMs(avg.p95_latency_ms) : '—';

  renderEvalMetricBars(avg, thr);

  const casesBody = $('eval-cases-table')?.querySelector('tbody');
  const cases = latest?.cases || [];
  if (casesBody) {
    if (cases.length) {
      casesBody.innerHTML = cases.map((c) => {
        const m = c.metrics || {};
        return `<tr>
          <td><code>${c.id}</code><br><span class="muted">${c.service} · ${c.severity}</span></td>
          <td>${c.expected_runbook_id || '—'}</td>
          <td>${c.actual_runbook_id || '—'}</td>
          <td>${m.rag_recall_at_3 >= 1 ? '✓' : '✗'}</td>
          <td>${(m.groundedness * 100).toFixed(0)}%</td>
          <td>${lfFormatMs(m.latency_ms)}</td>
          <td><span class="pill ${c.passed ? 'pass' : 'p1'}">${c.passed ? 'PASS' : 'FAIL'}</span></td>
        </tr>`;
      }).join('');
    } else if ((data.golden_cases || []).length) {
      casesBody.innerHTML = data.golden_cases.map((c) => `<tr class="eval-golden-preview">
          <td><code>${c.id}</code><br><span class="muted">${c.service} · ${c.severity}</span></td>
          <td>${c.expected_runbook_id || '—'}</td>
          <td class="muted">—</td>
          <td class="muted">—</td>
          <td class="muted">—</td>
          <td class="muted">—</td>
          <td><span class="pill">${c.expects_hitl ? 'HITL' : 'Auto'}</span></td>
        </tr>`).join('');
    } else {
      casesBody.innerHTML = `<tr><td colspan="7" class="muted">No golden cases found — check agent/evals/golden_alerts.json</td></tr>`;
    }
  }

  const histBody = $('eval-history-table')?.querySelector('tbody');
  const history = data.history || [];
  if (histBody) {
    histBody.innerHTML = history.length
      ? history.map((h) => {
        const passRate = h.averages?.correctness != null ? `${(h.averages.correctness * 100).toFixed(0)}%` : '—';
        return `<tr>
          <td class="muted">${formatAuditTime(h.started_at)}</td>
          <td>${h.triggered_by || '—'}</td>
          <td>${h.cases_passed != null ? `${h.cases_passed}/${h.case_count}` : h.case_count}</td>
          <td>${passRate}</td>
          <td><span class="pill ${h.passed ? 'pass' : 'p1'}">${h.passed ? 'PASS' : 'FAIL'}</span></td>
        </tr>`;
      }).join('')
      : '<tr><td colspan="5" class="muted">No runs yet</td></tr>';
  }
}

async function loadEvalDashboard() {
  try {
    const data = await api('/api/evaluation/dashboard');
    evalGoldenCases = data.golden_cases || [];
    renderEvalDashboard(data);
  } catch (err) {
    showToast('error', 'Eval dashboard failed', err.message);
  }
}

function govConclusionClass(conclusion) {
  const c = (conclusion || '').toLowerCase();
  if (c === 'success' || c === 'approved') return 'gov-ok';
  if (c === 'failure' || c === 'rejected') return 'gov-fail';
  if (c === 'pending') return 'gov-pending';
  return 'gov-muted';
}

function govWhen(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

async function loadGovernanceSection(tabId) {
  const tab = tabId || currentTab || 'gov-overview';
  try {
    if (tab === 'gov-overview' || tab === 'gov-controls' || tab === 'gov-github') {
      const data = await api('/api/governance/overview');
      renderGovernanceOverview(data);
      if (tab === 'gov-controls') {
        renderGovernanceControls(data.controls || []);
        const audit = await api('/api/governance/audit');
        renderGovernanceAudit(audit.events || []);
      }
      if (tab === 'gov-github') renderGovernanceGithub(data.github || {});
    }
    if (tab === 'gov-pipelines') {
      const data = await api('/api/governance/pipelines');
      renderGovernancePipelines(data.runs || []);
    }
    if (tab === 'gov-promotions') {
      const data = await api('/api/governance/promotions');
      renderGovernancePromotions(data.promotions || []);
    }
  } catch (err) {
    showToast('error', 'Governance failed', err.message);
  }
}

function renderGovernanceOverview(data) {
  const posture = data.posture || 'healthy';
  const gh = data.github || {};
  const banner = $('gov-posture-banner');
  if (banner) {
    banner.className = `gov-posture-banner gov-${posture}`;
    const wired = gh.wired ? `${gh.org}/${gh.repo}` : 'YOUR_GITHUB_ORG / YOUR_GITHUB_REPO (placeholder)';
    banner.textContent = posture === 'needs_approval'
      ? `Waiting on four-eyes reviewers · GitHub ${wired}`
      : posture === 'failing'
        ? `Required checks failing · GitHub ${wired}`
        : `Healthy · required checks green · GitHub ${wired}`;
  }
  const setText = (id, value) => { const el = $(id); if (el) el.textContent = value; };
  setText('gov-stat-posture', posture.replace('_', ' '));
  setText('gov-stat-pending', String(data.pending_promotions ?? 0));
  setText('gov-stat-failing', String(data.failing_checks ?? 0));
  setText('gov-stat-github', gh.wired ? 'wired' : 'placeholder');

  const checksBody = $('gov-overview-checks');
  if (checksBody) {
    const runs = data.runs || [];
    checksBody.innerHTML = runs.length
      ? runs.map((r) => `<tr>
          <td>${escapeHtml(r.check_name)}</td>
          <td><span class="gov-pill ${govConclusionClass(r.conclusion)}">${escapeHtml(r.conclusion)}</span></td>
          <td>${escapeHtml(govWhen(r.created_at))}</td>
        </tr>`).join('')
      : '<tr><td colspan="3" class="muted">No pipeline runs yet</td></tr>';
  }
  const promoWrap = $('gov-overview-promos');
  if (promoWrap) {
    const pending = (data.promotions || []).filter((p) => p.status === 'pending');
    promoWrap.innerHTML = pending.length
      ? pending.map(govPromoCard).join('')
      : '<p class="muted">No promotions waiting on reviewers.</p>';
    bindGovPromoActions(promoWrap);
  }
}

function govPromoCard(p) {
  const pending = p.status === 'pending';
  return `<article class="gov-promo-card glossy-card" data-promo-id="${escapeHtml(p.id)}">
    <div class="gov-promo-head">
      <strong>${escapeHtml(p.environment)}</strong>
      <span class="gov-pill ${govConclusionClass(p.status)}">${escapeHtml(p.status)}</span>
    </div>
    <p>${escapeHtml(p.reason || 'No reason given')}</p>
    <p class="muted">Requested by ${escapeHtml(p.requested_by)} · sha ${escapeHtml((p.sha || '').slice(0, 12) || 'local')}</p>
    ${pending ? `<div class="gov-promo-actions">
      <button type="button" class="btn-success btn-sm" data-gov-decide="approve">Approve</button>
      <button type="button" class="btn-danger btn-sm" data-gov-decide="reject">Reject</button>
    </div>` : `<p class="muted">Decided by ${escapeHtml(p.decided_by || '—')} · ${escapeHtml(p.decision_note || '')}</p>`}
  </article>`;
}

function bindGovPromoActions(root) {
  if (!root) return;
  root.querySelectorAll('[data-gov-decide]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const card = btn.closest('[data-promo-id]');
      const id = card?.dataset.promoId;
      if (!id) return;
      const approved = btn.dataset.govDecide === 'approve';
      try {
        await api(`/api/governance/promotions/${id}/decide`, {
          method: 'POST',
          body: JSON.stringify({ approved, note: approved ? 'Approved in console' : 'Rejected in console' }),
        });
        showToast('success', approved ? 'Promotion approved' : 'Promotion rejected', 'Four-eyes recorded in audit');
        await loadGovernanceSection(currentTab);
      } catch (err) {
        showToast('error', 'Promotion blocked', err.message);
      }
    });
  });
}

function renderGovernancePipelines(runs) {
  const body = $('gov-pipelines-body');
  if (!body) return;
  body.innerHTML = runs.length
    ? runs.map((r) => `<tr>
        <td>${escapeHtml(r.workflow)}</td>
        <td>${escapeHtml(r.check_name)}</td>
        <td><span class="gov-pill ${govConclusionClass(r.conclusion)}">${escapeHtml(r.conclusion)}</span></td>
        <td>${escapeHtml(r.branch || 'main')}</td>
        <td>${escapeHtml(r.triggered_by)}</td>
        <td>${escapeHtml(r.summary || '')}</td>
        <td>${escapeHtml(govWhen(r.created_at))}</td>
      </tr>`).join('')
    : '<tr><td colspan="7" class="muted">No pipeline runs yet</td></tr>';
}

function renderGovernancePromotions(promos) {
  const wrap = $('gov-promotions-list');
  if (!wrap) return;
  wrap.innerHTML = promos.length
    ? promos.map(govPromoCard).join('')
    : '<p class="muted">No promotions yet — request one above.</p>';
  bindGovPromoActions(wrap);
}

function renderGovernanceControls(controls) {
  const body = $('gov-controls-body');
  if (!body) return;
  body.innerHTML = controls.map((c) => `<tr>
    <td><code>${escapeHtml(c.id)}</code></td>
    <td>${escapeHtml(c.name)}</td>
    <td>${escapeHtml(c.domain)}</td>
    <td>${escapeHtml(c.owner)}</td>
    <td class="muted">${escapeHtml(c.evidence)}</td>
  </tr>`).join('');
}

function renderGovernanceAudit(events) {
  const body = $('gov-audit-body');
  if (!body) return;
  body.innerHTML = events.length
    ? events.map((e) => `<tr>
        <td>${escapeHtml(govWhen(e.created_at))}</td>
        <td>${escapeHtml(e.actor)}</td>
        <td>${escapeHtml(e.action)}</td>
        <td>${escapeHtml(e.resource)}</td>
        <td>${escapeHtml(e.detail || '')}</td>
      </tr>`).join('')
    : '<tr><td colspan="5" class="muted">No audit events</td></tr>';
}

function renderGovernanceGithub(gh) {
  const dl = $('gov-github-dl');
  const snippet = $('gov-github-snippet');
  const actions = $('gov-github-actions');
  if (dl) {
    const rows = [
      ['Organization', gh.org || 'YOUR_GITHUB_ORG'],
      ['Repository', gh.repo || 'YOUR_GITHUB_REPO'],
      ['Wired', gh.wired ? 'yes' : 'no — placeholders in the codebase'],
      ['Required checks', (gh.required_checks || []).join(', ')],
      ['Environments', (gh.environments || []).join(', ')],
      ['Secrets still needed', (gh.secrets_needed || []).join(', ')],
    ];
    dl.innerHTML = rows.map(([k, v]) => `<div><dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd></div>`).join('');
  }
  if (snippet) {
    snippet.textContent = [
      '# Once GitHub details are shared, set:',
      'GITHUB_ORG=YOUR_GITHUB_ORG',
      'GITHUB_REPO=YOUR_GITHUB_REPO',
      '',
      '# Copy workflows into the git root if this course is nested:',
      'rsync -a .github/ "$GITHUB_REPO_ROOT/.github/"',
      '',
      '# Protect main with required checks:',
      ...(gh.required_checks || []).map((c) => `#   - ${c}`),
      '',
      '# CODEOWNERS',
      ...(gh.codeowners || []),
    ].join('\n');
  }
  if (actions) {
    if (gh.actions_url) {
      actions.href = gh.actions_url;
      actions.classList.remove('hidden');
    } else {
      actions.classList.add('hidden');
    }
  }
}

async function submitGovernancePromotion(event) {
  event.preventDefault();
  try {
    await api('/api/governance/promotions', {
      method: 'POST',
      body: JSON.stringify({
        environment: $('gov-promo-env')?.value || 'staging',
        sha: $('gov-promo-sha')?.value || '',
        reason: $('gov-promo-reason')?.value || '',
      }),
    });
    showToast('success', 'Promotion requested', 'Waiting on a different reviewer (four-eyes)');
    if ($('gov-promo-reason')) $('gov-promo-reason').value = '';
    await loadGovernanceSection('gov-promotions');
  } catch (err) {
    showToast('error', 'Promotion request failed', err.message);
  }
}

const ALERT_PHASE_COLORS = {
  ingestion: '#6366f1',
  agent: '#22d3ee',
  guardrails: '#f97316',
  hitl: '#34d399',
};

const ALERT_PHASE_LABELS = {
  ingestion: 'Signals',
  agent: 'Agent',
  guardrails: 'OPA',
  hitl: 'HITL',
};

const ALERT_STEP_ICONS = {
  metrics_exporter: '📊',
  prometheus: '🔥',
  alertmanager: '📣',
  alert_receiver: '🔗',
  agent_invoke: '🤖',
  agent_classify: '🎯',
  agent_chroma: '📚',
  agent_logs: '📋',
  agent_metrics: '📈',
  agent_recommend: '💡',
  agent_traces: '🧵',
  opa_evaluate: '🛡️',
  hitl_gate: '✋',
};

let alertFlowCatalog = null;
let selectedAlertId = 'checkout-redis-pool';
let customAlertMode = false;
let customAlertPayload = null;
let alertFlowSimData = null;
let alertFlowAnimTimer = null;
let alertPhaseFilter = 'all';
let alertFlowMaxStepIndex = -1;
let alertFlowJourneyComplete = false;
let alertFlowSelectedStepId = null;

function getAlertSimBody() {
  if (customAlertMode && customAlertPayload) {
    return { custom_alert: customAlertPayload, invoke_agent: false };
  }
  return { alert_id: selectedAlertId, invoke_agent: false };
}

function renderAlertTypeGrid(catalog) {
  const grid = $('alert-type-grid');
  if (!grid) return;
  grid.innerHTML = (catalog.alerts || []).map((a) => {
    const sel = !customAlertMode && a.id === selectedAlertId ? ' is-selected' : '';
    const firing = a.prometheus_firing ? '<span class="pill p1">LIVE</span>' : '';
    return `<button type="button" class="alert-type-card${sel}" data-alert-id="${a.id}">
      <div class="alert-type-head"><strong>${escapeHtml(a.alert_name)}</strong>${firing}</div>
      <span class="muted">${escapeHtml(a.service)} · ${escapeHtml(a.severity)}</span>
      <p class="alert-type-summary">${escapeHtml(a.summary)}</p>
    </button>`;
  }).join('');
  grid.querySelectorAll('.alert-type-card').forEach((btn) => {
    btn.addEventListener('click', () => {
      customAlertMode = false;
      customAlertPayload = null;
      selectedAlertId = btn.dataset.alertId;
      grid.querySelectorAll('.alert-type-card').forEach((b) => b.classList.toggle('is-selected', b === btn));
      $('obs-custom-alert-form')?.classList.remove('is-active-custom');
      previewAlertFlow(false, { silent: true });
    });
  });
}

function scrollJourneyTrack(delta) {
  const track = $('alert-journey-track');
  if (!track) return;
  track.scrollBy({ left: delta, behavior: 'smooth' });
}

function updateJourneyScrollButtons() {
  const track = $('alert-journey-track');
  const leftBtn = $('alert-journey-scroll-left');
  const rightBtn = $('alert-journey-scroll-right');
  if (!track || !leftBtn || !rightBtn) return;
  const maxScroll = track.scrollWidth - track.clientWidth;
  leftBtn.disabled = track.scrollLeft <= 4;
  rightBtn.disabled = maxScroll <= 4 || track.scrollLeft >= maxScroll - 4;
}

function scrollActiveJourneyNodeIntoView() {
  const track = $('alert-journey-track');
  const active = track?.querySelector('.journey-node.is-active');
  if (!active || !track) return;
  const trackRect = track.getBoundingClientRect();
  const nodeRect = active.getBoundingClientRect();
  if (nodeRect.left < trackRect.left + 24 || nodeRect.right > trackRect.right - 24) {
    active.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }
  requestAnimationFrame(updateJourneyScrollButtons);
}

function wireJourneyTrackScroll() {
  const track = $('alert-journey-track');
  if (!track || track.dataset.scrollWired) return;
  track.dataset.scrollWired = '1';
  track.addEventListener('scroll', updateJourneyScrollButtons, { passive: true });
  $('alert-journey-scroll-left')?.addEventListener('click', () => scrollJourneyTrack(-320));
  $('alert-journey-scroll-right')?.addEventListener('click', () => scrollJourneyTrack(320));
  updateJourneyScrollButtons();
}

function getFilteredAlertSteps(steps) {
  if (!steps) return [];
  return alertPhaseFilter === 'all' ? steps : steps.filter((s) => s.phase === alertPhaseFilter);
}

function findAlertStep(stepId) {
  return alertFlowSimData?.steps?.find((s) => s.id === stepId) || null;
}

function selectAlertFlowStep(stepId) {
  const step = findAlertStep(stepId);
  if (!step || !alertFlowSimData?.steps) return;
  const globalIndex = alertFlowSimData.steps.indexOf(step);
  if (!alertFlowJourneyComplete && globalIndex > alertFlowMaxStepIndex) return;
  alertFlowSelectedStepId = stepId;
  renderAlertSimPayload(step);
  const sel = $('obs-sim-step-select');
  if (sel && sel.value !== stepId) sel.value = stepId;
  highlightJourneyStep(stepId, globalIndex);
  if ($('alert-flow-caption')) $('alert-flow-caption').textContent = `${step.title} — ${step.subtitle || ''}`;
  if ($('obs-sim-flow-status')) {
    $('obs-sim-flow-status').textContent = `Step ${globalIndex + 1}/${alertFlowSimData.steps.length} · ${ALERT_PHASE_LABELS[step.phase] || step.phase}`;
  }
}

function updateJourneyClickability() {
  if (!alertFlowSimData?.steps) return;
  document.querySelectorAll('.journey-node').forEach((node) => {
    const step = findAlertStep(node.dataset.step);
    if (!step) return;
    const globalIndex = alertFlowSimData.steps.indexOf(step);
    const canClick = alertFlowJourneyComplete || globalIndex <= alertFlowMaxStepIndex;
    node.classList.toggle('is-clickable', canClick);
    node.setAttribute('tabindex', canClick ? '0' : '-1');
    node.setAttribute('aria-disabled', canClick ? 'false' : 'true');
  });
}

function wireJourneyNodeClicks() {
  const track = $('alert-journey-track');
  if (!track) return;
  track.querySelectorAll('.journey-node').forEach((node) => {
    if (node.dataset.clickWired) return;
    node.dataset.clickWired = '1';
    node.addEventListener('click', () => {
      if (!node.classList.contains('is-clickable')) return;
      selectAlertFlowStep(node.dataset.step);
    });
    node.addEventListener('keydown', (e) => {
      if ((e.key === 'Enter' || e.key === ' ') && node.classList.contains('is-clickable')) {
        e.preventDefault();
        selectAlertFlowStep(node.dataset.step);
      }
    });
  });
}

function buildJourneyTrack(steps) {
  const track = $('alert-journey-track');
  if (!track) return;
  const filtered = getFilteredAlertSteps(steps);
  track.innerHTML = filtered.map((step, i) => {
    const color = ALERT_PHASE_COLORS[step.phase] || '#6366f1';
    const icon = ALERT_STEP_ICONS[step.id] || '•';
    const bridge = i < filtered.length - 1
      ? `<div class="journey-bridge" data-bridge="${step.id}"><span class="journey-packet"></span></div>`
      : '';
    return `<div class="journey-node" data-step="${step.id}" data-phase="${step.phase}" style="--phase-color:${color}" role="button">
      <div class="journey-icon">${icon}</div>
      <strong>${escapeHtml(step.title)}</strong>
      <span class="muted journey-sub">${escapeHtml(step.subtitle || '')}</span>
      <span class="journey-phase-pill">${step.phase}</span>
    </div>${bridge}`;
  }).join('');
  wireJourneyTrackScroll();
  wireJourneyNodeClicks();
  updateJourneyClickability();
  if (alertFlowSelectedStepId) highlightJourneyStep(alertFlowSelectedStepId, alertFlowSimData?.steps?.findIndex((s) => s.id === alertFlowSelectedStepId) ?? 0);
  requestAnimationFrame(updateJourneyScrollButtons);
}

function resetAlertFlowAnim() {
  stopAlertFlowAnim();
  alertFlowMaxStepIndex = -1;
  alertFlowJourneyComplete = false;
  alertFlowSelectedStepId = null;
  document.querySelectorAll('.journey-node').forEach((n) => n.classList.remove('is-active', 'is-done', 'is-selected', 'is-clickable'));
  document.querySelectorAll('.journey-packet').forEach((p) => p.classList.remove('run'));
  $('obs-hitl-banner')?.classList.add('hidden');
  if ($('alert-flow-caption')) $('alert-flow-caption').textContent = 'Preset or custom alert → Walkthrough or Fire.';
  if ($('obs-sim-flow-status')) $('obs-sim-flow-status').textContent = 'Select an alert';
  if ($('obs-sim-payload')) $('obs-sim-payload').textContent = '{}';
  if ($('obs-sim-step-visual')) {
    $('obs-sim-step-visual').innerHTML = '<p class="muted empty-visual">Run a walkthrough to see what happens inside each system.</p>';
  }
  if (alertFlowSimData?.steps) buildJourneyTrack(alertFlowSimData.steps);
}

function stopAlertFlowAnim() {
  if (alertFlowAnimTimer) {
    clearTimeout(alertFlowAnimTimer);
    alertFlowAnimTimer = null;
  }
}

function highlightJourneyStep(stepId, globalStepIndex) {
  document.querySelectorAll('.journey-node').forEach((n) => {
    const step = findAlertStep(n.dataset.step);
    const gi = step ? alertFlowSimData?.steps?.indexOf(step) ?? -1 : -1;
    n.classList.toggle('is-active', n.dataset.step === stepId);
    n.classList.toggle('is-done', gi >= 0 && gi < globalStepIndex);
    n.classList.toggle('is-selected', n.dataset.step === alertFlowSelectedStepId);
  });
  document.querySelectorAll('.journey-bridge').forEach((b) => {
    const bridgeStep = findAlertStep(b.dataset.bridge);
    const gi = bridgeStep ? alertFlowSimData?.steps?.indexOf(bridgeStep) ?? -1 : -1;
    const pkt = b.querySelector('.journey-packet');
    if (pkt) pkt.classList.toggle('run', gi >= 0 && gi < globalStepIndex);
  });
  scrollActiveJourneyNodeIntoView();
  updateJourneyClickability();
}

function renderAlertStepVisual(step) {
  const el = $('obs-sim-step-visual');
  const title = $('obs-sim-visual-title');
  if (!el || !step) return;
  if (title) title.textContent = step.title;
  const v = step.visual || {};
  let html = `<div class="visual-phase-tag" style="--phase-color:${ALERT_PHASE_COLORS[step.phase] || '#6366f1'}">${step.phase}</div>`;
  html += `<p class="visual-subtitle muted">${escapeHtml(step.subtitle || '')}</p>`;

  switch (v.type) {
    case 'metrics':
      html += `<div class="visual-metrics-grid">${Object.entries(v.metrics || {}).filter(([k]) => k !== 'service').map(([k, val]) =>
        `<div class="visual-metric"><span>${k.replace(/_/g, ' ')}</span><strong>${typeof val === 'number' && k.includes('rate') ? `${(val * 100).toFixed(1)}%` : val}</strong></div>`).join('')}</div>`;
      break;
    case 'promql':
      html += `<code class="visual-code">${escapeHtml(v.query || '')}</code>
        <p>Value: <strong class="${v.firing ? 'priority-p1' : ''}">${v.value ?? '—'}</strong> · threshold ${v.threshold}</p>
        <span class="pill ${v.firing ? 'p1' : 'pass'}">${v.firing ? 'RULE FIRING' : 'Below threshold'}</span>`;
      break;
    case 'webhook':
      html += `<p>Receiver <code>${escapeHtml(v.receiver || '')}</code> · status <span class="pill p1">${v.status || 'firing'}</span></p>`;
      break;
    case 'transform':
      html += `<div class="visual-transform"><span>${escapeHtml(v.from)}</span><span class="visual-arrow">→</span><span>${escapeHtml(v.to)}</span></div>`;
      break;
    case 'chroma':
      html += `<p>Collection <code>${escapeHtml(v.collection || 'runbooks')}</code> · query: <em>${escapeHtml(v.query || '')}</em></p>
        <p>Selected runbook: <strong>${escapeHtml(v.selected_runbook_id || '—')}</strong></p>
        <ul class="visual-chroma-list">${(v.chunks || []).map((c) =>
          `<li><code>${escapeHtml(c.runbook_id || '?')}</code><span class="muted">${escapeHtml(c.preview || '')}</span></li>`).join('') || `<li class="muted">Top vector matches from ${archStack('vector', 'Chroma')}</li>`}</ul>`;
      break;
    case 'logs':
      html += (v.lines || []).map((l) =>
        `<div class="log-line ${(l.level || 'info').toLowerCase()}"><span class="log-ts">${(l.timestamp || '').slice(11, 19)}</span>${escapeHtml(l.message || '')}</div>`).join('') || '<p class="muted">No log lines</p>';
      break;
    case 'recommendation':
      html += `<p>Runbook <code>${escapeHtml(v.runbook_id || '')}</code> ${v.destructive ? '<span class="pill p1">Destructive</span>' : ''}</p>
        <blockquote class="visual-quote">${escapeHtml(v.text || '')}</blockquote>`;
      break;
    case 'opa':
      html += `<div class="visual-opa ${v.allowed ? 'is-allow' : 'is-deny'}">
        <span class="visual-opa-verdict">${v.allowed ? '✓ ALLOW' : '✗ DENY'}</span>
        <p>Rule: <code>${escapeHtml(v.matched_rule || '')}</code></p>
        <p class="muted">${escapeHtml(v.reason || '')}${v.destructive ? ' · destructive action detected' : ''}</p></div>`;
      break;
    case 'hitl':
      html += `<span class="pill ${v.status === 'awaiting_hitl' ? 'p1' : v.status === 'blocked_by_policy' ? 'p1' : 'pass'}">${escapeHtml(v.status || '')}</span>
        ${v.thread_id ? `<p>Thread: <code>${escapeHtml(v.thread_id)}</code></p>` : ''}
        ${v.notify ? `<p class="muted">${escapeHtml(v.notify)}</p>` : ''}`;
      break;
    case 'pipeline_node':
    default:
      html += `<div class="visual-node-hero">${v.icon || '⚙️'} <strong>${escapeHtml(v.summary || step.title)}</strong></div>`;
      if (v.badges) html += `<div class="visual-badges">${v.badges.map((b) => `<span class="pill">${escapeHtml(b)}</span>`).join('')}</div>`;
  }
  el.innerHTML = html;
}

function renderAlertSimPayload(step) {
  if (!step || !$('obs-sim-payload')) return;
  const payload = step.response ? { ...step.payload, agent_response: step.response } : (step.payload || step);
  $('obs-sim-payload').textContent = JSON.stringify(payload, null, 2);
  renderAlertStepVisual(step);
}

function populateAlertStepSelect(steps) {
  const sel = $('obs-sim-step-select');
  if (!sel) return;
  const filtered = getFilteredAlertSteps(steps);
  sel.innerHTML = filtered.map((s) =>
    `<option value="${s.id}">[${ALERT_PHASE_LABELS[s.phase] || s.phase}] ${escapeHtml(s.title)}</option>`).join('');
  sel.onchange = () => selectAlertFlowStep(sel.value);
  if (alertFlowSelectedStepId && filtered.some((s) => s.id === alertFlowSelectedStepId)) {
    sel.value = alertFlowSelectedStepId;
  } else if (filtered.length) {
    sel.value = filtered[0].id;
  }
}

function showObsHitlBanner(data) {
  const banner = $('obs-hitl-banner');
  if (!banner || !data?.hitl) return;
  const hitl = data.hitl;
  if (!data.agent_response || hitl.status !== 'awaiting_hitl') {
    banner.classList.add('hidden');
    return;
  }
  banner.classList.remove('hidden');
  if ($('obs-hitl-banner-text')) {
    $('obs-hitl-banner-text').textContent = (hitl.recommendation || 'Approval required').slice(0, 200);
  }
  if ($('obs-hitl-service')) $('obs-hitl-service').textContent = data.service || '—';
  if ($('obs-hitl-runbook')) $('obs-hitl-runbook').textContent = data.runbook_id || '—';
  if ($('obs-hitl-thread')) $('obs-hitl-thread').textContent = hitl.thread_id || '—';
}

function wireObsHitlFromResponse(data) {
  const ar = data.agent_response;
  if (!ar) return;
  if (ar.thread_id) {
    lastThreadId = ar.thread_id;
    updateTraceLinks(ar.thread_id);
  }
  if (ar.status === 'awaiting_hitl') {
    pendingThread = ar.thread_id;
    pendingMode = ar.mode || 'standalone';
    pendingDomain = ar.domain || 'sre';
    pendingChangeRun = {
      data: ar,
      context: { service: data.service, severity: data.severity, error_summary: ar.error_summary },
    };
    setPendingBadge(true);
    populateAutomation(ar, { service: data.service, severity: data.severity });
    showObsHitlBanner(data);
    showToast('warning', 'HITL approval required', 'Open Simulation to approve remediation');
  }
}

function animateAlertFlowSteps(steps, onStep, onComplete) {
  stopAlertFlowAnim();
  alertFlowMaxStepIndex = -1;
  alertFlowJourneyComplete = false;
  alertFlowSelectedStepId = null;
  buildJourneyTrack(steps);
  let idx = 0;
  const tick = () => {
    if (idx >= steps.length) {
      alertFlowJourneyComplete = true;
      updateJourneyClickability();
      if ($('obs-sim-flow-status')) $('obs-sim-flow-status').textContent = 'Journey complete — click any step to inspect';
      if ($('alert-flow-caption')) $('alert-flow-caption').textContent = 'Click pipeline nodes or use the dropdown to review each phase.';
      if (onComplete) onComplete();
      return;
    }
    const step = steps[idx];
    alertFlowMaxStepIndex = idx;
    alertFlowSelectedStepId = step.id;
    highlightJourneyStep(step.id, idx);
    if ($('alert-flow-caption')) $('alert-flow-caption').textContent = `${step.title} — ${step.subtitle || ''}`;
    if ($('obs-sim-flow-status')) $('obs-sim-flow-status').textContent = `Step ${idx + 1}/${steps.length}`;
    onStep(step, idx);
    updateJourneyClickability();
    idx += 1;
    alertFlowAnimTimer = setTimeout(tick, 1200);
  };
  tick();
}

function renderAlertExternalViews(views) {
  if (!views) return;
  const prom = views.prometheus || {};
  const loki = views.loki || {};
  const d = typeof getArchDesign === 'function' ? getArchDesign() : null;
  applyDesignNativeLinks(d, d ? designExplore(d) : []);
  const promEl = $('obs-sim-prom-view');
  if (promEl) {
    const m = prom.metrics || {};
    promEl.innerHTML = `<code>${escapeHtml(prom.query || '')}</code>
      <table class="data-table compact-table"><tbody>
        <tr><td>error_rate</td><td>${m.error_rate_5m != null ? `${(m.error_rate_5m * 100).toFixed(2)}%` : '—'}</td></tr>
        <tr><td>cpu</td><td>${m.cpu_percent ?? '—'}%</td></tr>
        <tr><td>p95</td><td>${m.p95_latency_ms ?? '—'} ms</td></tr>
      </tbody></table>`;
  }
  const grafEl = $('obs-sim-grafana-view');
  if (grafEl) {
    const err = (prom.metrics?.error_rate_5m || 0) * 100;
    grafEl.innerHTML = `<div class="alert-grafana-bar"><div class="alert-grafana-fill" style="width:${Math.min(100, err * 8)}%"></div></div>
      <p class="muted">error_rate · <strong class="priority-p1">${err.toFixed(2)}%</strong></p>`;
  }
  const lokiEl = $('obs-sim-loki-view');
  if (lokiEl) {
    lokiEl.innerHTML = (loki.logs || []).map((l) =>
      `<div class="log-line ${(l.level || 'info').toLowerCase()}"><span class="log-ts">${(l.timestamp || '').slice(11, 19)}</span>${escapeHtml(l.message || '')}</div>`).join('') || '<p class="muted">No logs</p>';
  }
}

function relabelJourneyForDesign(data) {
  const d = typeof getArchDesign === 'function' ? getArchDesign() : null;
  const j = d?.journey;
  if (!data?.steps || !j) return data;
  const apply = (step, pair) => {
    if (!pair) return;
    step.title = pair[0];
    step.subtitle = pair[1];
  };
  data.steps.forEach((step) => {
    if (step.id === 'prometheus') apply(step, j.prometheus);
    if (step.id === 'agent_chroma') apply(step, j.vector);
    if (step.id === 'agent_logs') apply(step, j.logs);
    if (step.id === 'agent_metrics') apply(step, j.metrics);
    if (step.id === 'agent_traces') apply(step, j.traces);
    if (step.id === 'opa_evaluate') apply(step, j.policy);
  });
  if (j.traces && !data.steps.some((s) => s.id === 'agent_traces')) {
    const idx = data.steps.findIndex((s) => s.id === 'agent_metrics');
    const node = {
      id: 'agent_traces',
      phase: 'agent',
      title: j.traces[0],
      subtitle: j.traces[1],
      visual: { type: 'pipeline_node', icon: '🧵', summary: 'Distributed traces in Grafana Tempo (not logs)', badges: [d.name, 'Explore → Tempo'] },
      payload: { node: 'query_traces', backend: 'tempo' },
    };
    data.steps.splice(idx >= 0 ? idx + 1 : data.steps.length - 2, 0, node);
  }
  const tag = $('alert-journey-design');
  if (tag) tag.textContent = `${d.name} · ${d.vector} · ${d.logs} · ${d.metrics}`;
  return data;
}

function applyAlertSimResult(data, { invokeAgent = false } = {}) {
  relabelJourneyForDesign(data);
  alertFlowSimData = data;
  populateAlertStepSelect(data.steps);
  renderAlertExternalViews(data.external_views);
  $('obs-hitl-banner')?.classList.add('hidden');
  animateAlertFlowSteps(data.steps, (step) => {
    selectAlertFlowStep(step.id);
  }, () => {
    if (invokeAgent) {
      wireObsHitlFromResponse(data);
      if (data.hitl?.status === 'awaiting_hitl' && data.agent_response && $('alert-flow-caption')) {
        $('alert-flow-caption').textContent = 'Journey complete — HITL approval required before remediation executes.';
      }
    }
  });
}

async function loadAlertFlowCatalog() {
  try {
    alertFlowCatalog = await api('/api/observability/alerts/catalog');
    renderAlertTypeGrid(alertFlowCatalog);
    await previewAlertFlow(false, { silent: true });
  } catch (err) {
    showToast('error', 'Alert catalog failed', err.message);
  }
}

async function previewAlertFlow(invokeAgent = false, { silent = false } = {}) {
  if (!customAlertPayload && !selectedAlertId) return;
  setButtonLoading($('obs-sim-preview'), !invokeAgent);
  setButtonLoading($('obs-sim-fire'), invokeAgent);
  resetAlertFlowAnim();
  if ($('obs-sim-flow-status')) $('obs-sim-flow-status').textContent = invokeAgent ? 'Firing agent…' : 'Building journey…';
  const designId = typeof getArchDesignId === 'function' ? getArchDesignId() : 'd2';
  const body = customAlertMode && customAlertPayload
    ? { custom_alert: customAlertPayload, invoke_agent: invokeAgent, design_id: designId }
    : { alert_id: selectedAlertId, invoke_agent: invokeAgent, design_id: designId };
  try {
    const data = await api('/api/observability/alerts/simulate', { method: 'POST', body: JSON.stringify(body) });
    applyAlertSimResult(data, { invokeAgent });
    if (!invokeAgent && !silent) showToast('success', 'Walkthrough ready', `${data.steps?.length || 0} steps`);
    else if (data.error) showToast('error', 'Agent fire failed', data.error);
  } catch (err) {
    showToast('error', 'Simulation failed', err.message);
    if ($('obs-sim-flow-status')) $('obs-sim-flow-status').textContent = 'Failed';
  } finally {
    setButtonLoading($('obs-sim-preview'), false);
    setButtonLoading($('obs-sim-fire'), false);
  }
}

async function useCustomAlertFromForm() {
  customAlertMode = true;
  customAlertPayload = {
    service: $('obs-custom-service')?.value || 'checkout-service',
    severity: $('obs-custom-severity')?.value || 'P1',
    error_summary: $('obs-custom-summary')?.value?.trim() || 'Custom alert',
    log_snippet: $('obs-custom-log')?.value || '',
  };
  selectedAlertId = null;
  document.querySelectorAll('.alert-type-card').forEach((b) => b.classList.remove('is-selected'));
  $('obs-custom-alert-form')?.classList.add('is-active-custom');
  showToast('info', 'Custom alert selected', customAlertPayload.service);
  await previewAlertFlow(false);
}

const EVAL_GRAPH_NODES = ['classify', 'rag', 'logs', 'metrics', 'recommend', 'score'];
const EVAL_RING_CIRC = 213.6;
const EVAL_FALLBACK_CASES = [
  { id: 'eval-checkout-redis', service: 'checkout-service', severity: 'P1', expected_runbook_id: 'checkout-redis-pool' },
  { id: 'eval-payment-cpu', service: 'payment-api', severity: 'P1', expected_runbook_id: 'payment-high-cpu' },
  { id: 'eval-auth-errors', service: 'auth-service', severity: 'P2', expected_runbook_id: 'auth-error-spike' },
  { id: 'eval-db-pool', service: 'order-service', severity: 'P1', expected_runbook_id: 'db-pool-exhausted' },
  { id: 'eval-payment-cpu-low-sev', service: 'payment-api', severity: 'P3', expected_runbook_id: 'payment-high-cpu' },
  { id: 'eval-auth-cert-expiry', service: 'auth-service', severity: 'P1', expected_runbook_id: 'auth-error-spike' },
  { id: 'eval-db-slow-queries', service: 'order-service', severity: 'P2', expected_runbook_id: 'db-pool-exhausted' },
  { id: 'eval-checkout-deploy', service: 'checkout-service', severity: 'P1', expected_runbook_id: 'checkout-redis-pool' },
];

let evalGoldenCases = [];
let evalAnimTimers = [];
let evalAnimRunning = false;
let evalAnimCaseIndex = 0;
let evalAnimGraphTimer = null;

function stopEvalRunAnimation() {
  evalAnimTimers.forEach((t) => clearTimeout(t));
  evalAnimTimers = [];
  if (evalAnimGraphTimer) {
    clearInterval(evalAnimGraphTimer);
    evalAnimGraphTimer = null;
  }
  evalAnimRunning = false;
  $('eval-kpi-grid')?.classList.remove('eval-kpi-dim');
  $('eval-metrics-grid')?.classList.remove('eval-kpi-dim');
  document.querySelectorAll('.eval-score-pulse').forEach((el) => el.classList.remove('is-pulsing'));
}

function setEvalRingProgress(pct) {
  const ring = $('eval-ring-progress');
  const label = $('eval-ring-label');
  const p = Math.min(100, Math.max(0, pct));
  if (ring) ring.style.strokeDashoffset = String(EVAL_RING_CIRC * (1 - p / 100));
  if (label) label.textContent = `${Math.round(p)}%`;
}

function setEvalGraphStep(stepIndex) {
  const nodes = document.querySelectorAll('.eval-graph-node');
  const bridges = document.querySelectorAll('.eval-graph-bridge');
  nodes.forEach((n, i) => {
    n.classList.toggle('is-active', i === stepIndex);
    n.classList.toggle('is-done', i < stepIndex);
  });
  bridges.forEach((b, i) => b.classList.toggle('is-active', i < stepIndex));
}

function startEvalGraphCycle() {
  let step = 0;
  setEvalGraphStep(0);
  if (evalAnimGraphTimer) clearInterval(evalAnimGraphTimer);
  evalAnimGraphTimer = setInterval(() => {
    step = (step + 1) % EVAL_GRAPH_NODES.length;
    setEvalGraphStep(step);
  }, 650);
}

function buildEvalCaseTrack(cases) {
  const track = $('eval-case-track');
  if (!track) return;
  track.innerHTML = cases.map((c, i) => `
    <div class="eval-case-chip" data-case-idx="${i}" data-case-id="${escapeHtml(c.id || '')}">
      <strong>${escapeHtml(c.id || `case-${i + 1}`)}</strong>
      <span>${escapeHtml(c.service || '—')} · ${escapeHtml(c.severity || '—')}</span>
    </div>`).join('');
}

function highlightEvalCase(index, total) {
  document.querySelectorAll('.eval-case-chip').forEach((chip, i) => {
    chip.classList.toggle('is-active', i === index);
    if (i < index) chip.classList.add('is-done');
  });
  setEvalRingProgress(total ? ((index + 0.5) / total) * 100 : 0);
  const c = evalGoldenCases[index] || EVAL_FALLBACK_CASES[index];
  if ($('eval-theater-title')) $('eval-theater-title').textContent = c ? `Case ${index + 1}/${total}: ${c.id}` : 'Golden-set regression';
  if ($('eval-theater-sub')) {
    $('eval-theater-sub').textContent = c
      ? `Invoking agent for ${c.service} · expect ${c.expected_runbook_id || 'runbook'}`
      : 'Invoking LangGraph agent per fixture…';
  }
  const captions = [
    'Classifying alert intent…',
    `Querying ${archStack('vector', 'Chroma')} RAG for runbook…`,
    `Pulling ${archStack('logs', 'Loki')} logs…`,
    `Querying ${archStack('metrics', 'Prometheus')} metrics…`,
    'Generating grounded recommendation…',
    'Scoring RAG recall · groundedness · correctness…',
  ];
  if ($('eval-theater-caption')) {
    $('eval-theater-caption').textContent = captions[index % captions.length];
  }
  document.querySelectorAll('.eval-score-pulse').forEach((el, i) => {
    el.classList.toggle('is-pulsing', i === index % 5);
    const fill = el.querySelector('.eval-score-fill');
    if (fill) fill.style.width = `${Math.min(95, 20 + index * 12 + i * 8)}%`;
  });
}

function startEvalRunAnimation(cases) {
  stopEvalRunAnimation();
  evalAnimRunning = true;
  evalAnimCaseIndex = 0;
  evalGoldenCases = cases;
  const theater = $('eval-run-theater');
  const banner = $('eval-gate-banner');
  if (banner) banner.classList.add('hidden');
  if (theater) {
    theater.classList.remove('hidden', 'is-complete', 'eval-pass-theater', 'eval-fail-theater');
  }
  $('eval-kpi-grid')?.classList.add('eval-kpi-dim');
  $('eval-metrics-grid')?.classList.add('eval-kpi-dim');
  buildEvalCaseTrack(cases);
  setEvalRingProgress(0);
  startEvalGraphCycle();
  highlightEvalCase(0, cases.length);

  const advance = () => {
    if (!evalAnimRunning) return;
    evalAnimCaseIndex += 1;
    if (evalAnimCaseIndex >= cases.length) return;
    highlightEvalCase(evalAnimCaseIndex, cases.length);
    evalAnimTimers.push(setTimeout(advance, 3800));
  };
  evalAnimTimers.push(setTimeout(advance, 3800));
}

function applyEvalCaseResults(result) {
  const resultMap = {};
  (result?.cases || []).forEach((c) => { resultMap[c.id] = c; });
  document.querySelectorAll('.eval-case-chip').forEach((chip) => {
    const id = chip.dataset.caseId;
    const rc = resultMap[id];
    chip.classList.remove('is-active');
    chip.classList.add('is-done');
    if (rc) chip.classList.add(rc.passed ? 'pass' : 'fail');
    else chip.classList.add('pass');
  });
}

function animateEvalMetricFills(averages) {
  const keys = ['rag_recall_at_3', 'groundedness', 'correctness', 'tool_call_accuracy', 'p95_latency_ms'];
  const metrics = ['rag', 'ground', 'correct', 'hitl', 'latency'];
  metrics.forEach((m, i) => {
    const el = document.querySelector(`.eval-score-pulse[data-metric="${m}"] .eval-score-fill`);
    const key = keys[i];
    let pct = 0;
    if (key === 'p95_latency_ms') {
      const v = averages?.[key] ?? 0;
      pct = Math.max(8, 100 - Math.min(100, (v / 8000) * 100));
    } else {
      pct = Math.round((averages?.[key] ?? 0) * 100);
    }
    if (el) el.style.width = `${pct}%`;
  });
  document.querySelectorAll('.eval-score-pulse').forEach((el) => el.classList.remove('is-pulsing'));
}

async function finishEvalRunAnimation(result) {
  evalAnimRunning = false;
  evalAnimTimers.forEach((t) => clearTimeout(t));
  evalAnimTimers = [];
  if (evalAnimGraphTimer) {
    clearInterval(evalAnimGraphTimer);
    evalAnimGraphTimer = null;
  }
  const cases = evalGoldenCases.length ? evalGoldenCases : EVAL_FALLBACK_CASES;
  const theater = $('eval-run-theater');
  if (!theater) return;

  for (let i = evalAnimCaseIndex; i < cases.length; i += 1) {
    highlightEvalCase(i, cases.length);
    await new Promise((r) => setTimeout(r, 180));
  }
  setEvalGraphStep(EVAL_GRAPH_NODES.length);
  setEvalRingProgress(100);
  applyEvalCaseResults(result);
  animateEvalMetricFills(result?.averages || {});

  const passed = result?.passed;
  theater.classList.add('is-complete', passed ? 'eval-pass-theater' : 'eval-fail-theater');
  if ($('eval-theater-title')) {
    $('eval-theater-title').textContent = passed ? '✓ Eval gate PASSED' : '✗ Eval gate FAILED';
  }
  if ($('eval-theater-sub')) {
    $('eval-theater-sub').textContent = `${result?.cases_passed ?? '?'}/${result?.case_count ?? cases.length} golden cases · scores synced to ${archStack('llmops', 'Langfuse')} & MLflow`;
  }
  if ($('eval-theater-caption')) {
    $('eval-theater-caption').textContent = passed
      ? 'All thresholds met — RAG, groundedness, correctness, HITL accuracy, latency'
      : 'One or more cases or averages below threshold — inspect table below';
  }
  if ($('eval-theater-badge')) {
    $('eval-theater-badge').textContent = passed ? 'GATE PASS' : 'GATE FAIL';
    $('eval-theater-badge').style.background = passed ? 'rgba(52, 211, 153, 0.25)' : 'rgba(248, 113, 113, 0.2)';
    $('eval-theater-badge').style.color = passed ? '#047857' : '#b91c1c';
  }

  $('eval-kpi-grid')?.classList.remove('eval-kpi-dim');
  $('eval-metrics-grid')?.classList.remove('eval-kpi-dim');

  evalAnimTimers.push(setTimeout(() => {
    theater.classList.add('hidden');
    theater.classList.remove('is-complete', 'eval-pass-theater', 'eval-fail-theater');
    if ($('eval-theater-badge')) {
      $('eval-theater-badge').textContent = 'EVAL RUNNING';
      $('eval-theater-badge').style.background = '';
      $('eval-theater-badge').style.color = '';
    }
  }, 4500));
}

async function runEvalSuite() {
  const btn = $('eval-gate-run');
  setButtonLoading(btn, true);

  let cases = evalGoldenCases;
  if (!cases.length) {
    try {
      const dash = await api('/api/evaluation/dashboard');
      cases = dash.golden_cases || [];
      evalGoldenCases = cases;
    } catch (_) { /* use fallback */ }
  }
  if (!cases.length) cases = EVAL_FALLBACK_CASES;

  startEvalRunAnimation(cases);

  try {
    const result = await api('/api/evaluation/run', { method: 'POST', body: '{}' });
    await finishEvalRunAnimation(result);
    renderEvalDashboard({ latest: result, history: [], golden_count: result.case_count, golden_cases: cases });
    await loadEvalDashboard();
    loadLangfuseDashboard();
    showToast(result.passed ? 'success' : 'warning', result.passed ? 'Eval gate passed' : 'Eval gate failed', `${result.cases_passed}/${result.case_count} cases`);
  } catch (err) {
    stopEvalRunAnimation();
    $('eval-run-theater')?.classList.add('hidden');
    const banner = $('eval-gate-banner');
    if (banner) {
      banner.classList.remove('hidden');
      banner.className = 'eval-gate-banner eval-fail';
      banner.textContent = `Eval run failed: ${err.message}`;
    }
    showToast('error', 'Eval run failed', err.message);
  } finally {
    setButtonLoading(btn, false);
  }
}

async function loadLinks() {
  try {
    observabilityLinks = IS_CAPTURE
      ? {
        grafana: 'http://localhost:3001',
        prometheus: 'http://localhost:9090',
        langfuse: 'http://localhost:3000',
        mlflow: 'http://localhost:5001',
        opa: 'http://localhost:8181',
        weaviate: 'http://localhost:8088',
        kibana: 'http://localhost:5601',
        phoenix: 'http://localhost:6006',
        opensearch: 'http://localhost:9201',
        opensearch_dashboards: 'http://localhost:5602',
        mimir: 'http://localhost:9009',
        tempo: 'http://localhost:3200',
      }
      : await api('/api/config/links');
    const map = {
      'link-opa-console': observabilityLinks.opa || 'http://localhost:8181',
      'grd-link-opa': observabilityLinks.opa || 'http://localhost:8181',
      'link-prometheus-alert': observabilityLinks.prometheus || observabilityLinks.mimir || 'http://localhost:8428',
      'link-grafana-alert': observabilityLinks.grafana,
      'link-mlflow-eval': observabilityLinks.mlflow,
      'link-eval-langfuse': observabilityLinks.phoenix || observabilityLinks.langfuse,
      'link-eval-mlflow': observabilityLinks.mlflow,
      'link-trace': observabilityLinks.phoenix || observabilityLinks.langfuse,
      'link-trace-eval': observabilityLinks.phoenix || observabilityLinks.langfuse,
      'obs-link-grafana': observabilityLinks.grafana,
      'obs-link-prometheus': observabilityLinks.prometheus || observabilityLinks.mimir,
      'obs-link-loki': observabilityLinks.kibana || observabilityLinks.opensearch_dashboards || observabilityLinks.loki,
    };
    Object.entries(map).forEach(([id, href]) => { if ($(id) && href) $(id).href = href; });
    renderStackExplore();
  } catch (_) { /* optional */ }
}

async function loadIngestStatus() {
  try {
    const data = await api('/api/ingest/status');
    $('ingest-health-label').textContent = 'Healthy';
    $('st-collection').textContent = data.active_collection || '—';
    $('st-version').textContent = data.index_version || '—';
    const drive = data.drive || {};
    if ($('st-drive')) {
      if (!drive.enabled) {
        $('st-drive').textContent = 'Disabled (local seed runbooks only)';
      } else if (drive.ready) {
        $('st-drive').textContent = `Enabled · folder ${drive.folder_id}`;
      } else {
        $('st-drive').textContent = 'Enabled but not ready — add service account JSON + folder ID';
      }
    }
    updateIngestFlowMeta(data);
    const job = data.latest_job;
    if (job) {
      renderIngestJob(job);
      if (!INGEST_JOB_TERMINAL.has(normalizeJobStatus(job.status))) {
        pollIngestJob(job.id);
      }
    } else {
      setIngestJobLive(false);
      setIngestJobMsg('');
    }
  } catch (_) {
    $('ingest-health-label').textContent = 'Unavailable';
  }
}

function updateIngestFlowMeta(data) {
  const indexEl = $('ing-flow-index');
  const driveEl = $('ing-flow-drive');
  const jobEl = $('ing-flow-job');
  if (!indexEl) return;
  indexEl.textContent = data.active_collection
    ? `${data.index_version || '—'} · ${data.active_collection.split('-').slice(-2).join('-')}`
    : '—';
  const drive = data.drive || {};
  if (driveEl) {
    if (!drive.enabled) driveEl.textContent = 'Disabled · local seed only';
    else if (drive.ready) driveEl.textContent = 'Connected · syncing enabled';
    else driveEl.textContent = 'Enabled · awaiting credentials';
  }
  const job = data.latest_job;
  if (jobEl) {
    jobEl.textContent = job
      ? `${normalizeJobStatus(job.status)} · ${job.job_type || 'reindex'}`
      : 'No jobs yet';
  }
}

function startIngestFlowAnim() {
  stopIngestFlowAnim();
  const root = $('ing-flow-anim');
  if (!root) return;
  const stages = [...root.querySelectorAll('.ing-flow-stage')];
  const captionEl = $('ing-flow-caption');
  ingestFlowCaptionIdx = 0;

  const tick = () => {
    const captions = ingestFlowCaptions();
    const step = captions[ingestFlowCaptionIdx];
    stages.forEach((el) => el.classList.toggle('active', el.dataset.stage === step.stage));
    if (captionEl) captionEl.textContent = step.text;
    ingestFlowCaptionIdx = (ingestFlowCaptionIdx + 1) % captions.length;
    ingestFlowAnimTimer = setTimeout(tick, 2400);
  };
  tick();
}

function stopIngestFlowAnim() {
  if (ingestFlowAnimTimer) {
    clearTimeout(ingestFlowAnimTimer);
    ingestFlowAnimTimer = null;
  }
}

async function loadIngestIndex() {
  const summary = $('index-summary');
  const grid = $('chroma-runbooks-grid');
  const stats = $('chroma-stats-grid');
  if (!summary || !grid) return;
  summary.textContent = `Loading ${archStack('vector', 'Chroma')} index…`;
  grid.innerHTML = '<div class="chroma-empty">Loading vectors…</div>';
  if (stats) stats.innerHTML = '';
  try {
    const data = await api('/api/ingest/index?limit=500');
    window.__lastIndexData = data;
    if (data.error) {
      summary.textContent = `Index unavailable: ${data.error}`;
      grid.innerHTML = `<div class="chroma-empty chroma-empty-error">${escapeHtml(data.error)}</div>`;
      return;
    }
    summary.textContent = `${data.collection} · v${data.index_version || '—'} · ${data.distance_metric || 'cosine'} distance · ${data.embedding_model || 'embeddings'}`;
    renderChromaStats(data);
    populateChromaFilters(data);
    renderChromaRunbooks(data.runbooks || []);
    renderVectorSpaceMap(data);
    loadChromaCollections();
    if ($('chroma-runbook-count')) {
      $('chroma-runbook-count').textContent = `${data.runbook_count} runbooks · ${data.total_in_collection || data.total_chunks} vectors`;
    }
  } catch (err) {
    summary.textContent = `Failed to load index: ${err.message}`;
    grid.innerHTML = `<div class="chroma-empty chroma-empty-error">${escapeHtml(err.message)}</div>`;
  }
}

function renderChromaStats(data) {
  const el = $('chroma-stats-grid');
  if (!el) return;
  const cards = [
    { label: 'Vectors', value: data.total_in_collection ?? data.total_chunks, sub: 'stored chunks', tone: 'teal' },
    { label: 'Runbooks', value: data.runbook_count, sub: 'unique sources', tone: 'violet' },
    { label: 'Dimensions', value: data.embedding_dims || '—', sub: 'embedding size', tone: 'blue' },
    { label: 'Collection', value: (data.collection || '—').split('-').slice(-2).join('-') || data.collection, sub: data.collection, tone: 'green', mono: true },
  ];
  el.innerHTML = cards.map((c) => `
    <div class="chroma-stat chroma-stat-${c.tone}">
      <span class="chroma-stat-label">${c.label}</span>
      <strong class="${c.mono ? 'mono-accent' : ''}">${escapeHtml(String(c.value))}</strong>
      <span class="chroma-stat-sub">${escapeHtml(c.sub)}</span>
    </div>
  `).join('');
}

async function loadChromaCollections() {
  const el = $('chroma-collections-list');
  if (!el) return;
  el.innerHTML = '<div class="chroma-empty">Loading collections…</div>';
  try {
    const data = await api('/api/ingest/index/collections');
    if (data.error) {
      el.innerHTML = `<div class="chroma-empty chroma-empty-error">${escapeHtml(data.error)}</div>`;
      return;
    }
    const cols = data.collections || [];
    if (!cols.length) {
      el.innerHTML = '<div class="chroma-empty">No collections found.</div>';
      return;
    }
    el.innerHTML = cols.map((col) => `
      <div class="chroma-collection-row ${col.is_active ? 'active' : ''}">
        <div class="chroma-collection-main">
          <code>${escapeHtml(col.name)}</code>
          ${col.is_active ? '<span class="pill succeeded">active</span>' : ''}
        </div>
        <div class="chroma-collection-meta">
          <span>${col.count ?? 0} vectors</span>
          ${data.index_version && col.is_active ? `<span>v${escapeHtml(data.index_version)}</span>` : ''}
          ${data.activated_at && col.is_active ? `<span>${escapeHtml(formatUtc(data.activated_at))}</span>` : ''}
        </div>
      </div>
    `).join('');
  } catch (err) {
    el.innerHTML = `<div class="chroma-empty chroma-empty-error">${escapeHtml(err.message)}</div>`;
  }
}

function populateChromaFilters(data) {
  const fill = (id, values, label) => {
    const sel = $(id);
    if (!sel) return;
    sel.innerHTML = `<option value="">${label}</option>`;
    (values || []).forEach((v) => {
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = v;
      sel.appendChild(opt);
    });
  };
  fill('chroma-filter-service', data.services, 'All services');
  fill('chroma-filter-severity', data.severities, 'All severities');
  fill('chroma-filter-runbook', (data.runbooks || []).map((r) => r.runbook_id), 'All runbooks');
}

function severityPill(sev) {
  if (!sev) return '—';
  const cls = String(sev).startsWith('P1') ? 'p1' : 'open';
  return `<span class="pill ${cls}">${escapeHtml(sev)}</span>`;
}

function renderEmbeddingSparkline(preview) {
  if (!preview?.length) return '<span class="muted">No preview</span>';
  const max = Math.max(...preview.map(Math.abs), 0.001);
  return `<div class="emb-sparkline">${preview.map((v, i) => {
    const h = Math.max(4, Math.round((Math.abs(v) / max) * 100));
    const tone = v >= 0 ? 'pos' : 'neg';
    return `<span class="emb-bar ${tone}" style="height:${h}%" title="${v}"></span>`;
  }).join('')}</div>`;
}

const VSPACE_COLORS = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#3b82f6', '#14b8a6'];
const VSPACE_PAD = { l: 36, r: 20, t: 24, b: 36 };
const VSPACE_W = 440;
const VSPACE_H = 300;

let vspacePoints = [];
let vspaceProjection = null;
const vspaceRunbookColors = {};

function runbookColor(runbookId) {
  if (vspaceRunbookColors[runbookId]) return vspaceRunbookColors[runbookId];
  const hash = String(runbookId).split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  vspaceRunbookColors[runbookId] = VSPACE_COLORS[hash % VSPACE_COLORS.length];
  return vspaceRunbookColors[runbookId];
}

function collectVectorPoints(data) {
  const points = [];
  (data.runbooks || []).forEach((rb) => {
    (rb.chunks || []).forEach((c) => {
      if (!c.embedding_preview?.length) return;
      points.push({
        id: c.id,
        runbook_id: rb.runbook_id,
        vector: c.embedding_preview,
        chunk: c,
        runbook: rb,
      });
    });
  });
  return points;
}

function buildVectorProjection(vectors) {
  if (!vectors.length) return null;
  const dims = vectors[0].length;
  const mean = Array(dims).fill(0);
  vectors.forEach((v) => v.forEach((x, i) => { mean[i] += x; }));
  mean.forEach((_, i) => { mean[i] /= vectors.length; });
  return {
    mean,
    project(vec) {
      if (!vec?.length) return { x: 0, y: 0 };
      let x = 0;
      let y = 0;
      for (let i = 0; i < vec.length; i++) {
        const c = vec[i] - (mean[i] || 0);
        x += c * Math.cos(i * 0.417);
        y += c * Math.sin(i * 0.417);
      }
      return { x, y };
    },
  };
}

function scaleProjectedPoints(rawPoints, projectFn, extraVecs = []) {
  const projected = rawPoints.map((p) => ({ ...p, ...projectFn(p.vector) }));
  extraVecs.forEach((v) => projected.push({ ...projectFn(v), extra: true }));
  const xs = projected.map((p) => p.x);
  const ys = projected.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;
  const innerW = VSPACE_W - VSPACE_PAD.l - VSPACE_PAD.r;
  const innerH = VSPACE_H - VSPACE_PAD.t - VSPACE_PAD.b;
  return rawPoints.map((p) => {
    const { x, y } = projectFn(p.vector);
    return {
      ...p,
      x,
      y,
      sx: VSPACE_PAD.l + ((x - minX) / rangeX) * innerW,
      sy: VSPACE_PAD.t + ((maxY - y) / rangeY) * innerH,
      bounds: { minX, maxX, minY, maxY, rangeX, rangeY, innerW, innerH },
    };
  });
}

function projectToSvg(vec, bounds) {
  const { x, y } = vspaceProjection.project(vec);
  return {
    x,
    y,
    sx: VSPACE_PAD.l + ((x - bounds.minX) / bounds.rangeX) * bounds.innerW,
    sy: VSPACE_PAD.t + ((bounds.maxY - y) / bounds.rangeY) * bounds.innerH,
  };
}

function renderVectorSpaceGrid() {
  const g = $('chroma-vspace-grid');
  if (!g) return;
  const lines = [];
  for (let i = 1; i <= 4; i++) {
    const x = VSPACE_PAD.l + (i / 5) * (VSPACE_W - VSPACE_PAD.l - VSPACE_PAD.r);
    const y = VSPACE_PAD.t + (i / 5) * (VSPACE_H - VSPACE_PAD.t - VSPACE_PAD.b);
    lines.push(`<line class="vspace-grid-line" x1="${x}" y1="${VSPACE_PAD.t}" x2="${x}" y2="${VSPACE_H - VSPACE_PAD.b}"/>`);
    lines.push(`<line class="vspace-grid-line" x1="${VSPACE_PAD.l}" y1="${y}" x2="${VSPACE_W - VSPACE_PAD.r}" y2="${y}"/>`);
  }
  g.innerHTML = lines.join('');
}

function renderDimStrip(preview, { label = 'Index average', highlight = false } = {}) {
  const strip = $('chroma-dim-strip');
  const previewEl = $('chroma-dim-preview');
  if (!strip) return;
  const bars = 64;
  const src = preview?.length ? preview : null;
  const vals = [];
  if (src) {
    for (let i = 0; i < bars; i++) {
      const idx = Math.floor((i / bars) * src.length);
      vals.push(src[idx] ?? 0);
    }
  } else {
    for (let i = 0; i < bars; i++) vals.push(Math.sin(i * 0.4) * 0.5);
  }
  const max = Math.max(...vals.map(Math.abs), 0.001);
  strip.innerHTML = vals.map((v, i) => {
    const h = Math.max(8, Math.round((Math.abs(v) / max) * 100));
    const cls = highlight ? 'query' : (v >= 0 ? 'pos' : 'neg');
    return `<span class="chroma-dim-bar ${cls}" style="height:${h}%;animation-delay:${(i * 0.03).toFixed(2)}s" title="${v.toFixed(3)}"></span>`;
  }).join('');
  if (previewEl) {
    previewEl.innerHTML = src
      ? `<strong>${escapeHtml(label)}</strong> · ${bars} sample dims · range [${Math.min(...src).toFixed(2)}, ${Math.max(...src).toFixed(2)}]`
      : '<span class="muted">Hover a point or run a query to preview vector components</span>';
  }
}

function renderVectorSpaceLegend(points) {
  const el = $('chroma-vspace-legend');
  if (!el) return;
  const runbooks = [...new Set(points.map((p) => p.runbook_id))];
  el.innerHTML = runbooks.map((id) => `
    <span class="chroma-vspace-legend-item">
      <span class="chroma-vspace-legend-dot" style="background:${runbookColor(id)}"></span>
      <code>${escapeHtml(id)}</code>
    </span>
  `).join('');
}

function starPoints(cx, cy, outer, inner) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const r = i % 2 === 0 ? outer : inner;
    const a = (-Math.PI / 2) + (i * Math.PI) / 5;
    pts.push(`${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`);
  }
  return pts.join(' ');
}

function selectVectorSpacePoint(id) {
  document.querySelectorAll('.vspace-point').forEach((el) => {
    el.classList.toggle('selected', el.dataset.id === id);
    el.classList.toggle('dimmed', Boolean(id && el.dataset.id !== id));
  });
}

function renderVectorSpaceMap(data) {
  Object.keys(vspaceRunbookColors).forEach((k) => delete vspaceRunbookColors[k]);
  const rawPoints = collectVectorPoints(data);
  const pointsG = $('chroma-vspace-points');
  const linksG = $('chroma-vspace-links');
  const queryG = $('chroma-vspace-query');
  const hint = $('chroma-vspace-hint');
  if (!pointsG) return;

  renderVectorSpaceGrid();
  if (linksG) linksG.innerHTML = '';
  if (queryG) queryG.innerHTML = '';

  if (!rawPoints.length) {
    vspacePoints = [];
    vspaceProjection = null;
    pointsG.innerHTML = '';
    renderVectorSpaceLegend([]);
    renderDimStrip(null);
    if (hint) hint.textContent = 'No embedding previews available — reindex runbooks to populate the vector map.';
    return;
  }

  const vectors = rawPoints.map((p) => p.vector);
  vspaceProjection = buildVectorProjection(vectors);
  vspacePoints = scaleProjectedPoints(rawPoints, vspaceProjection.project);
  window.__vspaceBounds = vspacePoints[0]?.bounds;

  pointsG.innerHTML = vspacePoints.map((p, i) => {
    const color = runbookColor(p.runbook_id);
    return `
      <g class="vspace-point-group">
        <circle class="vspace-point" cx="${p.sx.toFixed(1)}" cy="${p.sy.toFixed(1)}" r="7"
          fill="${color}" data-id="${escapeHtml(p.id)}" style="animation-delay:${i * 0.08}s"/>
        <text class="vspace-point-label" x="${(p.sx + 10).toFixed(1)}" y="${(p.sy + 3).toFixed(1)}">${escapeHtml(p.runbook_id)}</text>
      </g>`;
  }).join('');

  pointsG.querySelectorAll('.vspace-point').forEach((el) => {
    el.addEventListener('mouseenter', () => {
      const pt = vspacePoints.find((p) => p.id === el.dataset.id);
      if (pt) renderDimStrip(pt.vector, { label: pt.runbook_id });
    });
    el.addEventListener('mouseleave', () => {
      if (!$('chroma-vspace-query')?.innerHTML) {
        const avg = vectors[0].map((_, i) => vectors.reduce((s, v) => s + v[i], 0) / vectors.length);
        renderDimStrip(avg, { label: 'Collection average' });
      }
    });
    el.addEventListener('click', () => {
      const pt = vspacePoints.find((p) => p.id === el.dataset.id);
      if (pt) {
        selectVectorSpacePoint(pt.id);
        openChunkInspector({ ...pt.chunk, metadata: pt.chunk.metadata }, { runbook: pt.runbook });
      }
    });
  });

  renderVectorSpaceLegend(vspacePoints);
  const avg = vectors[0].map((_, i) => vectors.reduce((s, v) => s + v[i], 0) / vectors.length);
  renderDimStrip(avg, { label: 'Collection average' });
  if (hint) hint.textContent = 'Hover points to inspect dimensions · click to open chunk · run a query to see ★ search vector';
}

function highlightVectorSpaceQuery(queryData) {
  const queryG = $('chroma-vspace-query');
  const linksG = $('chroma-vspace-links');
  const hint = $('chroma-vspace-hint');
  if (!queryG || !vspaceProjection || !queryData?.query_embedding_preview?.length || !vspacePoints.length) return;

  queryG.innerHTML = '';
  if (linksG) linksG.innerHTML = '';

  const bounds = window.__vspaceBounds || vspacePoints[0].bounds;
  const qPos = projectToSvg(queryData.query_embedding_preview, bounds);
  const hitIds = new Set((queryData.results || []).map((r) => r.id));

  document.querySelectorAll('.vspace-point').forEach((el) => {
    el.classList.toggle('dimmed', !hitIds.has(el.dataset.id));
    el.classList.toggle('selected', hitIds.has(el.dataset.id));
  });

  if (linksG) {
    linksG.innerHTML = (queryData.results || []).slice(0, 3).map((hit, i) => {
      const pt = vspacePoints.find((p) => p.id === hit.id);
      if (!pt) return '';
      return `<line class="vspace-link" x1="${qPos.sx.toFixed(1)}" y1="${qPos.sy.toFixed(1)}" x2="${pt.sx.toFixed(1)}" y2="${pt.sy.toFixed(1)}" style="animation-delay:${i * 0.15}s"/>`;
    }).join('');
  }

  queryG.innerHTML = `
    <circle class="vspace-query-ring" cx="${qPos.sx.toFixed(1)}" cy="${qPos.sy.toFixed(1)}" r="12"/>
    <polygon class="vspace-query-star" points="${starPoints(qPos.sx, qPos.sy, 10, 4.5)}"/>
  `;

  renderDimStrip(queryData.query_embedding_preview, { label: `Query: "${queryData.query}"`, highlight: true });
  if (hint) hint.textContent = `★ = your query vector · dashed lines = top ${Math.min(3, queryData.results?.length || 0)} cosine-nearest chunks`;
}

function renderChromaRunbooks(runbooks) {
  const grid = $('chroma-runbooks-grid');
  if (!grid) return;
  if (!runbooks.length) {
    grid.innerHTML = '<div class="chroma-empty">No vectors indexed yet — run Reindex on Status & Actions.</div>';
    return;
  }
  grid.innerHTML = runbooks.map((rb) => `
    <article class="chroma-runbook-card" data-runbook="${escapeHtml(rb.runbook_id)}">
      <header class="chroma-rb-head">
        <div class="chroma-rb-icon">${macIcon('ingestion', 'sm').replace('mac-icon', 'mac-icon chroma-rb-mac')}</div>
        <div>
          <h5><code>${escapeHtml(rb.runbook_id)}</code></h5>
          <div class="chroma-rb-meta">${severityPill(rb.severity)} <span class="muted">${escapeHtml(rb.service || '—')}</span></div>
        </div>
        <span class="chroma-chunk-badge">${rb.chunk_count} chunks</span>
      </header>
      <p class="chroma-rb-source muted">${escapeHtml(rb.source || `${rb.runbook_id}.md`)} · ${rb.total_chars || 0} chars</p>
      <div class="chroma-chunk-list">
        ${rb.chunks.map((c) => `
          <button type="button" class="chroma-chunk-row" data-chunk-id="${escapeHtml(c.id)}">
            <span class="chroma-chunk-idx">#${c.chunk_index}</span>
            <span class="chroma-chunk-preview">${escapeHtml(c.preview)}</span>
            <span class="chroma-chunk-meta">${c.embedding_dims || '—'}d · ${c.char_count}c</span>
          </button>
        `).join('')}
      </div>
    </article>
  `).join('');

  grid.querySelectorAll('.chroma-chunk-row').forEach((btn) => {
    btn.addEventListener('click', () => {
      const rb = runbooks.find((r) => r.chunks.some((c) => c.id === btn.dataset.chunkId));
      const chunk = rb?.chunks.find((c) => c.id === btn.dataset.chunkId);
      if (chunk) openChunkInspector(chunk, { runbook: rb });
    });
  });
}

function openChunkInspector(chunk, { runbook, queryHit } = {}) {
  const panel = $('chroma-inspector');
  const body = $('chroma-inspector-body');
  if (!panel || !body) return;
  panel.classList.remove('hidden');
  selectVectorSpacePoint(chunk.id);
  document.querySelectorAll('.chroma-chunk-row, .chroma-hit-row').forEach((el) => {
    el.classList.toggle('selected', el.dataset.chunkId === chunk.id);
  });

  const metaRows = Object.entries(chunk.metadata || chunk.meta || {}).filter(([k]) => !['chunk_index'].includes(k));
  body.innerHTML = `
    <div class="chroma-inspector-id"><code>${escapeHtml(chunk.id)}</code></div>
    ${queryHit ? `<div class="chroma-sim-bar"><span>Similarity</span><strong>${Math.round((queryHit.similarity || 0) * 100)}%</strong><div class="chroma-sim-track"><div class="chroma-sim-fill" style="width:${Math.round((queryHit.similarity || 0) * 100)}%"></div></div></div>` : ''}
    <dl class="chroma-meta-grid">
      <div><dt>runbook</dt><dd><code>${escapeHtml(chunk.runbook_id || runbook?.runbook_id || '—')}</code></dd></div>
      <div><dt>service</dt><dd>${escapeHtml(chunk.service || runbook?.service || '—')}</dd></div>
      <div><dt>severity</dt><dd>${severityPill(chunk.severity || runbook?.severity)}</dd></div>
      <div><dt>chunk</dt><dd>#${chunk.chunk_index ?? '—'} · ${chunk.char_count || 0} chars · ~${chunk.token_estimate || '?'} tokens</dd></div>
      <div><dt>distance</dt><dd>${queryHit?.distance != null ? queryHit.distance.toFixed(4) : '—'} (cosine)</dd></div>
    </dl>
    <h5>Document</h5>
    <pre class="chroma-doc-full">${escapeHtml(chunk.document || chunk.preview || '')}</pre>
    <h5>Metadata</h5>
    <pre class="chroma-meta-json">${escapeHtml(JSON.stringify(Object.fromEntries(metaRows.length ? metaRows : [['runbook_id', chunk.runbook_id]]), null, 2))}</pre>
    <h5>Embedding preview <span class="muted">(first ${(chunk.embedding_preview || []).length} dims)</span></h5>
    ${renderEmbeddingSparkline(chunk.embedding_preview)}
  `;
}

async function runChromaQuery(e) {
  e.preventDefault();
  const query = $('chroma-query-input')?.value?.trim();
  if (!query) return;
  const resultsEl = $('chroma-query-results');
  if (!resultsEl) return;
  resultsEl.classList.remove('hidden');
  resultsEl.innerHTML = '<div class="chroma-empty">Running semantic query…</div>';
  const btn = e.target.querySelector('button[type="submit"]');
  setButtonLoading(btn, true);
  try {
    const body = {
      query,
      n_results: Number($('chroma-n-results')?.value || 5),
      service: $('chroma-filter-service')?.value || null,
      severity: $('chroma-filter-severity')?.value || null,
      runbook_id: $('chroma-filter-runbook')?.value || null,
    };
    if (!body.service) delete body.service;
    if (!body.severity) delete body.severity;
    if (!body.runbook_id) delete body.runbook_id;

    const data = await api('/api/ingest/index/query', { method: 'POST', body: JSON.stringify(body) });
    if (data.error) {
      resultsEl.innerHTML = `<div class="chroma-empty chroma-empty-error">${escapeHtml(data.error)}</div>`;
      return;
    }
    if (!data.results?.length) {
      resultsEl.innerHTML = '<div class="chroma-empty">No matches — try a broader query or remove filters.</div>';
      return;
    }
    const whereLabel = data.where ? ` · filter ${JSON.stringify(data.where)}` : '';
    resultsEl.innerHTML = `
      <div class="chroma-query-head">
        <strong>${data.n_results} results</strong>
        <span class="muted">"${escapeHtml(data.query)}"${whereLabel}</span>
      </div>
      <div class="chroma-hits">
        ${data.results.map((hit) => `
          <button type="button" class="chroma-hit-row" data-chunk-id="${escapeHtml(hit.id)}">
            <span class="chroma-hit-rank">#${hit.rank}</span>
            <div class="chroma-hit-body">
              <div class="chroma-hit-top">
                <code>${escapeHtml(hit.runbook_id || '—')}</code>
                ${severityPill(hit.severity)}
                <span class="chroma-sim-pill">${Math.round((hit.similarity || 0) * 100)}% match</span>
              </div>
              <p>${escapeHtml(hit.preview)}</p>
            </div>
            <span class="chroma-hit-dist">d=${hit.distance?.toFixed(4) ?? '—'}</span>
          </button>
        `).join('')}
      </div>
    `;
    resultsEl.querySelectorAll('.chroma-hit-row').forEach((row) => {
      row.addEventListener('click', async () => {
        try {
          const detail = await api(`/api/ingest/index/chunks/${encodeURIComponent(row.dataset.chunkId)}`);
          openChunkInspector({ ...detail.chunk, metadata: detail.chunk.metadata }, { queryHit: data.results.find((h) => h.id === row.dataset.chunkId) });
        } catch (_) {
          const hit = data.results.find((h) => h.id === row.dataset.chunkId);
          if (hit) openChunkInspector({ ...hit, document: hit.document, metadata: hit.metadata, char_count: hit.preview?.length }, { queryHit: hit });
        }
      });
    });
    highlightVectorSpaceQuery(data);
  } catch (err) {
    resultsEl.innerHTML = `<div class="chroma-empty chroma-empty-error">${escapeHtml(err.message)}</div>`;
  } finally {
    setButtonLoading(btn, false);
  }
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function renderTicketDetail(ticket) {
  selectedTicket = ticket;
  show($('ticket-detail'));
  hide($('tickets-empty'));
  const rows = [
    ['ticket_id', `<code>${ticket.ticket_id}</code>`],
    ['service', ticket.service],
    ['severity', `<span class="pill p1">${ticket.severity}</span>`],
    ['status', `<span class="pill open">${ticket.status}</span>`],
    ['runbook_id', ticket.runbook_id],
    ['summary', ticket.summary],
    ['approved_by', ticket.approved_by],
  ];
  $('ticket-detail-body').innerHTML = rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('');
  $('td-created').textContent = formatUtc(ticket.created_at);
  $('td-approved').textContent = ticket.approved_by;
  $('ticket-json-box').textContent = JSON.stringify(ticket, null, 2);
  hide($('ticket-json-box'));
}

async function loadTickets() {
  try {
    const data = await api('/api/tickets');
    const tbody = $('tickets-body');
    tbody.innerHTML = '';
    const tickets = data.tickets || [];
    if (!tickets.length) {
      show($('tickets-empty'));
      hide($('ticket-detail'));
      return;
    }
    hide($('tickets-empty'));
    tickets.forEach((t, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td><code>${t.ticket_id}</code></td><td>${t.service}</td><td><span class="pill p1">${t.severity}</span></td><td><span class="pill open">${t.status}</span></td><td>${t.runbook_id}</td><td>${t.summary}</td><td>${t.approved_by}</td>`;
      tr.addEventListener('click', () => {
        document.querySelectorAll('.tickets-table tbody tr').forEach((r) => r.classList.remove('selected'));
        tr.classList.add('selected');
        renderTicketDetail(t);
        switchSection('actions', 'act-detail');
      });
      tbody.appendChild(tr);
      if (i === 0) { tr.classList.add('selected'); renderTicketDetail(t); }
    });
  } catch (err) {
    $('tickets-empty').textContent = err.message;
    show($('tickets-empty'));
  }
}

async function submitApproval(approved) {
  if (!pendingThread) return;
  if (approved && lastOpaEvaluation && !lastOpaEvaluation.allowed) {
    showToast('error', `${archStack('policy', 'OPA')} denied`, 'Policy blocks this action — change severity to P1 or use non-destructive remediation.');
    switchSection('simulation', 'auto-opa');
    return;
  }
  const banner = $('automation-banner');
  const ctxCard = $('ctx-hitl-card');
  const payload = hitlDecisionPayload();
  if (!approved) {
    try {
      await api('/api/agents/approve', {
        method: 'POST',
        body: JSON.stringify({ ...payload, approved: false }),
      });
    } catch (err) {
      showToast('error', 'Reject failed', err.message);
      return;
    }
    animateRejection($('opspilot-deny'), banner || ctxCard);
    markAutomationRejected();
    hide($('hitl-panel'));
    hide(ctxCard);
    pendingThread = null;
    pendingChangeRun = null;
    updateContextPanel();
    await loadHitlHistory();
    switchSection('simulation', 'auto-history');
    return;
  }
  try {
    const data = await api('/api/agents/approve', {
      method: 'POST',
      body: JSON.stringify({ ...payload, approved: true }),
    });
    animateApproval($('opspilot-approve') || $('ctx-approve'), banner || ctxCard);
    renderResult(data);
    hide($('hitl-panel'));
    hide(ctxCard);
    markAutomationCompleted(data.ticket);
    pendingThread = null;
    pendingChangeRun = null;
    await loadTickets();
    await loadHitlHistory();
    if (isPersistedTicket(data.ticket)) {
      renderTicketDetail(data.ticket);
      switchSection('actions', 'act-detail');
    } else {
      switchSection('simulation', 'auto-history');
    }
  } catch (err) {
    showToast('error', 'Approve failed', err.message);
    $('hitl-text').textContent = `Approve failed: ${err.message}`;
    $('cr-recommendation').textContent = `Approve failed: ${err.message}`;
  }
}

async function loadPendingFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const section = params.get('section')
    || (params.get('view') === 'opspilot' ? 'simulation' : null);
  const thread = params.get('thread');
  if ((section !== 'simulation' && section !== 'automation') || !thread) return false;
  try {
    const data = await api(`/api/agents/state/${encodeURIComponent(thread)}`);
    if (data.status !== 'awaiting_hitl') return false;
    pendingThread = data.thread_id;
    pendingMode = data.mode || 'standalone';
    pendingDomain = data.domain || 'sre';
    const context = {
      service: data.service || 'checkout-service',
      severity: data.severity || 'P1',
      error_summary: data.error_summary || data.classification || '',
    };
    pendingChangeRun = { data, context };
    setPendingBadge(true);
    populateAutomation(data, context);
    updateContextPanel();
    switchSection('simulation', 'auto-change');
    return true;
  } catch (_) {
    return false;
  }
}

const CAPTURE_SCENES = {
  'step-01b-runbook-ingestion': () => switchSection('ingestion', 'ing-pipeline'),
  'step-01-ingestion-observability': () => switchSection('observability', 'obs-alert'),
  'step-02-agent-orchestration': () => {
    switchSection('operations', 'ops-pipeline');
    setAgentMode('multi');
    const data = {
      thread_id: 'mock7821',
      mode: 'multi',
      route: 'full_pipeline',
      classification: 'Service Degradation',
      runbook_id: 'checkout-redis-pool',
      recommendation: 'Increase REDIS_MAX_CONNECTIONS 50 → 150',
      status: 'awaiting_hitl',
      worker_trace: ['supervisor:full_pipeline', 'triage_worker', 'runbook_worker', 'logs_worker', 'metrics_worker', 'remediation_worker'],
      delegation_events: MULTI_DELEGATION_PREVIEW,
    };
    buildOrchestrationGraph();
    show($('orchestration-theater'));
    renderOrchestrationFromResult(data);
    updatePipeline(data, 6);
    $('pipeline-status-text').textContent = 'Step 7 of 8 — Waiting for human approval';
    show($('pipeline-running-pill'));
    $('pipeline-timer').textContent = '00:01:42';
    ['ingestion', 'triage', 'investigation'].forEach((id) => setFlowNodeState(id, 'done'));
    setFlowNodeState('hitl', 'waiting');
    setFlowNodeState('remediation', 'pending');
    setPipelineLiveMode(true);
  },
  'step-03-langfuse-trace': () => switchSection('evaluation', 'eval-trace'),
  'step-04-mlflow-evals': () => switchSection('evaluation', 'eval-gate'),
  'step-05-hitl-opa-guardrails': () => {
    const data = {
      thread_id: 'mock7821',
      classification: 'Service Degradation',
      runbook_id: 'checkout-redis-pool',
      recommendation: 'Increase REDIS_MAX_CONNECTIONS from 50 to 150 and rolling restart checkout-service.',
      status: 'awaiting_hitl',
    };
    const ctx = { service: 'checkout-service', severity: 'P1' };
    populateAutomation(data, ctx);
    pendingThread = data.thread_id;
    pendingChangeRun = { data, context: ctx };
    setPendingBadge(true);
    updateContextPanel();
    switchSection('simulation', 'auto-change');
  },
  'step-06-ticket-action': () => {
    renderTicketDetail({
      ticket_id: 'OPS-7821',
      service: 'checkout-service',
      severity: 'P1',
      status: 'open',
      runbook_id: 'checkout-redis-pool',
      summary: 'Increase Redis pool + rolling restart after HITL approval',
      approved_by: 'operator@agentops.local',
      created_at: new Date().toISOString(),
    });
    switchSection('actions', 'act-detail');
  },
};

function navigateLearningScene(sceneKey) {
  const fn = CAPTURE_SCENES[sceneKey];
  if (fn) {
    fn();
    showToast('info', 'Guided tour', 'Opened the live platform view for this step');
  }
}

window.navigateLearningScene = navigateLearningScene;
window.switchSection = switchSection;
window.showToast = showToast;

async function runCaptureScene(key) {
  setUserDisplay({ name: 'Alex Kim', role: 'operator', email: 'alex@agentops.local' });
  hide($('login-screen'));
  show($('app-screen'));
  await bootApp();
  const fn = CAPTURE_SCENES[key];
  if (fn) fn();
  updateQuickStats();
  document.body.dataset.captureReady = '1';
  document.title = `CAPTURE_READY:${key}`;
}

async function bootApp() {
  try {
    initMacNav();
    initArchDesignSwitcher();
    initNotifications();
    initUserMenu();
    initAdminPanel();
    initPipelineFlow();
    initPipelineUI();
    initToolTiles();
    bindActionRipples();
    await loadDashboardStats();
    window.addEventListener('resize', updateTabIndicator);
    await loadLinks();
    initToolTiles();
    syncEvalToolLinks();
    applyArchDesignContext();
    await loadScenarios();
    const deepLinked = await loadPendingFromUrl();
    if (!deepLinked) switchSection('operations', 'ops-incident');
    else updateContextPanelForSection(currentSection);
    updateQuickStats();
    updateContextPanel();

    await refreshCurrentUser();
    await loadAgentModes();
    setAgentMode(currentMode);
    if (currentUser?.theme_pref && typeof window.applyTheme === 'function') {
      window.applyTheme(currentUser.theme_pref);
    }

    $('global-search')?.addEventListener('focus', () => $('search-shell')?.classList.add('focused'));
    $('global-search')?.addEventListener('blur', () => $('search-shell')?.classList.remove('focused'));
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        $('global-search')?.focus();
      }
    });
  } catch (err) {
    console.error('bootApp failed', err);
  } finally {
    document.body.dataset.boot = '1';
  }
}

$('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  $('login-error').textContent = '';
  try {
    const data = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: $('email').value, password: $('password').value }),
    });
    token = data.access_token;
    localStorage.setItem('aiops_token', token);
    setUserDisplay({ name: data.name, role: data.role, email: $('email').value.trim().toLowerCase() });
    hide($('login-screen'));
    show($('app-screen'));
    await bootApp();
  } catch (err) {
    $('login-error').textContent = err.message;
  }
});

document.querySelectorAll('.nav-item[data-section]').forEach((btn) => {
  btn.addEventListener('click', () => switchSection(btn.dataset.section));
});

$('logout-btn').addEventListener('click', logout);

async function loadScenarios() {
  try {
    const data = IS_CAPTURE
      ? await fetch('/static/scenarios.json').then((r) => r.json())
      : await api('/api/agents/scenarios');
    scenarios = (data.scenarios || []).filter((s) => s.domain === currentDomain);
  } catch (_) {
    try {
      const data = await fetch('/static/scenarios.json').then((r) => r.json());
      scenarios = (data.scenarios || []).filter((s) => s.domain === currentDomain);
    } catch (err) {
      scenarios = [];
    }
  }
  const sel = $('scenario');
  sel.innerHTML = '';
  scenarios.forEach((s, i) => {
    const opt = document.createElement('option');
    opt.value = String(i);
    opt.textContent = s.label;
    sel.appendChild(opt);
  });
  sel.onchange = () => applyScenario(sel.value);
  populateServiceSelect();
  if (scenarios.length) applyScenario('0');
}

function populateServiceSelect() {
  const sel = $('service');
  if (!sel) return;
  const current = sel.value;
  sel.innerHTML = '';
  const services = [...new Set(scenarios.map((s) => s.payload?.service).filter(Boolean))];
  services.forEach((s) => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s;
    sel.appendChild(opt);
  });
  if (current && services.includes(current)) sel.value = current;
  else if (services.length) sel.value = services[0];
}

function applyScenario(index) {
  activeScenarioIndex = Number(index) || 0;
  const scenario = getActiveScenario();
  const p = scenario?.payload;
  if (!p) return;
  $('service').value = p.service;
  $('severity').value = p.severity;
  $('error_summary').value = p.error_summary;
  $('log_snippet').textContent = p.log_snippet || '';
  $('severity-badge').textContent = `${p.severity} · SEVERE`;
  renderScenarioOverview(scenario);
  renderLogPreview(p.log_snippet, 'cr-log-preview');
}

function loadModes() {
  populateServiceSelect();
  void loadAgentModes();
}

$('severity').addEventListener('change', () => {
  $('severity-badge').textContent = `${$('severity').value} · SEVERE`;
});

$('agent-mode-select')?.addEventListener('change', (e) => {
  setAgentMode(e.target.value);
  showToast('info', 'Agent mode', `Pipeline will run as ${currentMode}`);
});

$('service').addEventListener('change', () => {
  const svc = $('service').value;
  const idx = scenarios.findIndex((s) => s.payload?.service === svc);
  if (idx >= 0 && idx !== activeScenarioIndex) {
    $('scenario').value = String(idx);
    applyScenario(String(idx));
  }
});

$('alert-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  currentMode = $('agent-mode-select')?.value || currentMode;
  setAgentMode(currentMode);
  hide($('hitl-panel'));
  initPipelineUI();
  resetPipelineFlow();
  startTimer();
  show($('pipeline-running-pill'));
  $('pipeline-status-text').textContent = 'AI agent is investigating…';
  updateQuickStats();

  const submitBtn = $('run-pipeline-btn');
  setButtonLoading(submitBtn, true);
  animatePipelineRun().then(() => completeRunButtonState(true));

  const formContext = {
    service: $('service').value,
    severity: $('severity').value,
    error_summary: $('error_summary').value,
    log_snippet: getLogSnippet(),
    scenario_runbook_id: getActiveScenario()?.runbook_id,
    scenario_label: getActiveScenario()?.label,
  };

  try {
    const data = await api('/api/agents/invoke', {
      method: 'POST',
      body: JSON.stringify({
        domain: currentDomain,
        mode: currentMode,
        ...formContext,
        log_snippet: getLogSnippet(),
      }),
    });
    renderResult(data);
    loadLangfuseDashboard();
    if (data.status === 'awaiting_hitl') {
      pendingThread = data.thread_id;
      pendingMode = data.mode;
      pendingDomain = data.domain;
      pendingChangeRun = { data, context: formContext };
      setPendingBadge(true);
      show($('hitl-panel'));
      show($('ctx-hitl-card'));
      $('hitl-text').textContent = data.recommendation || 'Sensitive action requires approval.';
      populateAutomation(data, formContext);
      updateContextPanel();
      switchSection('simulation', 'auto-change');
      showToast('warning', 'HITL required', 'Human approval needed before remediation');
    } else {
      showToast('success', 'Pipeline completed', 'Agent run finished successfully');
      completeRunButtonState(false);
    }
  } catch (err) {
    hide($('pipeline-running-pill'));
    stopTimer();
    setPipelineLiveMode(false);
    completeRunButtonState(false);
    pipelineAnimToken++;
    resetPipelineFlow();
    $('pipeline-status-text').textContent = `Error: ${err.message}`;
    showToast('error', 'Pipeline failed', err.message);
    updateQuickStats();
  } finally {
    setButtonLoading(submitBtn, false);
  }
});

$('open-automation-btn').addEventListener('click', () => switchSection('simulation', 'auto-change'));
$('link-guardrails-console')?.addEventListener('click', () => switchSection('guardrails', 'grd-overview'));
$('opspilot-view-opa')?.addEventListener('click', () => switchSection('guardrails', 'grd-editor'));
$('ctx-view-opa')?.addEventListener('click', () => switchSection('guardrails', 'grd-editor'));
document.querySelectorAll('.grd-filter').forEach((btn) => {
  btn.addEventListener('click', () => loadGrdAudit(btn.dataset.verdict || ''));
});
$('grd-audit-refresh')?.addEventListener('click', () => loadGrdAudit());
document.querySelectorAll('.hitl-hist-filter').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.hitl-hist-filter').forEach((b) => b.classList.toggle('active', b === btn));
    loadHitlHistory(btn.dataset.decision || '');
  });
});
$('hitl-history-refresh')?.addEventListener('click', () => loadHitlHistory());
$('eval-trace-refresh')?.addEventListener('click', () => {
  if (lastThreadId) loadEvalTrace(lastThreadId);
  else showToast('info', 'No trace', 'Run the pipeline first to capture a trace');
});
$('eval-analytics-refresh')?.addEventListener('click', () => loadLangfuseDashboard());
$('eval-gate-refresh')?.addEventListener('click', () => loadEvalDashboard());
$('eval-gate-run')?.addEventListener('click', () => runEvalSuite());
$('eval-how-toggle')?.addEventListener('click', () => {
  const body = $('eval-how-body');
  const btn = $('eval-how-toggle');
  if (!body || !btn) return;
  const collapsed = body.classList.toggle('is-collapsed');
  btn.textContent = collapsed ? 'Expand' : 'Collapse';
  btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
});
$('obs-sim-refresh')?.addEventListener('click', () => loadAlertFlowCatalog());
$('obs-sim-preview')?.addEventListener('click', () => previewAlertFlow(false));
$('obs-sim-fire')?.addEventListener('click', () => previewAlertFlow(true));
$('obs-custom-use')?.addEventListener('click', () => useCustomAlertFromForm());
$('obs-hitl-open-sim')?.addEventListener('click', () => switchSection('simulation', 'auto-change'));
$('obs-hitl-open-trace')?.addEventListener('click', () => switchSection('evaluation', 'eval-trace'));
document.querySelectorAll('.alert-phase-tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.alert-phase-tab').forEach((t) => t.classList.toggle('is-active', t === tab));
    alertPhaseFilter = tab.dataset.phase || 'all';
    if (alertFlowSimData?.steps) {
      populateAlertStepSelect(alertFlowSimData.steps);
      buildJourneyTrack(alertFlowSimData.steps);
      if (alertFlowSelectedStepId) {
        const visible = getFilteredAlertSteps(alertFlowSimData.steps).some((s) => s.id === alertFlowSelectedStepId);
        if (visible) selectAlertFlowStep(alertFlowSelectedStepId);
        else if (getFilteredAlertSteps(alertFlowSimData.steps)[0]) {
          selectAlertFlowStep(getFilteredAlertSteps(alertFlowSimData.steps)[0].id);
        }
      }
    }
  });
});
$('grd-test-run')?.addEventListener('click', () => runGrdSandboxTest());
$('grd-policy-test')?.addEventListener('click', () => runGrdSandboxTest());
$('grd-policy-save')?.addEventListener('click', () => {
  setButtonLoading($('grd-policy-save'), true);
  saveGrdPolicy().finally(() => setButtonLoading($('grd-policy-save'), false));
});
$('grd-policy-reset')?.addEventListener('click', () => {
  if ($('grd-rego-editor')) $('grd-rego-editor').value = grdPolicyDraft;
  showToast('info', 'Reset', 'Restored last loaded policy text.');
});
$('ctx-run-pipeline').addEventListener('click', () => {
  switchSection('operations', 'ops-incident');
  $('alert-form').requestSubmit();
});
$('ctx-approve').addEventListener('click', () => {
  setButtonLoading($('ctx-approve'), true);
  submitApproval(true).finally(() => setButtonLoading($('ctx-approve'), false));
});
$('ctx-reject').addEventListener('click', () => submitApproval(false));
$('opspilot-approve').addEventListener('click', () => {
  setButtonLoading($('opspilot-approve'), true);
  submitApproval(true).finally(() => setButtonLoading($('opspilot-approve'), false));
});
$('opspilot-deny').addEventListener('click', () => submitApproval(false));

$('qa-create').addEventListener('click', (e) => {
  createRipple(e.currentTarget, e);
  e.currentTarget.style.transform = 'scale(1.05)';
  setTimeout(() => { e.currentTarget.style.transform = ''; switchSection('operations', 'ops-incident'); }, 200);
  showToast('info', 'Create Pipeline', 'Configure incident details to start a new run');
});
$('qa-add-agent').addEventListener('click', (e) => {
  createRipple(e.currentTarget, e);
  showToast('success', 'Agent added', 'Investigation agent joined the pool');
  void loadDashboardStats();
});
$('qa-import').addEventListener('click', async (e) => {
  const btn = e.currentTarget;
  createRipple(btn, e);
  const orig = btn.textContent;
  btn.textContent = 'Importing…';
  btn.disabled = true;
  await new Promise((r) => setTimeout(r, 900));
  btn.textContent = orig;
  btn.disabled = false;
  showToast('success', 'Configuration imported', 'Settings synced successfully');
});
$('qa-alerts').addEventListener('click', (e) => {
  createRipple(e.currentTarget, e);
  switchSection('observability', 'obs-simulator');
  showToast('info', 'Alert Flow', 'Generate and trace alert ingestion');
});

$('btn-refresh-tickets').addEventListener('click', (e) => {
  const btn = e.currentTarget;
  btn.classList.add('is-loading');
  loadTickets().finally(() => {
    btn.classList.remove('is-loading');
    document.querySelectorAll('.stat-card').forEach((c) => c.classList.add('stat-pop'));
    setTimeout(() => document.querySelectorAll('.stat-card').forEach((c) => c.classList.remove('stat-pop')), 600);
    showToast('info', 'Refreshed', 'Ticket data updated');
  });
});

$('copy-result').addEventListener('click', () => navigator.clipboard.writeText($('result').textContent));

$('btn-reindex').addEventListener('click', async (e) => {
  setIngestJobMsg('Starting reindex…', 'running');
  setIngestJobLive(true, 'Starting reindex…', 'Preparing incremental runbook ingestion');
  setButtonLoading($('btn-reindex'), true);
  createRipple(e.currentTarget, e);
  try {
    const job = await api('/api/ingest/reindex', { method: 'POST', body: JSON.stringify({ mode: 'incremental', sync_drive: true }) });
    renderIngestJob(job);
    showToast('info', 'Reindex started', `Job ${job.id.slice(0, 8)}… queued`);
    await pollIngestJob(job.id);
  } catch (err) {
    setIngestJobLive(false);
    setIngestJobMsg(err.message, 'error');
    showToast('error', 'Reindex failed', err.message);
  } finally {
    setButtonLoading($('btn-reindex'), false);
  }
});

$('btn-sync-drive').addEventListener('click', async () => {
  setIngestJobMsg('Syncing Drive…', 'running');
  setIngestJobLive(true, 'Syncing Google Drive…', `Downloading .md runbooks and embedding into ${archStack('vector', 'Chroma')}`);
  setButtonLoading($('btn-sync-drive'), true);
  try {
    const job = await api('/api/ingest/sync-drive', { method: 'POST' });
    renderIngestJob(job);
    showToast('info', 'Drive sync started', `Job ${job.id.slice(0, 8)}… queued`);
    await pollIngestJob(job.id);
  } catch (err) {
    setIngestJobLive(false);
    setIngestJobMsg(err.message, 'error');
    showToast('error', 'Drive sync failed', err.message);
  } finally {
    setButtonLoading($('btn-sync-drive'), false);
  }
});

$('btn-refresh-tickets').addEventListener('click', loadTickets);
$('gov-refresh')?.addEventListener('click', () => loadGovernanceSection('gov-overview'));
$('gov-pipelines-refresh')?.addEventListener('click', () => loadGovernanceSection('gov-pipelines'));
$('gov-promo-form')?.addEventListener('submit', submitGovernancePromotion);
$('btn-refresh-index')?.addEventListener('click', loadIngestIndex);
$('btn-go-ingest-actions')?.addEventListener('click', () => switchSection('ingestion', 'ing-status'));
$('chroma-query-form')?.addEventListener('submit', runChromaQuery);
$('chroma-inspector-close')?.addEventListener('click', () => {
  $('chroma-inspector')?.classList.add('hidden');
  document.querySelectorAll('.chroma-chunk-row.selected, .chroma-hit-row.selected').forEach((el) => el.classList.remove('selected'));
});
$('btn-ticket-json').addEventListener('click', () => $('ticket-json-box').classList.toggle('hidden'));
$('btn-ticket-copy').addEventListener('click', () => {
  if (selectedTicket) navigator.clipboard.writeText(JSON.stringify(selectedTicket, null, 2));
});

const captureKey = new URLSearchParams(window.location.search).get('capture');
if (captureKey) {
  token = 'capture-mode';
  runCaptureScene(captureKey);
} else if (token) {
  api('/api/auth/me').then(async (u) => {
    setUserDisplay(u);
    hide($('login-screen'));
    show($('app-screen'));
    await bootApp();
  }).catch(logout);
}
