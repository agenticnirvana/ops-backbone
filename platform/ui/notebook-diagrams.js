/** Inline architecture boards + diagrams for the Learning notebook. */

function nbFig(src, caption) {
  return `
    <figure class="nb-figure">
      <img src="/static/learn/${src}" alt="${caption}" loading="lazy" />
      <figcaption>${caption}</figcaption>
    </figure>`;
}

function nbArchBoard(designId) {
  const d = (typeof getArchDesign === 'function' ? getArchDesign(designId) : null);
  const phases = d ? d.phases : {
    ingestion: ['Alertmanager', 'Loki + Promtail', 'Prometheus', 'Grafana', 'ChromaDB'],
    orchestration: ['LangGraph', 'Gateway UI', 'MCP servers', 'Ollama'],
    evaluation: ['Langfuse', 'MLflow', 'OTEL'],
    guardrails: ['OPA / Rego', 'HITL gate', 'FastAPI'],
    action: ['PostgreSQL', 'Ticket API', 'GitHub Actions'],
  };
  const cols = [
    { goto: 'ing-splash', n: '01', title: 'Ingestion', tone: 'sky', blurb: 'What the agent sees', nodes: phases.ingestion },
    { goto: 'orch-splash', n: '02', title: 'Orchestration', tone: 'violet', blurb: 'How it reasons', nodes: phases.orchestration },
    { goto: 'eval-splash', n: '03', title: 'Evaluation', tone: 'teal', blurb: 'How you trust it', nodes: phases.evaluation },
    { goto: 'grd-splash', n: '04', title: 'Guardrails', tone: 'amber', blurb: 'What can run', nodes: phases.guardrails },
    { goto: 'act-splash', n: '05', title: 'Action', tone: 'green', blurb: 'What gets recorded', nodes: phases.action },
  ];
  return `
    <div class="nb-arch" role="img" aria-label="Five-phase AgentOps architecture">
      ${cols.map((c) => `
        <button type="button" class="nb-arch-col tone-${c.tone}" data-nb-goto="${c.goto}">
          <span class="nb-arch-n">${c.n}</span>
          <strong>${c.title}</strong>
          <small>${c.blurb}</small>
          <ul>${c.nodes.map((n) => `<li>${n}</li>`).join('')}</ul>
        </button>`).join('')}
    </div>
    <p class="nb-arch-foot">Fixed across designs: LangGraph · Ollama · Platform UI · checkout-redis-pool${d ? ` · viewing <strong>${d.name}</strong>` : ''}</p>`;
}

function nbIngestPipeSvg() {
  return `
    <svg class="nb-flow-svg" viewBox="0 0 720 220" role="img" aria-label="Ingestion pipeline">
      <defs>
        <linearGradient id="nbFlow" x1="0" x2="1">
          <stop offset="0" stop-color="#38bdf8"/><stop offset="1" stop-color="#2dd4bf"/>
        </linearGradient>
        <marker id="nbArr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 z" fill="#0f766e"/>
        </marker>
      </defs>
      <text x="12" y="22" class="nb-svg-kicker">Phase 1 · two pipes into the agent</text>
      <g>
        <rect x="16" y="44" rx="12" width="150" height="52" fill="#fff7ed" stroke="#fb923c"/>
        <text x="91" y="68" text-anchor="middle" class="nb-svg-title">Runbooks.md</text>
        <text x="91" y="84" text-anchor="middle" class="nb-svg-sub">git + Drive</text>
        <line x1="166" y1="70" x2="214" y2="70" stroke="url(#nbFlow)" stroke-width="3" marker-end="url(#nbArr)"/>
        <rect x="220" y="44" rx="12" width="160" height="52" fill="#ecfeff" stroke="#22d3ee"/>
        <text x="300" y="68" text-anchor="middle" class="nb-svg-title">Ingestion :8092</text>
        <text x="300" y="84" text-anchor="middle" class="nb-svg-sub">chunk · MiniLM 384-d</text>
        <line x1="380" y1="70" x2="428" y2="70" stroke="url(#nbFlow)" stroke-width="3" marker-end="url(#nbArr)"/>
        <rect x="434" y="44" rx="12" width="150" height="52" fill="#fef9c3" stroke="#eab308"/>
        <text x="509" y="68" text-anchor="middle" class="nb-svg-title">Chroma</text>
        <text x="509" y="84" text-anchor="middle" class="nb-svg-sub">vector index</text>
      </g>
      <g>
        <rect x="16" y="132" rx="12" width="118" height="52" fill="#fee2e2" stroke="#f87171"/>
        <text x="75" y="156" text-anchor="middle" class="nb-svg-title">Alerts</text>
        <text x="75" y="172" text-anchor="middle" class="nb-svg-sub">Alertmanager</text>
        <rect x="150" y="132" rx="12" width="118" height="52" fill="#e0f2fe" stroke="#38bdf8"/>
        <text x="209" y="156" text-anchor="middle" class="nb-svg-title">Logs</text>
        <text x="209" y="172" text-anchor="middle" class="nb-svg-sub">Loki</text>
        <rect x="284" y="132" rx="12" width="118" height="52" fill="#ffedd5" stroke="#fb923c"/>
        <text x="343" y="156" text-anchor="middle" class="nb-svg-title">Metrics</text>
        <text x="343" y="172" text-anchor="middle" class="nb-svg-sub">Prometheus</text>
        <line x1="402" y1="158" x2="454" y2="158" stroke="#64748b" stroke-width="3" marker-end="url(#nbArr)"/>
        <rect x="460" y="132" rx="12" width="160" height="52" fill="#ede9fe" stroke="#8b5cf6"/>
        <text x="540" y="156" text-anchor="middle" class="nb-svg-title">LangGraph</text>
        <text x="540" y="172" text-anchor="middle" class="nb-svg-sub">reads both pipes</text>
      </g>
    </svg>`;
}

function nbSqlVsVecSvg() {
  return `
    <svg class="nb-flow-svg" viewBox="0 0 720 210" role="img" aria-label="SQL rows versus embedding space">
      <rect x="12" y="28" rx="14" width="330" height="168" fill="#fff" stroke="#d6d3d1"/>
      <text x="28" y="54" class="nb-svg-kicker">Postgres row</text>
      <text x="28" y="84" class="nb-svg-title">id | title | body</text>
      <text x="28" y="112" font-family="ui-monospace,monospace" font-size="11" fill="#57534e">WHERE title ILIKE '%redis%'</text>
      <text x="28" y="148" class="nb-svg-sub">misses “connection starvation”</text>
      <rect x="378" y="28" rx="14" width="330" height="168" fill="#ecfdf5" stroke="#14b8a6"/>
      <text x="394" y="54" class="nb-svg-kicker">Vector (384-d)</text>
      <g transform="translate(402 78)">
        ${[0.7, 0.35, 0.9, 0.2, 0.55, 0.8, 0.4, 0.65, 0.3, 0.75, 0.5, 0.85].map((h, i) =>
          `<rect x="${i * 22}" y="${70 - h * 70}" width="16" height="${h * 70}" rx="2" fill="#0d9488" opacity="0.85"/>`
        ).join('')}
      </g>
      <text x="394" y="178" class="nb-svg-sub">nearest neighbor = similar meaning</text>
    </svg>`;
}

function nbRagLoopSvg() {
  return `
    <svg class="nb-flow-svg" viewBox="0 0 720 168" role="img" aria-label="RAG loop">
      <text x="12" y="22" class="nb-svg-kicker">RAG in one lap</text>
      ${[
        [20, 'Alert text'],
        [160, 'Embed'],
        [300, 'k-NN in Chroma'],
        [460, 'Top runbooks'],
        [600, 'LLM reasons'],
      ].map(([x, label], i) => `
        <g>
          <circle cx="${x}" cy="88" r="28" fill="${i === 4 ? '#ede9fe' : '#ccfbf1'}" stroke="#0f766e" stroke-width="2"/>
          <text x="${x}" y="92" text-anchor="middle" font-size="11" font-weight="700" fill="#134e4a">${i + 1}</text>
          <text x="${x}" y="138" text-anchor="middle" font-size="11" fill="#44403c">${label}</text>
        </g>
        ${i < 4 ? `<line x1="${x + 30}" y1="88" x2="${x + 110}" y2="88" stroke="#0d9488" stroke-width="2.5" marker-end="url(#nbArr2)"/>` : ''}
      `).join('')}
      <defs>
        <marker id="nbArr2" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 z" fill="#0d9488"/>
        </marker>
      </defs>
    </svg>`;
}

function nbOrchSvg() {
  return `
    <svg class="nb-flow-svg" viewBox="0 0 720 200" role="img" aria-label="LangGraph orchestration">
      <text x="12" y="22" class="nb-svg-kicker">Phase 2 · one graph, three modes</text>
      <rect x="24" y="48" rx="12" width="672" height="44" fill="#ede9fe" stroke="#8b5cf6"/>
      <text x="360" y="76" text-anchor="middle" class="nb-svg-title">LangGraph  classify → RAG → logs → metrics → recommend → HITL → execute</text>
      <g>
        <rect x="24" y="116" rx="10" width="210" height="60" fill="#f5f3ff" stroke="#a78bfa"/>
        <text x="129" y="142" text-anchor="middle" class="nb-svg-title">Standalone</text>
        <text x="129" y="160" text-anchor="middle" class="nb-svg-sub">one worker</text>
        <rect x="255" y="116" rx="10" width="210" height="60" fill="#eef2ff" stroke="#818cf8"/>
        <text x="360" y="142" text-anchor="middle" class="nb-svg-title">Multi-agent</text>
        <text x="360" y="160" text-anchor="middle" class="nb-svg-sub">supervisor + specialists</text>
        <rect x="486" y="116" rx="10" width="210" height="60" fill="#ecfeff" stroke="#22d3ee"/>
        <text x="591" y="142" text-anchor="middle" class="nb-svg-title">MCP mode</text>
        <text x="591" y="160" text-anchor="middle" class="nb-svg-sub">:8081 :8082 :8083</text>
      </g>
    </svg>`;
}

function nbEvalSvg() {
  return `
    <svg class="nb-flow-svg" viewBox="0 0 720 170" role="img" aria-label="Evaluation architecture">
      <text x="12" y="22" class="nb-svg-kicker">Phase 3 · trace it, score it, gate it</text>
      <rect x="20" y="50" rx="12" width="200" height="90" fill="#ecfeff" stroke="#22d3ee"/>
      <text x="120" y="88" text-anchor="middle" class="nb-svg-title">Langfuse</text>
      <text x="120" y="108" text-anchor="middle" class="nb-svg-sub">spans per node</text>
      <rect x="260" y="50" rx="12" width="200" height="90" fill="#dbeafe" stroke="#60a5fa"/>
      <text x="360" y="88" text-anchor="middle" class="nb-svg-title">MLflow</text>
      <text x="360" y="108" text-anchor="middle" class="nb-svg-sub">golden alerts / recall</text>
      <rect x="500" y="50" rx="12" width="200" height="90" fill="#f1f5f9" stroke="#94a3b8"/>
      <text x="600" y="88" text-anchor="middle" class="nb-svg-title">OTEL</text>
      <text x="600" y="108" text-anchor="middle" class="nb-svg-sub">export anywhere</text>
    </svg>`;
}

function nbGuardSvg() {
  return `
    <svg class="nb-flow-svg" viewBox="0 0 720 180" role="img" aria-label="OPA and HITL guardrails">
      <text x="12" y="22" class="nb-svg-kicker">Phase 4 · policy then a human</text>
      <rect x="20" y="50" rx="12" width="150" height="70" fill="#ede9fe" stroke="#8b5cf6"/>
      <text x="95" y="90" text-anchor="middle" class="nb-svg-title">Recommend</text>
      <line x1="170" y1="85" x2="220" y2="85" stroke="#b45309" stroke-width="3"/>
      <rect x="224" y="50" rx="12" width="150" height="70" fill="#ffedd5" stroke="#f59e0b"/>
      <text x="299" y="82" text-anchor="middle" class="nb-svg-title">OPA / Rego</text>
      <text x="299" y="100" text-anchor="middle" class="nb-svg-sub">allow / deny</text>
      <line x1="374" y1="85" x2="424" y2="85" stroke="#b45309" stroke-width="3"/>
      <rect x="428" y="50" rx="12" width="150" height="70" fill="#fce7f3" stroke="#ec4899"/>
      <text x="503" y="82" text-anchor="middle" class="nb-svg-title">HITL</text>
      <text x="503" y="100" text-anchor="middle" class="nb-svg-sub">interrupt_before</text>
      <line x1="578" y1="85" x2="628" y2="85" stroke="#16a34a" stroke-width="3"/>
      <rect x="632" y="50" rx="12" width="70" height="70" fill="#dcfce7" stroke="#22c55e"/>
      <text x="667" y="90" text-anchor="middle" class="nb-svg-title">Go</text>
    </svg>`;
}

function nbActionSvg() {
  return `
    <svg class="nb-flow-svg" viewBox="0 0 720 160" role="img" aria-label="Action and ticket flow">
      <text x="12" y="22" class="nb-svg-kicker">Phase 5 · the paper trail</text>
      <rect x="24" y="50" rx="12" width="160" height="70" fill="#dcfce7" stroke="#22c55e"/>
      <text x="104" y="90" text-anchor="middle" class="nb-svg-title">Approve</text>
      <rect x="220" y="50" rx="12" width="200" height="70" fill="#ffedd5" stroke="#fb923c"/>
      <text x="320" y="82" text-anchor="middle" class="nb-svg-title">ticket-api :8091</text>
      <text x="320" y="100" text-anchor="middle" class="nb-svg-sub">create_ticket</text>
      <rect x="456" y="50" rx="12" width="240" height="70" fill="#dbeafe" stroke="#3b82f6"/>
      <text x="576" y="82" text-anchor="middle" class="nb-svg-title">PostgreSQL</text>
      <text x="576" y="100" text-anchor="middle" class="nb-svg-sub">OPS-xxxxxxxx + audit</text>
    </svg>`;
}
