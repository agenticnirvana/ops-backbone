/** Contextual learning tips — learn · try · practice per section/tab */

const SECTION_LEARNING_TIPS = {
  operations: {
    default: {
      icon: '⚡',
      title: 'Operations — agent triage',
      learn: 'Three LangGraph modes: standalone pipeline, multi-agent supervisor + workers, or MCP mode where tools call a hosted HTTP MCP server (FastAPI + Basic Auth).',
      try: 'Select checkout Redis scenario → choose Multi-agent or MCP mode → Run Pipeline.',
      practice: 'Compare delegation feed (multi) vs MCP tool call cards (mcp). Admin → Agent Registry lists all registered agents in PostgreSQL.',
      action: { section: 'operations', tab: 'ops-incident', label: 'Run capstone incident' },
    },
    'ops-pipeline': {
      icon: '🔄',
      title: 'Agent Run — live graph',
      learn: 'Multi-agent mode shows a hierarchical tree: supervisor at root, workers nested down the spine. MCP mode previews HTTP tool calls inline.',
      try: 'Switch Agent mode → Run Pipeline. Open Multi-Agent Flow or MCP Server tabs for full hierarchy views.',
      practice: 'Compare tree node states with delegation_events in Response JSON.',
      action: { section: 'operations', tab: 'ops-multi', label: 'Open multi-agent tree' },
    },
    'ops-multi': {
      icon: '🌳',
      title: 'Multi-agent hierarchy',
      learn: 'LangGraph supervisor topology as a tree: each worker is a child node. HITL gate branches before incident/ticket creation.',
      try: 'Run pipeline in Multi-agent mode first — this tab replays the full delegation tree and log.',
      practice: 'Trace supervisor → triage → runbook → logs → metrics → remediation → HITL → incident in order.',
      action: { section: 'operations', tab: 'ops-incident', label: 'Run multi-agent pipeline' },
    },
    'ops-mcp': {
      icon: '🔌',
      title: 'MCP server architecture',
      learn: 'Hosted FastAPI MCP server (OSS) exposes tools over HTTP with Basic Auth. Agent calls POST /tools/{name} instead of in-process imports.',
      try: 'Run pipeline in MCP mode — tool nodes highlight on the architecture tree when invoked.',
      practice: 'For hands-on testing, open MCP Playground in the left nav (Inspector).',
      action: { section: 'mcp', tab: 'mcp-playground', label: 'Open MCP Playground' },
    },
  },
  simulation: {
    default: {
      icon: '👤',
      title: 'Simulation — HITL gate',
      learn: 'Destructive recommendations (restart, kill, rollback) pause at hitl_gate. {policy} must allow the action; then an operator approves or rejects.',
      try: 'Fire an alert from Observability → Alert Flow, then open HITL Review here.',
      practice: 'Add a reason/comment before Approve. Check History for the audit record with who decided and why.',
      action: { section: 'observability', tab: 'obs-simulator', label: 'Fire alert & reach HITL' },
    },
    'auto-history': {
      icon: '📜',
      title: 'HITL decision history',
      learn: 'Every approve/reject is persisted with operator email, {policy} verdict, optional comment, and ticket linkage.',
      try: 'Filter Approved vs Rejected after completing a HITL cycle.',
      practice: 'Use this as your compliance trail — who approved destructive prod changes and when.',
      action: { section: 'simulation', tab: 'auto-change', label: 'Back to HITL Review' },
    },
    'auto-opa': {
      icon: '🛡️',
      title: '{policy} policy preview',
      learn: 'Same rules as Guardrails: non-destructive always allowed; destructive allowed only on P1; P2/P3 destructive denied.',
      try: 'Change severity to P3 on Operations and re-run — {policy} should deny destructive remediation.',
      practice: 'Compare this panel with Guardrails → Audit Log after each evaluation.',
      action: { section: 'guardrails', tab: 'grd-audit', label: 'Open {policy} audit log' },
    },
  },
  guardrails: {
    default: {
      icon: '🛡️',
      title: 'Guardrails — {policy} policy ops',
      learn: '{policy} evaluates agent recommendations against live policy before HITL and execute. Deny stops the pipeline. {safety} adds a second safety layer.',
      try: 'Overview shows rule flow. Audit Log lists every evaluation from HITL preview and sandbox tests.',
      practice: 'Edit policy in Policy Editor → save + reload → re-test in sandbox.',
      action: { section: 'guardrails', tab: 'grd-editor', label: 'Open policy editor' },
    },
  },
  ingestion: {
    default: {
      icon: '📚',
      title: 'Ingestion — runbook → vectors',
      learn: 'Markdown runbooks are chunked, embedded (384-d), and stored in {vector}. The agent searches this index at retrieve_runbook — stale index = wrong runbook.',
      try: 'Open the native {vector} UI ({vectorUrl}) in a second tab, then query "redis pool checkout" here.',
      practice: '{ingestTab}: query "redis pool checkout" and confirm checkout-redis-pool chunks appear.',
      action: { section: 'ingestion', tab: 'ing-jobs', label: 'Open {ingestTab}' },
    },
  },
  observability: {
    default: {
      icon: '📡',
      title: 'Observability — signal chain',
      learn: 'Metrics exporter → {metrics} → alert webhook → agent. Logs flow through {logs}. {dashboards} visualizes the same signals.',
      try: 'Alert Flow tab: Walkthrough animates all 12 steps; Fire invokes the real agent.',
      practice: 'Click completed pipeline nodes to inspect {vector}, {policy}, and HITL payloads in the breakdown panel.',
      action: { section: 'observability', tab: 'obs-simulator', label: 'Start Alert Flow demo' },
    },
    'obs-simulator': {
      icon: '🔥',
      title: 'Alert Flow simulator',
      learn: 'End-to-end demo: signals → agent → {vector} RAG → {policy} → HITL. Custom alerts use the same webhook shape as production.',
      try: 'Walkthrough first (no agent fire), then Fire & Request Approval for live HITL.',
      practice: 'Use phase tabs (Signals / Agent / {policy} / HITL) to focus the pipeline and dropdown.',
      action: { section: 'simulation', tab: 'auto-change', label: 'Open HITL after fire' },
    },
  },
  evaluation: {
    default: {
      icon: '📊',
      title: 'Evaluation — trust but verify',
      learn: '{llmops} is the only eval tool for this design: traces, experiments, and LLM-as-judge. Run Eval Suite, then open {llmops} — do not look for the other vendors here.',
      try: 'Run a pipeline in Operations, then open Agent Analytics and {llmops} Trace.',
      practice: 'Eval & Scores runs 8 golden cases on demand — the same suite is the required GitHub check eval-gate / golden-set.',
      action: { section: 'evaluation', tab: 'eval-gate', label: 'Run eval suite' },
    },
    'eval-gate': {
      icon: '✅',
      title: 'Eval gate — how it works',
      learn: 'Golden alerts invoke the live graph. Each case is scored on RAG recall, groundedness, correctness, HITL, latency, and an LLM-as-judge groundedness score. Results publish only to {llmops}.',
      try: 'Click Run Eval Suite — takes ~30–60s. Watch cases populate and gate PASS/FAIL banner.',
      practice: 'Fail a case on purpose: stop runbook-ingestion, re-run eval, see RAG recall drop. Reindex and pass again.',
      action: { section: 'evaluation', tab: 'eval-gate', label: 'Run eval suite', actionFn: 'runEval' },
      howItWorks: true,
    },
    'eval-analytics': {
      icon: '📈',
      title: '{llmops} agent analytics',
      learn: 'Aggregated KPIs from {llmops}: trace counts, latency percentiles, LLM call volume, and custom scores pushed after pipeline runs.',
      try: 'Run Operations pipeline first so traces exist, then Refresh here.',
      practice: 'Open {llmops} → Traces → filter session_id from your last run.',
      action: { section: 'operations', tab: 'ops-pipeline', label: 'Generate traces first' },
    },
    'eval-trace': {
      icon: '🔍',
      title: '{llmops} trace viewer',
      learn: 'Langfuse v3 (the GitHub product): Tracing, Playground, Prompts, Datasets, Evaluation / LLM-as-judge. Observation types: SPAN, GENERATION, EVENT.',
      try: 'Open Langfuse :3000. Tracing after a pipeline run. Playground + Evaluation after Settings → LLM connection to Ollama llama3.2.',
      practice: 'Compare span order with Operations → Agent Run animation.',
      action: { section: 'operations', tab: 'ops-incident', label: 'Run pipeline' },
    },
  },
  governance: {
    default: {
      icon: '🏛️',
      title: 'Governance — CI, evals, promotions',
      learn: 'Enterprise change control: pre-commit, required GitHub checks (lint / unit / secret-scan / eval-gate), CODEOWNERS, and four-eyes promotions into staging/production.',
      try: 'Open Pipelines for seeded CI rows, then Promotions — request staging as operator, approve as admin.',
      practice: 'GitHub org/repo stay YOUR_GITHUB_ORG / YOUR_GITHUB_REPO until wired. Controls tab lists evidence files.',
      action: { section: 'governance', tab: 'gov-github', label: 'GitHub setup placeholders' },
    },
    'gov-pipelines': {
      icon: '🚦',
      title: 'CI / eval pipelines',
      learn: 'ci.yml = lint, unit, gitleaks. eval-gate.yml = golden_alerts.json with score thresholds. Running Eval Suite here also records a pipeline row.',
      try: 'Evaluation → Run Eval Suite, then come back — a new eval-gate row should appear.',
      practice: 'Required checks on main are listed in deploy/github/config.yml.',
      action: { section: 'evaluation', tab: 'eval-gate', label: 'Run eval suite' },
    },
    'gov-promotions': {
      icon: '✅',
      title: 'Four-eyes promotions',
      learn: 'Requester cannot approve their own change. Production also requires an admin. This mirrors GitHub Environment reviewers on promote.yml.',
      try: 'Request production as operator@, then log in as admin@ to approve.',
      practice: 'Reject a promotion and read the audit log on Controls.',
      action: { section: 'governance', tab: 'gov-controls', label: 'Open audit log' },
    },
    'gov-github': {
      icon: '🐙',
      title: 'Wire GitHub later',
      learn: 'Workflows, CODEOWNERS, and pre-commit already live in the course tree. Copy .github/ to the real repo root when you share org/repo.',
      try: 'Note the secrets list — GOVERNANCE_WEBHOOK_URL points at the governance service on :8093.',
      practice: 'After wiring, set GITHUB_ORG / GITHUB_REPO in deploy/.env and restart gateway.',
      action: { section: 'governance', tab: 'gov-overview', label: 'Back to posture' },
    },
  },
  actions: {
    default: {
      icon: '🎫',
      title: 'Actions — remediation records',
      learn: 'After HITL approve, ticket-api writes OPS-xxxxxxxx to PostgreSQL — audit trail of who approved what remediation.',
      try: 'Complete Observability → Fire → Simulation Approve, then Refresh tickets.',
      practice: 'Click a ticket row to see full JSON record including runbook_id and approver.',
      action: { section: 'simulation', tab: 'auto-change', label: 'Complete HITL first' },
    },
  },
  learning: {
    default: {
      icon: '📓',
      title: 'The AgentOps notebook',
      learn: 'Open-book UI: chapters per phase, page-turn, bookmarks, margin notes. Chapter 1 starts with vector databases — what / why / why not SQL / viz / OSS vs cloud.',
      try: '← → or click page edges. 🔖 to dog-ear. First real lesson: What is a vector DB?',
      practice: 'Toggle Vector vs Keyword on the nearest-neighbor sketch, then open {ingestTab}.',
      action: { section: 'learning', tab: 'learn-notebook', label: 'Open notebook' },
    },
    'learn-notebook': {
      icon: '📖',
      title: 'Page-turn reader',
      learn: 'Pick a reading skin: Hardcover (two-page book), Kindle (e-ink Paperwhite), Editorial, or Stories if you hate walls of text. Architecture maps sit in every chapter.',
      try: 'Toolbar → Kindle. Tap the page edge — you should see the e-ink flash, then Loc X of Y at the bottom.',
      practice: 'Stories mode: swipe cards. Notebook mode: doodles + margin notes.',
      action: { section: 'ingestion', tab: 'ing-jobs', label: '{ingestTab}' },
    },
    'learn-bookmarks': {
      icon: '🔖',
      title: 'Dog-ears',
      learn: 'Bookmarks persist in this browser. Jump back to any page.',
      try: 'If empty, bookmark the vector viz page first.',
      practice: 'Keep one bookmark per chapter.',
      action: { section: 'learning', tab: 'learn-notebook', label: 'Back to notebook' },
    },
    'learn-notes': {
      icon: '✏️',
      title: 'Margin notes',
      learn: 'Scribbles from the bottom of each page land here.',
      try: 'Write why pgvector vs {vector} for your team.',
      practice: 'Use notes as a personal glossary.',
      action: { section: 'learning', tab: 'learn-notebook', label: 'Keep reading' },
    },
    'learn-highlights': {
      icon: '🟨',
      title: 'Highlights',
      learn: 'Select a sentence on any page, then pick yellow / pink / mint. Click a mark to undo.',
      try: 'Highlight the tl;dr on “What is a vector database?”',
      practice: 'Collect three quotes you’d teach someone else.',
      action: { section: 'learning', tab: 'learn-notebook', label: 'Back to notebook' },
    },
    'learn-designs': {
      icon: '🗺️',
      title: 'Pick a stack',
      learn: 'Three reference designs, one product. D2 is live here (Weaviate + Elasticsearch + VictoriaMetrics + Phoenix). D1/D3 are compare mode until those compose profiles are up.',
      try: 'Tap Design 2 in the header, then come back here — the pick cards highlight.',
      practice: 'Say out loud which stack your org would actually run.',
      action: { section: 'learning', tab: 'learn-notebook', label: 'Architecture map' },
    },
  },
  mcp: {
    default: {
      icon: '🔌',
      title: 'MCP & Skills',
      learn: 'Three tabs: MCP Inspector (live tools), Skills Catalog (agentregistry SKILL.md + scripts), MCP vs Skills (decision guide).',
      try: 'Skills Catalog → severity-classifier → Run script with capstone alert text.',
      practice: 'Compare skill script output with MCP get_metrics on the same incident.',
      action: { section: 'mcp', tab: 'mcp-vs-skills', label: 'Open decision guide' },
    },
    'mcp-playground': {
      icon: '🧪',
      title: 'MCP Inspector',
      learn: 'Live callable tools over HTTP — side effects possible. Use for {logs}, {metrics}, {vector}, tickets at runtime.',
      try: 'Connect Ops MCP Server → invoke retrieve_runbooks for checkout-service.',
      practice: 'Compare with Skills tab — MCP fetches live data; skills run offline eval scripts.',
      action: { section: 'operations', tab: 'ops-mcp', label: 'View MCP architecture' },
    },
    'mcp-skills': {
      icon: '📚',
      title: 'Skills catalog',
      learn: 'Skills = SKILL.md + optional scripts in agentregistry. No live network — knowledge, checklists, eval helpers.',
      try: 'Runbook Recall Check → verify_runbook_id.py with checkout-service checkout-redis-pool.',
      practice: 'Read SKILL.md “Skill vs MCP” table in each skill — same pattern as Learning → MCP vs Skills.',
      action: { section: 'learning', tab: 'learn-notebook', label: 'Notebook → Ch.1' },
    },
    'mcp-vs-skills': {
      icon: '⚖️',
      title: 'When to use MCP vs Skills',
      learn: 'MCP when the agent must act on live systems. Skills when teaching procedures, CI evals, or HITL checklists.',
      try: 'Use the decision matrix — then open the matching tab (Inspector or Catalog).',
      practice: 'Map each LangGraph worker to either MCP tools or skills it would consult first.',
      action: { section: 'mcp', tab: 'mcp-skills', label: 'Browse skills' },
    },
  },
  admin: {
    default: {
      icon: '🗂️',
      title: 'Admin — platform control',
      learn: 'Agent Registry uses OSS agentregistry (:12121). Skills live in the same registry under kind Skill.',
      try: 'Agent Registry → refresh · Open agentregistry UI for full catalog.',
      practice: 'Cross-reference registry slugs with worker_trace from a multi-agent run.',
      action: { section: 'mcp', tab: 'mcp-skills', label: 'View skills' },
    },
    'adm-agents': {
      icon: '🤖',
      title: 'Agent registry',
      learn: 'agentregistry stores Agents + MCPServers. Design 1 labels map kind, mode, tools. Skills are separate resources.',
      try: 'Find sre-supervisor and mcp-ops-server — orchestrator vs MCP host.',
      practice: 'Register a new worker here; bulk updates via arctl apply -f design1-catalog.yaml.',
      action: { section: 'mcp', tab: 'mcp-vs-skills', label: 'MCP vs Skills guide' },
    },
  },
};

function getLearningTip(section, tab) {
  const sec = SECTION_LEARNING_TIPS[section];
  if (!sec) return null;
  return sec[tab] || sec.default || null;
}

function renderLearningTip(section, tab) {
  const el = document.getElementById('section-learning-tip');
  if (!el) return;
  const tip = getLearningTip(section, tab);
  if (!tip) {
    el.classList.add('hidden');
    el.innerHTML = '';
    return;
  }
  el.classList.remove('hidden');
  const fill = (s) => (typeof archFill === 'function' ? archFill(s) : s);
  const actionBtn = tip.action
    ? `<button type="button" class="btn-primary btn-glossy btn-sm learning-tip-action" data-tip-action="1"><span class="btn-shine"></span>${escapeHtml(fill(tip.action.label))}</button>`
    : '';
  el.innerHTML = `
    <div class="learning-tip-inner glossy-card">
      <div class="learning-tip-icon" aria-hidden="true">${tip.icon || '💡'}</div>
      <div class="learning-tip-body">
        <div class="learning-tip-head">
          <strong>${escapeHtml(fill(tip.title))}</strong>
          <button type="button" class="btn-ghost btn-sm learning-tip-dismiss" aria-label="Dismiss tip">Hide</button>
        </div>
        <dl class="learning-tip-list">
          <div><dt>Learn</dt><dd>${escapeHtml(fill(tip.learn))}</dd></div>
          <div><dt>Try</dt><dd>${escapeHtml(fill(tip.try))}</dd></div>
          <div><dt>Practice</dt><dd>${escapeHtml(fill(tip.practice))}</dd></div>
        </dl>
      </div>
      <div class="learning-tip-actions">${actionBtn}</div>
    </div>`;
  el.querySelector('.learning-tip-dismiss')?.addEventListener('click', () => {
    el.classList.add('hidden');
    try { sessionStorage.setItem(`tip-hidden-${section}-${tab}`, '1'); } catch (_) { /* ignore */ }
  });
  el.querySelector('[data-tip-action]')?.addEventListener('click', () => {
    if (tip.actionFn === 'runEval' && typeof runEvalSuite === 'function') {
      runEvalSuite();
      return;
    }
    if (tip.action && typeof switchSection === 'function') {
      switchSection(tip.action.section, tip.action.tab);
    }
  });
  try {
    if (sessionStorage.getItem(`tip-hidden-${section}-${tab}`) === '1') el.classList.add('hidden');
  } catch (_) { /* ignore */ }
}

window.renderLearningTip = renderLearningTip;
window.getLearningTip = getLearningTip;
