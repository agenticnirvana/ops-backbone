/** Design 1 — integrated learning guide (from DESIGN-1-COMPLETE-WALKTHROUGH.md) */

const LEARNING_PHASES = [
  { n: 1, name: 'Ingestion', question: 'What signals & knowledge does the agent see?', tools: '{metrics} · {logs} · {dashboards} · {vector} · runbook-ingestion', color: 'teal' },
  { n: 2, name: 'Orchestration', question: 'How does the agent reason and call tools?', tools: 'LangGraph · Platform UI · MCP · Ollama', color: 'indigo' },
  { n: 3, name: 'Evaluation', question: 'How do you trust it before/after deploy?', tools: '{evals}', color: 'violet' },
  { n: 4, name: 'Guardrails', question: 'What stops bad or unauthorized actions?', tools: '{policy} · HITL · {safety}', color: 'amber' },
  { n: 5, name: 'Action & CI/CD', question: 'What happens after a decision?', tools: 'PostgreSQL ticket-api · GitHub Actions', color: 'green' },
];

const LEARNING_STEPS = [
  {
    id: 'step-0',
    phase: 'Prep',
    title: 'Runbooks become searchable',
    subtitle: 'Before any alert fires — {vector} must have your procedures',
    happens: 'Git seed runbooks copy to /data/runbooks. Optional Google Drive sync. runbook-ingestion chunks + embeds markdown into {vector} (384-d vectors).',
    expect: 'Platform → Ingestion → Pipeline / Status / {ingestTab}. Open {vectorUrl} for the native {vector} UI alongside this console.',
    mind: 'Drive is the drop zone · ingestion is the factory · {vector} is the library the agent searches.',
    scene: 'step-01b-runbook-ingestion',
    section: ['ingestion', 'ing-pipeline'],
    img: '/static/learn/step-01b-runbook-ingestion.png',
    tryUi: 'Open Ingestion → {ingestTab}',
  },
  {
    id: 'step-1',
    phase: 'Phase 1',
    title: 'Alerts, logs & metrics land',
    subtitle: 'The senses of the agent — ears, eyes, pulse',
    happens: '{metrics} rule CheckoutHighErrorRate → alert webhook → agent. Logs land in {logs}. metrics-exporter scrapes into {metrics}.',
    expect: 'Observability tab shows firing P1 alert + log preview. Grafana :3001 shows checkout spike.',
    mind: 'Phase 1 feeds real signals — not hallucinated context.',
    scene: 'step-01-ingestion-observability',
    section: ['observability', 'obs-alert'],
    img: '/static/learn/step-01-ingestion-observability.png',
    tryUi: 'Open Observability → Alerts',
  },
  {
    id: 'step-2',
    phase: 'Phase 2',
    title: 'LangGraph agent triages',
    subtitle: 'Brain + hands — classify → RAG → logs → metrics → recommend',
    happens: 'Graph: classify → retrieve_runbook → query_logs → query_metrics → recommend → hitl_gate. Capstone retrieves checkout-redis-pool from {vector}.',
    expect: 'Operations → Agent Run — six pipeline steps animate. Runbook ID checkout-redis-pool appears.',
    mind: 'LangGraph is the brain; MCP/tools are the hands.',
    scene: 'step-02-agent-orchestration',
    section: ['operations', 'ops-pipeline'],
    img: '/static/learn/step-02-agent-orchestration.png',
    tryUi: 'Run capstone on Operations → Incident',
  },
  {
    id: 'step-3',
    phase: 'Phase 3',
    title: 'Evaluation & traces',
    subtitle: 'Quality department — prove grounding and repeatability',
    happens: '{llmops} records every graph span. Eval Suite scores golden alerts and publishes LLM-as-judge results into the same tool.',
    expect: 'Evaluation → Agent Analytics + {llmops} Trace. After Eval Suite, open {llmops} for datasets/experiments and llm-as-judge scores.',
    mind: 'Every node is observable before you trust automation in prod.',
    scene: 'step-03-langfuse-trace',
    section: ['evaluation', 'eval-analytics'],
    img: '/static/learn/step-03-langfuse-trace.png',
    tryUi: 'Open Evaluation → Agent Analytics',
  },
  {
    id: 'step-3b',
    phase: 'Phase 3',
    title: '{llmops} eval gate',
    subtitle: 'Golden alerts + LLM-as-judge in this design’s eval tool',
    happens: 'golden_alerts.json expected runbook IDs are checked, then an LLM-as-judge scores groundedness. Design 1 → Langfuse datasets. Design 2 → Phoenix. Design 3 → MLflow.',
    expect: 'Evaluation → Eval & Scores. Then open {llmops} — not the other vendors.',
    mind: 'Regression tests for RAG — not just unit tests.',
    scene: 'step-04-mlflow-evals',
    section: ['evaluation', 'eval-gate'],
    img: '/static/learn/step-04-mlflow-evals.png',
    tryUi: 'Open Evaluation → Eval Gate',
  },
  {
    id: 'step-4',
    phase: 'Phase 4',
    title: '{policy} + HITL guardrails',
    subtitle: 'The airbag — simulated remediation pauses until a human says yes',
    happens: 'FastAPI blocks bad payloads. {policy} checks destructive actions. LangGraph interrupt_before hitl_gate. Platform shows Approve/Deny.',
    expect: 'Simulation → HITL Review opens when status is awaiting_hitl.',
    mind: 'P1 + restart/scale language always pauses for operator approval.',
    scene: 'step-05-hitl-opa-guardrails',
    section: ['simulation', 'auto-change'],
    img: '/static/learn/step-05-hitl-opa-guardrails.png',
    tryUi: 'Open Simulation → HITL Review',
  },
  {
    id: 'step-5',
    phase: 'Phase 5',
    title: 'Ticket & audit trail',
    subtitle: 'Every approved action leaves a record',
    happens: 'After HITL approve → ticket-api writes OPS-xxxxxxxx to PostgreSQL. GitHub Actions runs lint, pytest, eval on push.',
    expect: 'Actions → Record shows remediation ticket. Toast after approve in live demo.',
    mind: 'Phase 5 is compliance — who approved what, when, and why.',
    scene: 'step-06-ticket-action',
    section: ['actions', 'act-detail'],
    img: '/static/learn/step-06-ticket-action.png',
    tryUi: 'Open Actions → Record',
  },
];

const LEARN_PORTS_COMMON = [
  ['8080', 'Platform UI (login + HITL)'],
  ['8081', 'Ops MCP Server — logs, metrics, tickets'],
  ['8082', 'Policy MCP Server — policy + HITL preview'],
  ['8083', 'Runbook RAG MCP — catalog + retrieval'],
  ['12121', 'agentregistry (OSS catalog UI + API)'],
  ['8002', 'Agent API'],
  ['8090', 'Alert webhook receiver'],
  ['8092', 'Runbook ingestion API'],
  ['5001', 'MLflow'],
  ['3001', 'Grafana'],
];

/** Deep-dive topics — OSS stack, auth, and how to extend each area */
const LEARNING_TOPICS = [
  {
    id: 'registry',
    title: 'Agent Registry',
    icon: '🗂️',
    oss: ['agentregistry (Apache 2.0)', 'arctl CLI', 'FastAPI gateway adapter'],
    summary: 'Catalog of orchestrators, workers, and MCP hosts — powered by OSS agentregistry.',
    blocks: [
      {
        h: 'OSS tools used',
        p: 'Design 1 uses <strong><a href="https://github.com/agentregistry-dev/agentregistry" target="_blank" rel="noopener">agentregistry</a></strong> (Apache 2.0) on <code>:12121</code> with its own PostgreSQL. Platform labels (<code>design1.io/*</code>) map kind, mode, tools, and risk onto agentregistry Agent and MCPServer resources. Gateway adapts <code>GET /v0/agents</code> + <code>/v0/mcpservers</code> for the Admin UI.',
      },
      {
        h: 'What gets stored',
        p: 'Each agentregistry resource: <code>metadata.name</code> (slug), <code>spec.title</code>, labels for <code>kind</code>, <code>mode</code>, <code>tools</code>, <code>risk-tier</code>, <code>owner</code>, <code>status</code>. Ten Design 1 agents seeded in namespace <code>design1</code> (supervisor, six workers, MCP host, MCP runner, standalone orchestrator).',
      },
      {
        h: 'How to add a new agent',
        ul: [
          '<strong>Admin UI (recommended):</strong> Admin → Agent Registry → “Register new agent” (applies to agentregistry via gateway).',
          '<strong>REST API:</strong> <code>POST /api/agents/registry</code> with admin JWT.',
          '<strong>agentregistry UI:</strong> <code>http://localhost:12121</code> — browse catalog, MCP servers, deployments.',
          '<strong>arctl CLI:</strong> <code>arctl apply -f deploy/config/agentregistry/design1-catalog.yaml</code> for bulk seed/updates.',
          '<strong>Code seed:</strong> <code>DEFAULT_AGENTS</code> in <code>platform/shared/agent_registry.py</code> — auto-applied on startup if missing.',
        ],
      },
      {
        h: 'Authentication & authorization',
        p: '<strong>Read</strong> registry: any logged-in platform user (JWT). <strong>Create/update</strong>: admin role only (<code>require_admin</code>). Per-agent execution auth is separate — registry is metadata, not runtime IAM.',
      },
    ],
    action: { section: 'admin', tab: 'adm-agents', label: 'Open Agent Registry' },
  },
  {
    id: 'mcp',
    title: 'MCP & Tool Servers',
    icon: '🔌',
    oss: ['FastAPI', 'Python mcp SDK', 'httpx', 'Optional: FastMCP (stdio/HTTP)'],
    summary: 'Model Context Protocol pattern — tools hosted outside the agent process, called over HTTP with Basic Auth in Design 1.',
    blocks: [
      {
        h: 'Are we using MCP 2?',
        p: 'The stack installs the official <strong>Python <code>mcp</code> package</strong> (Anthropic MCP SDK, <code>mcp&gt;=1.0.0</code>). The <strong>production Docker service</strong> runs <code>mcp_server/http_server.py</code> — a <strong>FastAPI REST tool server</strong> with MCP-<em>compatible</em> surface (<code>GET /tools</code>, <code>POST /tools/{name}</code>), not the full MCP 2 wire protocol over stdio/SSE in the default compose profile.',
      },
      {
        h: 'FastMCP — when it is used',
        p: '<code>platform/mcp_server/server.py</code> defines an alternate entry using <strong>FastMCP</strong> (<code>mcp.server.fastmcp</code>) for <code>stdio</code> or <code>streamable-http</code> transports — useful for Cursor/Claude Desktop style clients. Run manually: <code>python -m mcp_server.server stdio</code> or <code>http</code>. Compose default CMD is <code>http_server</code> for predictable Basic Auth + playground proxying.',
      },
      {
        h: 'Authentication (authn)',
        ul: [
          '<strong>MCP server →</strong> HTTP <strong>Basic Auth</strong> (<code>MCP_BASIC_USER</code> / <code>MCP_BASIC_PASSWORD</code> in <code>.env</code>). Every <code>/health</code>, <code>/tools</code>, and invoke requires credentials.',
          '<strong>Platform UI →</strong> JWT login (<code>PyJWT</code>). MCP Playground never calls :8081 from the browser directly — gateway proxies with server-side credentials for builtin server.',
          '<strong>Custom servers in Playground:</strong> user enters URL + Basic Auth; gateway forwards (demo only — production should use vault-stored secrets).',
        ],
      },
      {
        h: 'Authorization (authz)',
        p: 'Demo scope: any authenticated operator can use MCP Playground; MCP server only validates Basic Auth (shared service account). <strong>Not yet implemented:</strong> per-tool RBAC, {policy} on tool payloads, or scoped tokens per agent. Production pattern: OAuth2/mTLS at MCP edge + policy engine before destructive tools like <code>create_ticket</code>.',
      },
      {
        h: 'Tools exposed',
        p: 'Three MCP servers for exploration: <strong>Ops :8081</strong> (<code>query_logs</code>, <code>retrieve_runbooks</code>, <code>get_metrics</code>, <code>create_ticket</code>) · <strong>Policy :8082</strong> (<code>check_opa_policy</code>, <code>list_policy_rules</code>, <code>preview_hitl_gate</code>) · <strong>RAG :8083</strong> (<code>list_runbooks</code>, <code>get_runbook_by_id</code>, RAG search). MCP Playground left rail lists all three.',
      },
      {
        h: 'Try it',
        p: 'MCP Playground (left nav): connect → list tools → edit JSON → Run tool. Same flow as MCP Inspector.',
      },
    ],
    action: { section: 'mcp', tab: 'mcp-playground', label: 'Open MCP Inspector' },
  },
  {
    id: 'mcp-vs-skills',
    title: 'MCP vs Skills',
    icon: '⚖️',
    oss: ['agentregistry Skills', 'MCP HTTP server', 'SKILL.md bundles'],
    summary: 'MCP = live callable tools · Skills = packaged knowledge + optional scripts — both in agentregistry.',
    blocks: [
      {
        h: 'MCP (Model Context Protocol)',
        ul: [
          '<strong>What:</strong> Servers expose tools the agent calls at runtime (<code>query_logs</code>, <code>get_metrics</code>, <code>create_ticket</code>).',
          '<strong>When:</strong> Live observability, RAG retrieval from {vector}, side effects after HITL.',
          '<strong>Design 1:</strong> Ops MCP Server :8081 · MCP Inspector tab · MCP agent mode.',
          '<strong>Risk:</strong> Network calls + side effects → auth (Basic Auth) + {policy} + HITL.',
        ],
      },
      {
        h: 'Skills (agentregistry)',
        ul: [
          '<strong>What:</strong> <code>SKILL.md</code> + optional Python scripts — procedural knowledge, eval helpers, checklists.',
          '<strong>When:</strong> Golden-alert evals, deterministic rules, operator checklists, teaching before production MCP.',
          '<strong>Design 1:</strong> 4 skills in namespace <code>design1</code> — see Skills Catalog tab.',
          '<strong>Risk:</strong> Scripts are whitelisted read-only demos; checklists have no API surface.',
        ],
      },
      {
        h: 'Decision matrix',
        ul: [
          'Live {logs} logs → <strong>MCP</strong> <code>query_logs</code>',
          'CI severity rules → <strong>Skill</strong> <code>severity-classifier</code>',
          'Runtime runbook RAG → <strong>MCP</strong> <code>retrieve_runbooks</code>',
          'Verify runbook ID in eval → <strong>Skill</strong> <code>runbook-recall-check</code>',
          'HITL operator checklist → <strong>Skill</strong> <code>hitl-approval-checklist</code>',
          'Ticket after approve → <strong>MCP</strong> <code>create_ticket</code>',
        ],
      },
      {
        h: 'Bundled skills in this course',
        p: '<code>checkout-redis-triage</code> (metrics heuristic) · <code>severity-classifier</code> (P1/P2/P3 rules) · <code>runbook-recall-check</code> (golden eval) · <code>hitl-approval-checklist</code> (procedural only). Stored in agentregistry; scripts under <code>platform/skills/</code>.',
      },
    ],
    action: { section: 'mcp', tab: 'mcp-vs-skills', label: 'Open MCP vs Skills guide' },
  },
  {
    id: 'multi',
    title: 'Multi-Agent Orchestration',
    icon: '🌳',
    oss: ['LangGraph', 'LangChain Core', 'Ollama (LLM)', '{llmops} (OTEL spans)'],
    summary: 'Supervisor orchestrator delegates alert triage to specialist worker agents in a hierarchical graph.',
    blocks: [
      {
        h: 'Topology',
        p: 'Root: <code>sre-supervisor</code> (orchestrator). Children in order: <code>triage-worker</code> → <code>runbook-worker</code> → <code>logs-worker</code> → <code>metrics-worker</code> → <code>remediation-worker</code> → HITL gate → <code>incident-worker</code>. Each worker is a LangGraph node with a narrow responsibility — easier to test, trace, and swap than one monolithic graph.',
      },
      {
        h: 'OSS stack',
        ul: [
          '<strong>LangGraph</strong> — <code>StateGraph</code> with shared <code>AgentState</code>; <code>MemorySaver</code> checkpoints for HITL resume.',
          '<strong>Supervisor routing</strong> — LLM (Ollama) chooses <code>full_pipeline</code> vs <code>fast_path</code> based on alert severity and context.',
          '<strong>Workers</strong> — call the same underlying tools as standalone mode ({vector} RAG, {logs}, {metrics}) but scoped to one step each.',
          '<strong>Tracing</strong> — each worker emits OTEL span names consumed by {llmops} (<code>worker/triage</code>, <code>worker/logs</code>, etc.).',
        ],
      },
      {
        h: 'Delegation events',
        p: 'Every supervisor → worker handoff is recorded in <code>delegation_events</code> on the API response: timestamp, from_agent, to_agent, reason. Operations → Multi-Agent Flow renders this as a live tree + event log so you can explain <em>why</em> the supervisor routed a certain way.',
      },
      {
        h: 'When to use multi-agent vs standalone',
        ul: [
          '<strong>Multi-agent:</strong> complex incidents, team ownership per capability, clearer audit per specialist, easier to add/remove workers without rewriting the whole graph.',
          '<strong>Standalone:</strong> simpler deployments, fewer moving parts, good for learning LangGraph basics first.',
          '<strong>MCP mode:</strong> when tools must run in a separate trust boundary (network isolation, shared tool farm).',
        ],
      },
      {
        h: 'Registry mapping',
        p: 'Each worker has a row in Agent Registry (<code>kind: worker</code>, <code>mode: multi</code>). Supervisor slug: <code>sre-supervisor</code>. Register new workers via Admin before wiring new LangGraph nodes in <code>platform/multi_agent/workers.py</code>.',
      },
    ],
    action: { section: 'operations', tab: 'ops-multi', label: 'View multi-agent tree' },
  },
  {
    id: 'standalone',
    title: 'Standalone LangGraph Agent',
    icon: '⚡',
    oss: ['LangGraph', '{vector}', 'sentence-transformers', 'Ollama', 'httpx ({logs}/{metrics})'],
    summary: 'Single orchestrator pipeline — all tools in-process inside the agent runtime.',
    blocks: [
      {
        h: 'Graph nodes (in order)',
        p: '<code>classify</code> → <code>retrieve_runbook</code> → <code>query_logs</code> → <code>query_metrics</code> → <code>recommend</code> → <code>hitl_gate</code> → <code>execute</code>. State carries alert payload, retrieved runbook chunks, log snippets, metric anomalies, and the LLM recommendation through the graph.',
      },
      {
        h: 'OSS tools in-process',
        ul: [
          '<strong>LangGraph</strong> — graph definition in <code>platform/agent/graph.py</code>; compiled once at agent startup.',
          '<strong>{vector}</strong> — RAG retrieval via embedded sentence-transformers (MiniLM, 384-d).',
          '<strong>{logs} / {metrics}</strong> — queried over HTTP from tool functions (no MCP hop).',
          '<strong>Ollama</strong> — local LLM for classification and remediation text generation.',
        ],
      },
      {
        h: 'API & UI',
        p: 'Agent API on <code>:8002</code>. Platform Operations → Incident runs the capstone checkout-redis-pool alert. Response includes <code>worker_trace</code> (node names + timings) and <code>thread_id</code> for HITL resume.',
      },
      {
        h: 'When to use',
        ul: [
          'Best starting point for learning LangGraph — one graph, one process, full visibility.',
          'Smaller Docker footprint (no separate MCP server required).',
          'Production teams often start standalone, then split tools to MCP or workers when isolation/scale demands it.',
        ],
      },
    ],
    action: { section: 'operations', tab: 'ops-incident', label: 'Run standalone pipeline' },
  },
  {
    id: 'ingestion',
    title: 'Ingestion & RAG',
    icon: '📚',
    oss: ['{vector}', 'sentence-transformers', 'FastAPI runbook-ingestion', '{metrics}', '{logs}', '{dashboards}'],
    summary: 'Runbooks become searchable vectors; observability signals feed the agent context.',
    blocks: [
      {
        h: 'Runbook pipeline',
        ul: [
          'Markdown runbooks (git-seeded under <code>rag/runbooks/</code>) → chunk (~512 tokens) → embed with <strong>MiniLM</strong> (384 dimensions) → upsert into {vector}.',
          '<strong>runbook-ingestion</strong> service on <code>:8092</code> — REST API for re-index, status, and collection stats.',
          'Auth: API token (<code>RUNBOOK_INGEST_TOKEN</code>) on write endpoints; read/status often open in demo.',
          'Platform Ingestion tab: Pipeline status, job history, {ingestTab} (browse chunks + metadata).',
        ],
      },
      {
        h: 'Observability ingestion',
        ul: [
          '<strong>{metrics}</strong> scrapes <code>metrics-exporter</code> and service targets; alert rules fire on checkout error rate.',
          'Alert webhook receiver (<code>:8090</code>) → triggers agent pipeline with structured alert JSON.',
          '<strong>{logs}</strong> ship container and app logs; the agent queries them from tools.',
          '<strong>{dashboards}</strong> visualize the capstone spike for human verification.',
        ],
      },
      {
        h: 'Why ingestion matters for agents',
        p: 'Without {vector}, the agent hallucinates procedures. Without {logs}/{metrics}, it reasons on alert text alone. Phase 1 ensures every downstream node (RAG, logs, metrics) has <strong>grounded, fresh context</strong> — the foundation of trustworthy AgentOps.',
      },
      {
        h: 'Extend it',
        p: 'Add a new runbook markdown file → trigger re-ingest via API or restart ingestion job. Add {metrics} rules for new services. Point log shippers at additional paths. Production: schedule ingestion on git webhook, version collections per environment.',
      },
    ],
    action: { section: 'ingestion', tab: 'ing-jobs', label: '{ingestTab}' },
  },
  {
    id: 'evaluation',
    title: 'Evaluation & Tracing',
    icon: '📈',
    oss: ['{llmops}', 'Pytest', 'OpenTelemetry Collector'],
    summary: 'Prove the agent is grounded, fast, and repeatable before trusting automation.',
    blocks: [
      {
        h: '{llmops} — traces, experiments, LLM-as-judge',
        ul: [
          'This design uses one tool in depth. Design 1 = Langfuse, Design 2 = Phoenix, Design 3 = MLflow.',
          'Every LangGraph node becomes a trace span. Filter by <code>thread_id</code>.',
          'Eval Suite writes a dataset/experiment run plus an <code>llm-as-judge</code> generation/span.',
          'Look for score <code>llm_judge_groundedness</code> after you click Run Eval Suite.',
        ],
      },
      {
        h: 'Golden-set eval gate',
        ul: [
          'Fixtures in <code>agent/evals/golden_alerts.json</code> — expected runbook IDs, severity, service names.',
          'Evaluation tab invokes the real agent and checks RAG recall, groundedness, correctness, HITL, latency.',
          'An LLM-as-judge prompt scores whether the recommendation is grounded — published into {llmops}, not a second vendor.',
          'Think of it as <strong>regression tests for RAG + reasoning</strong>, not just unit tests on tools.',
        ],
      },
      {
        h: 'OpenTelemetry',
        p: 'OTEL Collector on <code>:4318</code> receives OTLP HTTP from agent/gateway. Exports to {llmops} and optionally other backends. Standardizes span naming so multi-agent worker traces align with standalone spans.',
      },
      {
        h: 'What to measure',
        ul: [
          '<strong>Grounding:</strong> did retrieval return the correct runbook ID?',
          '<strong>Latency:</strong> p95 pipeline time under load.',
          '<strong>Safety:</strong> did destructive recommendations always pause at HITL?',
          '<strong>Cost/proxy:</strong> LLM call count per incident (Ollama = local, but pattern applies to cloud models).',
        ],
      },
    ],
    action: { section: 'evaluation', tab: 'eval-gate', label: 'Run eval suite' },
  },
  {
    id: 'guardrails',
    title: 'Guardrails & HITL',
    icon: '🛡️',
    oss: ['{policy}', '{safety}', 'FastAPI HITL gate', 'LangGraph interrupts'],
    summary: 'Policy checks and human approval before destructive remediation executes.',
    blocks: [
      {
        h: '{policy} policy engine',
        ul: [
          'Live policy evaluates agent recommendations before HITL and execute.',
          'Rules example: destructive actions (restart, scale-down language) allowed on <strong>P1 only</strong>; P2/P3 destructive paths denied.',
          'Gateway/agent calls {policy} with JSON input: severity, action type, recommendation text.',
          'Verdict returned as <code>allow</code> / <code>deny</code> with reason — surfaced in HITL UI before Approve enables.',
        ],
      },
      {
        h: 'HITL gate (human-in-the-loop)',
        ul: [
          'LangGraph <code>interrupt_before=[\"hitl_gate\"]</code> pauses graph execution until operator approves.',
          'Platform Simulation tab shows pending recommendation, {policy} verdict, runbook citation, and Approve/Deny buttons.',
          'Decisions persisted in PostgreSQL with operator email, timestamp, thread_id — audit-ready.',
          'Deny path ends graph without ticket creation; Approve resumes → execute node → ticket-api.',
        ],
      },
      {
        h: 'Authentication & authorization',
        p: '<strong>Authn:</strong> JWT login required to approve/deny. <strong>Authz:</strong> demo allows any operator role; production would map AD/OIDC groups to <code>approver</code> vs <code>viewer</code> and require dual approval for P1 destructive actions.',
      },
      {
        h: 'Defense in depth',
        p: 'Layer 1: input validation on webhook payloads. Layer 2: {policy} on recommendation content. Layer 3: HITL interrupt. Layer 4: ticket audit trail. MCP mode adds Layer 0: network boundary on tool execution — but policy still applies before tickets fire.',
      },
    ],
    action: { section: 'guardrails', tab: 'grd-overview', label: '{policy} overview' },
  },
  {
    id: 'actions',
    title: 'Actions & Audit',
    icon: '🎫',
    oss: ['PostgreSQL 16', 'FastAPI ticket-api', 'SQLAlchemy'],
    summary: 'Approved remediations become durable tickets and audit records.',
    blocks: [
      {
        h: 'ticket-api service',
        ul: [
          'FastAPI microservice on <code>:8091</code> — creates and lists ops tickets.',
          'After HITL approve, execute node calls <code>create_ticket</code> (in-process standalone/multi, or via MCP HTTP in MCP mode).',
          'Ticket format: <code>OPS-xxxxxxxx</code> with service, severity, recommendation, runbook_id, timestamps.',
          'Stored in PostgreSQL — same database cluster as agent registry and HITL decisions (different tables).',
        ],
      },
      {
        h: 'Audit trail — four lenses',
        ul: [
          '<strong>Actions tab</strong> — all tickets with status and detail view.',
          '<strong>HITL history</strong> — who approved/denied, linked by thread_id.',
          '<strong>{llmops} traces</strong> — technical proof of which nodes ran and how long.',
          '<strong>Agent registry</strong> — metadata on which orchestrator/worker version was active.',
        ],
      },
      {
        h: 'CI/CD hook',
        p: 'GitHub Actions workflow runs lint, pytest, and MLflow eval on push. Phase 5 closes the loop: code change → eval pass → deploy → incident → HITL → ticket → postmortem with full traceability.',
      },
      {
        h: 'Production upgrades',
        p: 'Integrate with Jira/ServiceNow via ticket-api adapter, add SOX-style immutable audit log (WORM storage), and correlate tickets to change-management systems before auto-remediation goes live.',
      },
    ],
    action: { section: 'actions', tab: 'act-list', label: 'All tickets' },
  },
];

let learnTopicsActiveId = 'registry';

const CAPSTONE_DEMO_SCRIPT = `# After ./deploy.sh up && ./deploy.sh verify
cd deploy

# 1) Fire capstone alert
RESP=$(curl -sf -X POST http://localhost:8090/webhook/alert/checkout-redis-pool.json)

# 2) Extract thread_id
THREAD=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['agent_response']['thread_id'])")

# 3) Approve HITL
curl -sf -X POST http://localhost:8002/approve \\
  -H "Content-Type: application/json" \\
  -d "{\\"thread_id\\":\\"$THREAD\\",\\"approved\\":true}"

# 4) Confirm ticket
curl -sf http://localhost:8091/tickets | python3 -m json.tool`;

function learnEsc(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function learnArch(s) {
  return typeof archFill === 'function' ? archFill(String(s ?? '')) : String(s ?? '');
}

function learnPorts() {
  const extra = (typeof getArchDesign === 'function' && getArchDesign().ports) || [];
  return [...LEARN_PORTS_COMMON, ...extra];
}

function renderLearningOverview() {
  const el = document.getElementById('learn-overview-body');
  if (!el) return;
  el.innerHTML = `
    <div class="learn-hero card glossy-card">
      <div class="learn-hero-text">
        <span class="learn-badge">${learnArch('{name}')} · End to end</span>
        <h3>Production SRE AgentOps — the whole story</h3>
        <p>You are not building a chatbot that reads logs. You are building a <strong>five-phase AgentOps platform</strong>: ingest signals & runbooks, orchestrate with LangGraph, evaluate with ${learnArch('{llmops}')}/MLflow, guard with ${learnArch('{policy}')}/HITL, and record actions in PostgreSQL.</p>
      </div>
      <figure class="learn-figure">
        <img src="/static/learn/step-00-architecture-overview.png" alt="Five-phase architecture overview" loading="lazy" />
        <figcaption>Five phases · one Docker Compose stack · capstone: checkout Redis pool</figcaption>
      </figure>
    </div>

    <div class="learn-flow-card card glossy-card">
      <h4>End-to-end flow</h4>
      <pre class="learn-flow-diagram">${learnArch(`Runbooks → {vector}          Alerts + logs + metrics → {logs}/{metrics}
         └──────────────┬──────────────────────┘
                        ▼
             LangGraph agent triages incident
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
    {llmops} trace   MLflow eval    {policy} + HITL
         └──────────────┴──────────────┘
                        ▼
            Ticket opened in PostgreSQL`)}</pre>
    </div>

    <div class="learn-phase-grid">
      ${LEARNING_PHASES.map((p) => `
        <article class="learn-phase-card learn-phase-${p.color}">
          <span class="learn-phase-num">Phase ${p.n}</span>
          <h4>${learnEsc(p.name)}</h4>
          <p class="learn-phase-q">${learnEsc(p.question)}</p>
          <p class="muted learn-phase-tools">${learnEsc(learnArch(p.tools))}</p>
        </article>
      `).join('')}
    </div>

    <div class="learn-ports card glossy-card">
      <h4>Ports & login</h4>
      <p class="muted">Demo credentials: <code>operator@agentops.local</code> / <code>operator123</code> · Admin: <code>admin@agentops.local</code> / <code>admin123</code></p>
      <table class="data-table learn-port-table">
        <thead><tr><th>Port</th><th>Service</th></tr></thead>
        <tbody>${learnPorts().map(([port, svc]) => `<tr><td><code>:${port}</code></td><td>${learnEsc(svc)}</td></tr>`).join('')}</tbody>
      </table>
    </div>

    <div class="card glossy-card learn-topics-teaser">
      <h4>Deep-dive topics</h4>
      <p class="muted">Agent Registry, MCP auth, multi-agent, ingestion, eval, guardrails — OSS stack details and how to extend.</p>
      <button type="button" class="btn-primary btn-glossy btn-sm learn-go-topics" data-topic="mcp">
        <span class="btn-shine"></span>Open Topics → MCP & Tools
      </button>
    </div>
  `;
  el.querySelector('.learn-go-topics')?.addEventListener('click', (e) => {
    const topic = e.currentTarget.dataset.topic || 'registry';
    learnTopicsActiveId = topic;
    if (window.switchSection) window.switchSection('learning', 'learn-topics');
  });
}

function renderLearnTopicContent(topic) {
  if (!topic) return '<p class="muted">Select a topic.</p>';
  const blocks = (topic.blocks || []).map((b) => {
    const body = b.p ? `<p>${learnArch(b.p)}</p>` : '';
    const ul = b.ul ? `<ul class="learn-topic-ul">${b.ul.map((li) => `<li>${learnArch(li)}</li>`).join('')}</ul>` : '';
    return `<section class="learn-topic-block"><h4>${learnEsc(learnArch(b.h))}</h4>${body}${ul}</section>`;
  }).join('');
  const oss = (topic.oss || []).map((t) => `<span class="pill open">${learnEsc(learnArch(t))}</span>`).join(' ');
  const action = topic.action
    ? `<button type="button" class="btn-primary btn-glossy btn-sm learn-topic-action" data-section="${topic.action.section}" data-tab="${topic.action.tab || ''}"><span class="btn-shine"></span>${learnEsc(learnArch(topic.action.label))}</button>`
    : '';
  return `
    <div class="learn-topic-hero">
      <span class="learn-topic-icon">${topic.icon || '📖'}</span>
      <div>
        <h3>${learnEsc(topic.title)}</h3>
        <p class="muted">${learnEsc(learnArch(topic.summary))}</p>
        <div class="learn-topic-oss">${oss}</div>
      </div>
    </div>
    <div class="learn-topic-blocks">${blocks}</div>
    ${action ? `<div class="learn-topic-foot">${action}</div>` : ''}`;
}

function renderLearningTopics() {
  const el = document.getElementById('learn-topics-body');
  if (!el) return;
  const active = LEARNING_TOPICS.find((t) => t.id === learnTopicsActiveId) || LEARNING_TOPICS[0];
  el.innerHTML = `
    <div class="learn-topics-layout card glossy-card">
      <aside class="learn-topics-rail">
        <strong class="learn-topics-rail-title">Topics</strong>
        ${LEARNING_TOPICS.map((t) => `
          <button type="button" class="learn-topic-rail-btn${t.id === active.id ? ' active' : ''}" data-topic-id="${t.id}">
            <span>${t.icon}</span> ${learnEsc(t.title)}
          </button>`).join('')}
      </aside>
      <article class="learn-topics-main" id="learn-topics-main">
        ${renderLearnTopicContent(active)}
      </article>
    </div>`;
  el.querySelectorAll('.learn-topic-rail-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      learnTopicsActiveId = btn.dataset.topicId;
      renderLearningTopics();
    });
  });
  el.querySelector('.learn-topic-action')?.addEventListener('click', (e) => {
    const b = e.currentTarget;
    if (window.switchSection) window.switchSection(b.dataset.section, b.dataset.tab || undefined);
  });
}

function renderLearningCapstone() {
  const el = document.getElementById('learn-capstone-body');
  if (!el) return;
  el.innerHTML = `
    <div class="learn-capstone-hero card glossy-card">
      <span class="learn-badge p1">Capstone incident</span>
      <h3>Checkout Redis connection pool exhaustion</h3>
      <dl class="meta-list compact learn-cap-meta">
        <div><dt>Service</dt><dd>checkout-service</dd></div>
        <div><dt>Severity</dt><dd><span class="pill p1">P1</span></dd></div>
        <div><dt>Alert</dt><dd>CheckoutHighErrorRate · HTTP 500 on /checkout</dd></div>
        <div><dt>Log line</dt><dd><code>Timeout waiting for connection pool (Redis)</code></dd></div>
        <div><dt>Runbook</dt><dd><code>checkout-redis-pool.md</code></dd></div>
      </dl>
    </div>

    <div class="card glossy-card learn-story">
      <h4>The story in one paragraph</h4>
      <p>${learnArch('{metrics} sees error rate spike → alert fires → webhook hits the agent → LangGraph classifies the alert, <strong>retrieves the Redis pool runbook from {vector}</strong>, pulls matching logs from {logs} and error-rate from {metrics}, recommends remediation → {llmops} records every step → {policy} checks the action is allowed for P1 → <strong>HITL pauses</strong> because the fix is destructive → operator approves in the Platform UI → ticket-api writes a row to PostgreSQL.')}</p>
      <p class="muted">That is the entire course in one sentence.</p>
    </div>

    <div class="learn-cap-actions">
      <button type="button" class="btn-primary btn-glossy learn-go-btn" data-scene="step-02-agent-orchestration">
        <span class="btn-shine"></span>Walk through in Operations
      </button>
      <button type="button" class="btn-outline learn-go-btn" data-section="ingestion" data-tab="ing-jobs">${learnArch('See runbook in {vector}')}</button>
    </div>
  `;
  bindLearnGoButtons(el);
}

function renderLearningJourney() {
  const el = document.getElementById('learn-journey-body');
  if (!el) return;
  el.innerHTML = `
    <p class="learn-journey-intro muted">Follow each step in order. Click <strong>Open in platform</strong> to jump to the live UI screen — mockup shown for reference.</p>
    <div class="learn-timeline">
      ${LEARNING_STEPS.map((step, i) => `
        <article class="learn-step card glossy-card" id="${step.id}">
          <div class="learn-step-head">
            <span class="learn-step-phase">${learnEsc(step.phase)}</span>
            <span class="learn-step-idx">${String(i).padStart(2, '0')}</span>
          </div>
          <h4>${learnEsc(learnArch(step.title))}</h4>
          <p class="muted">${learnEsc(learnArch(step.subtitle))}</p>
          <div class="learn-step-grid">
            <div>
              <h5>What happens</h5>
              <p>${learnEsc(learnArch(step.happens))}</p>
              <h5>What to expect</h5>
              <p>${learnEsc(learnArch(step.expect))}</p>
              <blockquote class="learn-mind">${learnEsc(learnArch(step.mind))}</blockquote>
              <div class="learn-step-actions">
                <button type="button" class="btn-primary btn-glossy btn-sm learn-go-btn" data-scene="${learnEsc(step.scene)}">Open in platform →</button>
                <span class="muted learn-try-hint">${learnEsc(learnArch(step.tryUi))}</span>
              </div>
            </div>
            <figure class="learn-figure learn-figure-sm">
              <img src="${step.img}" alt="${learnEsc(step.title)} mockup" loading="lazy" />
            </figure>
          </div>
        </article>
      `).join('')}
    </div>
  `;
  bindLearnGoButtons(el);
}

function renderLearningDemo() {
  const el = document.getElementById('learn-demo-body');
  if (!el) return;
  el.innerHTML = `
    <div class="card glossy-card">
      <h4>Full capstone script</h4>
      <p class="muted">Run after <code>./deploy.sh up</code> and <code>./deploy.sh verify</code></p>
      <pre class="learn-code-block" id="learn-demo-script">${learnEsc(CAPSTONE_DEMO_SCRIPT)}</pre>
      <button type="button" class="btn-outline btn-sm" id="learn-copy-script">Copy script</button>
    </div>

    <div class="card glossy-card learn-checklist">
      <h4>Success checklist</h4>
      <ul class="learn-checks">
        <li><span class="learn-check">✓</span> Runbook retrieved: <code>checkout-redis-pool</code></li>
        <li><span class="learn-check">✓</span> ${learnArch('{llmops}')} trace with all graph spans</li>
        <li><span class="learn-check">✓</span> HITL paused then completed after approve</li>
        <li><span class="learn-check">✓</span> Ticket row exists with severity P1</li>
        <li><span class="learn-check">✓</span> <code>./deploy.sh eval</code> passes</li>
      </ul>
    </div>

    <div class="learn-demo-actions card glossy-card">
      <h4>Guided UI tour</h4>
      <p class="muted">Jump to each phase with the capstone scenario pre-loaded where applicable.</p>
      <div class="learn-tour-grid">
        ${LEARNING_STEPS.filter((s) => s.scene).map((s) => `
          <button type="button" class="learn-tour-btn learn-go-btn" data-scene="${s.scene}">
            <strong>${learnEsc(s.phase)}</strong>
            <span>${learnEsc(s.title)}</span>
          </button>
        `).join('')}
      </div>
      <button type="button" class="btn-primary btn-glossy block learn-go-btn" data-scene="step-02-agent-orchestration" style="margin-top:14px">
        <span class="btn-shine"></span>Start capstone demo (Operations)
      </button>
    </div>
  `;
  bindLearnGoButtons(el);
  document.getElementById('learn-copy-script')?.addEventListener('click', () => {
    navigator.clipboard?.writeText(CAPSTONE_DEMO_SCRIPT.replace(/\\"/g, '"'));
    window.showToast?.('success', 'Copied', 'Capstone script on clipboard');
  });
}

function bindLearnGoButtons(root) {
  root?.querySelectorAll('.learn-go-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (btn.dataset.scene && window.navigateLearningScene) {
        window.navigateLearningScene(btn.dataset.scene);
      } else if (btn.dataset.section && window.switchSection) {
        window.switchSection(btn.dataset.section, btn.dataset.tab || undefined);
      }
    });
  });
}

function initLearningSection(tabId) {
  if (typeof renderNotebook === 'function') {
    const tab = tabId || 'learn-slides';
    if (tab === 'learn-slides') return;
    if (tab === 'learn-bookmarks' && typeof renderNotebookBookmarks === 'function') {
      renderNotebookBookmarks();
      return;
    }
    if (tab === 'learn-notes' && typeof renderNotebookNotes === 'function') {
      renderNotebookNotes();
      return;
    }
    if (tab === 'learn-highlights' && typeof renderNotebookHighlights === 'function') {
      renderNotebookHighlights();
      return;
    }
    if (tab === 'learn-designs' && typeof renderDesignsTab === 'function') {
      renderDesignsTab();
      return;
    }
    if (typeof initNotebookKeyboard === 'function') initNotebookKeyboard();
    renderNotebook();
    return;
  }
  renderLearningOverview();
}
