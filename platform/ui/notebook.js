/** Design 1 — notebook-style Learning reader */

const NB_STORAGE = {
  progress: 'agentops-nb-progress',
  bookmarks: 'agentops-nb-bookmarks',
  notes: 'agentops-nb-notes',
  highlights: 'agentops-nb-highlights',
  settings: 'agentops-nb-settings',
};

const NB_CHAPTERS = [
  {
    id: 'front',
    n: 0,
    title: 'Front matter',
    color: 'ink',
    pages: [
      { id: 'cover', title: 'Cover', kind: 'cover' },
      { id: 'toc', title: 'Table of contents', kind: 'toc' },
      { id: 'arch-full', title: 'Architecture map' },
      { id: 'pick-stack', title: 'Pick a stack' },
    ],
  },
  {
    id: 'ingestion',
    n: 1,
    title: 'Ingestion',
    color: 'teal',
    question: 'What does the agent actually see?',
    pages: [
      { id: 'ing-splash', title: 'Chapter 1', kind: 'chapter' },
      { id: 'ing-arch', title: 'Ingestion architecture' },
      { id: 'vdb-what', title: 'What is a vector database?' },
      { id: 'vdb-why', title: 'Why agents need vectors' },
      { id: 'vdb-sql', title: 'Why your SQL DB is not enough' },
      { id: 'vdb-viz', title: 'See it: nearest neighbors' },
      { id: 'vdb-tools', title: 'OSS tools vs cloud' },
      { id: 'vdb-chroma', title: 'Chroma in Design 1' },
    ],
  },
  {
    id: 'orchestration',
    n: 2,
    title: 'Orchestration',
    color: 'indigo',
    question: 'How does the agent reason and call tools?',
    pages: [
      { id: 'orch-splash', title: 'Chapter 2', kind: 'chapter' },
      { id: 'orch-arch', title: 'Orchestration architecture' },
      { id: 'orch-langgraph', title: 'LangGraph is the brain' },
      { id: 'orch-mcp', title: 'MCP vs skills' },
    ],
  },
  {
    id: 'evaluation',
    n: 3,
    title: 'Evaluation',
    color: 'violet',
    question: 'How do you trust it?',
    pages: [
      { id: 'eval-splash', title: 'Chapter 3', kind: 'chapter' },
      { id: 'eval-arch', title: 'Eval architecture' },
      { id: 'eval-trace', title: 'Traces, evals, OTEL' },
    ],
  },
  {
    id: 'guardrails',
    n: 4,
    title: 'Guardrails',
    color: 'amber',
    question: 'What stops a bad action?',
    pages: [
      { id: 'grd-splash', title: 'Chapter 4', kind: 'chapter' },
      { id: 'grd-arch', title: 'Guardrail architecture' },
      { id: 'grd-opa', title: 'OPA + HITL' },
    ],
  },
  {
    id: 'action',
    n: 5,
    title: 'Action',
    color: 'green',
    question: 'What happens after yes?',
    pages: [
      { id: 'act-splash', title: 'Chapter 5', kind: 'chapter' },
      { id: 'act-arch', title: 'Action architecture' },
      { id: 'act-ticket', title: 'Tickets & audit' },
    ],
  },
];

const NB_FLAT = NB_CHAPTERS.flatMap((ch) => ch.pages.map((p) => ({ ...p, chapter: ch })));

const NB_VDB_POINTS = [
  { id: 'checkout-redis-pool', x: 78, y: 62, label: 'redis pool', tokens: 'redis pool exhausted checkout' },
  { id: 'db-pool-exhausted', x: 126, y: 98, label: 'db pool', tokens: 'postgres pool connections database' },
  { id: 'payment-high-cpu', x: 268, y: 198, label: 'cpu', tokens: 'cpu saturation payment' },
  { id: 'auth-error-spike', x: 332, y: 58, label: 'auth', tokens: 'auth 401 jwt errors' },
  { id: 'kafka-consumer-lag', x: 214, y: 44, label: 'kafka', tokens: 'kafka lag consumer' },
  { id: 'api-gateway-latency', x: 304, y: 148, label: 'latency', tokens: 'gateway p99 latency' },
];

const NB_TOOLS = [
  { kind: 'oss', name: 'Chroma', vibe: 'Local-first Python. What this course actually runs.', tag: 'this laptop' },
  { kind: 'oss', name: 'Qdrant', vibe: 'Rust, filters, the production darling for many teams.', tag: 'self-host' },
  { kind: 'oss', name: 'Weaviate', vibe: 'Hybrid search + modules. Graph-ish energy.', tag: 'hybrid' },
  { kind: 'oss', name: 'Milvus / Zilliz', vibe: 'Scale-out. GPU optional. Big index energy.', tag: 'scale' },
  { kind: 'oss', name: 'pgvector', vibe: 'Postgres extension. One DB if you already live there.', tag: 'sql-native' },
  { kind: 'oss', name: 'LanceDB / FAISS', vibe: 'Embedded / library-first. Bring your own server.', tag: 'library' },
  { kind: 'cloud', name: 'Pinecone', vibe: 'Serverless vectors. Fastest “just ship RAG”.', tag: 'managed' },
  { kind: 'cloud', name: 'AWS OpenSearch k-NN', vibe: 'Already on AWS? Hybrid BM25 + vectors.', tag: 'aws' },
  { kind: 'cloud', name: 'Azure AI Search', vibe: 'Enterprise + semantic ranker.', tag: 'azure' },
  { kind: 'cloud', name: 'Vertex Vector Search', vibe: 'GCP-native, huge indexes.', tag: 'gcp' },
  { kind: 'cloud', name: 'MongoDB Atlas Vector', vibe: 'If Mongo is already home.', tag: 'atlas' },
  { kind: 'cloud', name: 'Elasticsearch vector', vibe: 'Logs + vectors in one cluster.', tag: 'elastic' },
];

const NB_THEMES = [
  { id: 'notebook', name: 'Notebook', blurb: 'Stickers, lined paper, doodles' },
  { id: 'book', name: 'Hardcover', blurb: 'Two-page spread · Apple Books' },
  { id: 'kindle', name: 'Kindle', blurb: 'Paperwhite e-ink — flash, bezel, loc bar' },
  { id: 'magazine', name: 'Editorial', blurb: 'Medium / magazine spreads' },
  { id: 'stories', name: 'Stories', blurb: 'Card reels — skip the essay' },
];

const nbState = {
  index: 0,
  flipping: false,
  paper: 'cream',
  font: 'm',
  theme: 'book',
  read: new Set(),
  focus: false,
  last: 0,
};

function nbSaveSettings() {
  nbSaveJson(NB_STORAGE.settings, {
    paper: nbState.paper,
    font: nbState.font,
    focus: nbState.focus,
    theme: nbState.theme,
  });
}

function nbLoadJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || '') || fallback;
  } catch (_) {
    return fallback;
  }
}

function nbSaveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function nbLoadState() {
  const settings = nbLoadJson(NB_STORAGE.settings, {});
  nbState.paper = settings.paper || 'cream';
  nbState.font = settings.font || 'm';
  nbState.focus = !!settings.focus;
  nbState.theme = settings.theme || 'book';
  const progress = nbLoadJson(NB_STORAGE.progress, {});
  if (typeof progress.index === 'number') nbState.index = Math.min(progress.index, NB_FLAT.length - 1);
  nbState.read = new Set(progress.read || []);
  nbState.last = typeof progress.last === 'number' ? progress.last : nbState.index;
}

function nbSaveProgress() {
  nbSaveJson(NB_STORAGE.progress, {
    index: nbState.index,
    last: nbState.last,
    read: [...nbState.read],
  });
}

function nbBookmarks() {
  return nbLoadJson(NB_STORAGE.bookmarks, []);
}

function nbToggleBookmark(pageId) {
  const list = nbBookmarks();
  const i = list.indexOf(pageId);
  if (i >= 0) list.splice(i, 1);
  else list.push(pageId);
  nbSaveJson(NB_STORAGE.bookmarks, list);
  return list.includes(pageId);
}

function nbNotesMap() {
  return nbLoadJson(NB_STORAGE.notes, {});
}

function nbSaveNote(pageId, text) {
  const notes = nbNotesMap();
  if (text.trim()) notes[pageId] = text;
  else delete notes[pageId];
  nbSaveJson(NB_STORAGE.notes, notes);
}

function nbHighlightsMap() {
  return nbLoadJson(NB_STORAGE.highlights, {});
}

function nbAddHighlight(pageId, text, color) {
  const snippet = String(text || '').trim().slice(0, 280);
  if (!snippet) return;
  const map = nbHighlightsMap();
  const list = map[pageId] || [];
  if (list.some((h) => h.text === snippet)) return;
  list.push({ text: snippet, color: color || 'yellow', ts: Date.now() });
  map[pageId] = list;
  nbSaveJson(NB_STORAGE.highlights, map);
}

function nbRemoveHighlight(pageId, text) {
  const map = nbHighlightsMap();
  map[pageId] = (map[pageId] || []).filter((h) => h.text !== text);
  if (!map[pageId].length) delete map[pageId];
  nbSaveJson(NB_STORAGE.highlights, map);
}

function nbPageIndex(id) {
  return NB_FLAT.findIndex((p) => p.id === id);
}

function nbCurrent() {
  return NB_FLAT[nbState.index] || NB_FLAT[0];
}

function nbPercent() {
  return Math.round((nbState.read.size / Math.max(1, NB_FLAT.length)) * 100);
}

function nbMinsLeft() {
  return Math.max(1, Math.round((NB_FLAT.length - nbState.index) * 1.4));
}

function nbEsc(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function nbApplyMarks(html, pageId) {
  const list = nbHighlightsMap()[pageId] || [];
  let out = html;
  list.forEach((h) => {
    const safe = h.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    out = out.replace(new RegExp(safe, 'i'), `<mark class="nb-hl nb-hl-${h.color}">$&</mark>`);
  });
  return out;
}

function nbPageHtml(page) {
  const renderers = {
    cover: nbCoverHtml,
    toc: nbTocHtml,
    chapter: nbChapterSplashHtml,
    'arch-full': nbArchFullHtml,
    'pick-stack': nbPickStackHtml,
    'ing-arch': nbIngArchHtml,
    'orch-arch': nbOrchArchHtml,
    'eval-arch': nbEvalArchHtml,
    'grd-arch': nbGrdArchHtml,
    'act-arch': nbActArchHtml,
    'vdb-what': nbVdbWhatHtml,
    'vdb-why': nbVdbWhyHtml,
    'vdb-sql': nbVdbSqlHtml,
    'vdb-viz': nbVdbVizHtml,
    'vdb-tools': nbVdbToolsHtml,
    'vdb-chroma': nbVdbChromaHtml,
    'orch-langgraph': nbOrchHtml,
    'orch-mcp': nbMcpHtml,
    'eval-trace': nbEvalHtml,
    'grd-opa': nbGuardHtml,
    'act-ticket': nbActionHtml,
  };
  const fn = renderers[page.id] || renderers[page.kind];
  return fn ? fn(page) : `<h2>${page.title}</h2><p>Coming soon.</p>`;
}

function nbCoverHtml() {
  const last = NB_FLAT[nbState.last];
  const resume = nbState.last > 0 && last
    ? `<button type="button" class="nb-cover-cta ghost" data-nb-goto="${last.id}">Continue · ${last.chapter.title} · ${last.title}</button>`
    : '';
  return `
    <div class="nb-cover">
      <p class="nb-kicker">Design 1 · Field notes</p>
      <h1>The AgentOps<br>Notebook</h1>
      <p class="nb-cover-sub">Five phases. One stack. Zero vibes-based production.</p>
      <div class="nb-sticker-row">
        <span class="nb-sticker pink">annotated</span>
        <span class="nb-sticker yellow">dog-eared</span>
        <span class="nb-sticker mint">open book</span>
      </div>
      <p class="nb-hand">start with the architecture map, then Ch.1 → vector databases.</p>
      <div class="nb-cover-actions">
        <button type="button" class="nb-cover-cta" data-nb-goto="arch-full">See the map →</button>
        <button type="button" class="nb-cover-cta ghost" data-nb-goto="pick-stack">Pick a stack</button>
        ${resume}
      </div>
      <p class="nb-keys-hint">← → turn pages · B bookmark · / search · H highlight · F focus</p>
    </div>`;
}

function nbTocHtml() {
  return `
    <h2 class="nb-serif">Contents</h2>
    <p class="nb-lede">Tap a chapter. Bookmark later. This is a book, not a wiki dump.</p>
    <ol class="nb-toc">
      ${NB_CHAPTERS.filter((c) => c.n > 0).map((c) => `
        <li>
          <button type="button" class="nb-toc-row" data-nb-goto="${c.pages[0].id}">
            <span class="nb-toc-num">${String(c.n).padStart(2, '0')}</span>
            <span>
              <strong>${c.title}</strong>
              <small>${c.question}</small>
            </span>
            <span class="nb-toc-pages">${c.pages.length}p</span>
          </button>
        </li>`).join('')}
    </ol>`;
}

function nbChapterSplashHtml(page) {
  const ch = page.chapter;
  return `
    <div class="nb-chapter-splash nb-chapter-${ch.color}">
      <span class="nb-kicker">Chapter ${ch.n}</span>
      <h1 class="nb-serif">${ch.title}</h1>
      <p class="nb-lede">${ch.question}</p>
      <ul class="nb-chapter-list">
        ${ch.pages.filter((p) => p.kind !== 'chapter').map((p) => `
          <li><button type="button" data-nb-goto="${p.id}">${p.title}</button></li>`).join('')}
      </ul>
    </div>`;
}

function nbArchFullHtml() {
  const d = typeof getArchDesign === 'function' ? getArchDesign() : { name: 'Design 1', stack: 'Chroma + Loki + Prometheus + Langfuse', id: 'd1' };
  const chips = typeof ARCH_DESIGNS === 'object'
    ? Object.values(ARCH_DESIGNS).map((x) => `
        <button type="button" class="nb-chip${x.id === d.id ? ' active' : ''}" data-arch-design="${x.id}">${x.name}</button>`).join('')
    : '';
  return `
    <p class="nb-kicker">Front matter · map</p>
    <h2 class="nb-serif">The whole machine</h2>
    <p class="nb-lede">Same five phases. Different landlords. Toggle a design — the board swaps tools. Live stack on this laptop is Design 1.</p>
    <div class="nb-viz-toolbar">${chips}</div>
    ${typeof nbArchBoard === 'function' ? nbArchBoard(d.id) : ''}
    ${typeof archDesignCompareHtml === 'function' ? archDesignCompareHtml() : ''}
    ${d.id === 'd1' && typeof nbFig === 'function' ? nbFig('architecture-diagram.png', 'Official Design 1 architecture — tap to zoom') : ''}
    <p class="nb-hand">LangGraph + HITL stay. Vector / logs / metrics / LLM ops / evals change.</p>`;
}

function nbPickStackHtml() {
  return typeof archPickHtml === 'function' ? archPickHtml() : '<p>Pick a stack</p>';
}

function nbIngArchHtml() {
  return `
    <p class="nb-kicker">Ch.1 · Ingestion · architecture</p>
    <h2 class="nb-serif">Two pipes, one brain</h2>
    <p class="nb-lede">Knowledge (runbooks → Chroma) and signals (alerts / logs / metrics) land <em>before</em> LangGraph runs.</p>
    ${typeof nbIngestPipeSvg === 'function' ? nbIngestPipeSvg() : ''}
    ${typeof nbFig === 'function' ? nbFig('step-01b-runbook-ingestion.png', 'Live UI: runbook ingestion pipeline') : ''}
    ${typeof nbFig === 'function' ? nbFig('step-01-ingestion-observability.png', 'Observability: alerts, Loki, Prometheus') : ''}
    <button type="button" class="nb-cta" data-nb-jump="ingestion" data-tab="ing-pipeline">Open live pipeline →</button>`;
}

function nbOrchArchHtml() {
  return `
    <p class="nb-kicker">Ch.2 · Orchestration · architecture</p>
    <h2 class="nb-serif">LangGraph in the middle</h2>
    <p class="nb-lede">Same graph, three skins: standalone, multi-agent, MCP tools over HTTP.</p>
    ${typeof nbOrchSvg === 'function' ? nbOrchSvg() : ''}
    ${typeof nbFig === 'function' ? nbFig('step-02-agent-orchestration.png', 'Operations: agent run pipeline') : ''}
    <button type="button" class="nb-cta" data-nb-jump="operations" data-tab="ops-incident">Run it live →</button>`;
}

function nbEvalArchHtml() {
  return `
    <p class="nb-kicker">Ch.3 · Evaluation · architecture</p>
    <h2 class="nb-serif">Trace, score, gate</h2>
    <p class="nb-lede">If retrieval misses <code>checkout-redis-pool</code>, CI should fail — not your on-call.</p>
    ${typeof nbEvalSvg === 'function' ? nbEvalSvg() : ''}
    ${typeof archDesignCompareHtml === 'function' ? archDesignCompareHtml('llmops') : ''}
    ${typeof nbFig === 'function' ? nbFig('step-03-langfuse-trace.png', 'Langfuse trace in the platform') : ''}
    ${typeof nbFig === 'function' ? nbFig('step-04-mlflow-evals.png', 'MLflow eval gate') : ''}
    <button type="button" class="nb-cta" data-nb-jump="evaluation" data-tab="eval-gate">Open eval gate →</button>`;
}

function nbGrdArchHtml() {
  return `
    <p class="nb-kicker">Ch.4 · Guardrails · architecture</p>
    <h2 class="nb-serif">Policy, then a human</h2>
    <p class="nb-lede">OPA decides allow/deny. LangGraph waits. Nobody restarts prod on a vibe.</p>
    ${typeof nbGuardSvg === 'function' ? nbGuardSvg() : ''}
    ${typeof archDesignCompareHtml === 'function' ? archDesignCompareHtml('policy') : ''}
    ${typeof nbFig === 'function' ? nbFig('step-05-hitl-opa-guardrails.png', 'HITL + OPA in the change run') : ''}
    <button type="button" class="nb-cta" data-nb-jump="simulation" data-tab="auto-change">Open HITL →</button>`;
}

function nbActArchHtml() {
  return `
    <p class="nb-kicker">Ch.5 · Action · architecture</p>
    <h2 class="nb-serif">Tickets are the exam</h2>
    <p class="nb-lede">Approve → ticket-api → Postgres <code>OPS-xxxxxxxx</code>. Who said yes, against which runbook.</p>
    ${typeof nbActionSvg === 'function' ? nbActionSvg() : ''}
    ${typeof nbFig === 'function' ? nbFig('step-06-ticket-action.png', 'Ticket record after HITL') : ''}
    <button type="button" class="nb-cta" data-nb-jump="actions" data-tab="act-list">See tickets →</button>`;
}

function nbVdbWhatHtml() {
  return `
    <p class="nb-kicker">Ch.1 · Ingestion · 01</p>
    <h2 class="nb-serif">What is a vector database?</h2>
    <p class="nb-lede">A vector DB stores <em>meaning</em>, not rows. Text becomes a list of numbers (an embedding). Similar meaning → nearby numbers. Search = “who’s closest?”</p>
    <div class="nb-tldr">
      <strong>tl;dr</strong>
      <p>SQL finds exact strings. Vectors find <em>vibes that match the incident</em> — even if the runbook never used the same words.</p>
    </div>
    <div class="nb-formula">
      <div class="nb-formula-card">
        <span>1</span>
        <p><strong>Chunk</strong> runbook markdown into bite-size passages.</p>
      </div>
      <div class="nb-formula-card">
        <span>2</span>
        <p><strong>Embed</strong> each chunk (Design 1: MiniLM, 384 numbers).</p>
      </div>
      <div class="nb-formula-card">
        <span>3</span>
        <p><strong>Index</strong> those vectors so nearest-neighbor is fast.</p>
      </div>
      <div class="nb-formula-card">
        <span>4</span>
        <p><strong>Query</strong> the alert text → top-k similar runbooks.</p>
      </div>
    </div>
    <div class="nb-embed-strip" aria-hidden="true">
      <span>embedding</span>
      ${Array.from({ length: 24 }, (_, i) => `<i style="--h:${30 + ((i * 37) % 70)}%"></i>`).join('')}
      <span>384-d</span>
    </div>
    <aside class="nb-sticky rotate-1">
      embedding = GPS coords for a sentence in “meaning space”
    </aside>
    ${typeof nbSqlVsVecSvg === 'function' ? nbSqlVsVecSvg() : ''}
    ${typeof nbRagLoopSvg === 'function' ? nbRagLoopSvg() : ''}
    <p>When checkout is dying with “Redis pool exhausted”, you don’t grep for that exact phrase. You drop the alert into the same space and walk to the nearest procedure: <code>checkout-redis-pool</code>.</p>`;
}

function nbVdbWhyHtml() {
  return `
    <p class="nb-kicker">Ch.1 · Ingestion · 02</p>
    <h2 class="nb-serif">Why agents need this</h2>
    <p class="nb-lede">LLMs don’t remember your runbooks. If you paste the whole wiki, they hallucinate and you pay for tokens. RAG = retrieve the 3 pages that matter, then reason.</p>
    <div class="nb-hot-take">
      <span>hot take</span>
      <p>Without a vector index, your “SRE agent” is a chatbot with opinions. With one, it’s grounded in <em>your</em> procedures.</p>
    </div>
    <ul class="nb-why-list">
      <li><strong>Grounding.</strong> Capstone success = retrieve <code>checkout-redis-pool</code>, not invent a restart.</li>
      <li><strong>Language drift.</strong> Alert says “max clients”. Runbook says “connection pool”. Vectors still match.</li>
      <li><strong>Scale.</strong> 12 runbooks today, 1,200 tomorrow. Same query path.</li>
      <li><strong>Eval.</strong> You can test recall: did the right ID come back? That’s MLflow later.</li>
    </ul>
    <div class="nb-compare-mini">
      <div>
        <h4>No vector DB</h4>
        <p>Agent reads alert text → guesses a fix → maybe mentions Redis.</p>
      </div>
      <div>
        <h4>With vector DB</h4>
        <p>Agent retrieves the runbook → cites it → HITL sees the source.</p>
      </div>
    </div>`;
}

function nbVdbSqlHtml() {
  return `
    <p class="nb-kicker">Ch.1 · Ingestion · 03</p>
    <h2 class="nb-serif">Why existing DBs aren’t fit</h2>
    <p class="nb-lede">Postgres is elite at transactions. It’s mid at “find the procedure that <em>feels like</em> this outage.”</p>
    <div class="nb-flip-cards">
      <article>
        <h4>Relational (Postgres)</h4>
        <p>Great for tickets, users, HITL audit. Search is <code>WHERE title ILIKE '%redis%'</code> — misses synonyms, paraphrases, messy alerts.</p>
      </article>
      <article>
        <h4>Keyword (Elastic / Loki)</h4>
        <p>Great for logs. BM25 loves exact tokens. Runbooks are prose, not inverted-index poetry.</p>
      </article>
      <article>
        <h4>Object stores (S3)</h4>
        <p>Great for files. Not a query engine. You’d still embed + index somewhere.</p>
      </article>
      <article class="nb-win">
        <h4>Vector DB</h4>
        <p>Built for high-dim similarity (HNSW / IVF). That’s the retrieval primitive RAG needs.</p>
      </article>
    </div>
    <p class="nb-hand">you still <em>keep</em> Postgres — tickets live there. vectors are a new index type, not a religion.</p>
    <div class="nb-quiz" data-nb-quiz>
      <p><strong>Pop quiz.</strong> Alert: “checkout 5xx · connection starvation”. Runbook title: “Redis pool exhaustion”. What fails first?</p>
      <button type="button" data-quiz="sql">SQL <code>ILIKE '%starvation%'</code></button>
      <button type="button" data-quiz="vec">Vector nearest-neighbor</button>
      <p class="nb-quiz-answer hidden" data-answer="sql">Correct. Keyword miss. Vectors still land near “pool / Redis / checkout”.</p>
      <p class="nb-quiz-answer hidden" data-answer="vec">Vectors should <em>succeed</em>. The trap is keyword search.</p>
    </div>`;
}

function nbVdbVizHtml() {
  return `
    <p class="nb-kicker">Ch.1 · Ingestion · 04</p>
    <h2 class="nb-serif">See it: nearest neighbors</h2>
    <p class="nb-lede">Tiny 2D sketch of embedding space. Real MiniLM is 384-D — same idea, more axes. Drag the red query. Toggle vector vs keyword.</p>
    <div class="nb-viz-toolbar">
      <button type="button" class="nb-chip active" data-viz-mode="vector">Vector search</button>
      <button type="button" class="nb-chip" data-viz-mode="keyword">Keyword / SQL</button>
    </div>
    <div class="nb-embed-viz" id="nb-embed-viz">
      <svg viewBox="0 0 400 260" role="img" aria-label="Embedding space sketch">
        <defs>
          <radialGradient id="nbGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#2dd4bf" stop-opacity="0.35"/>
            <stop offset="100%" stop-color="#2dd4bf" stop-opacity="0"/>
          </radialGradient>
        </defs>
        <rect width="400" height="260" rx="16" fill="rgba(15,23,42,0.03)"/>
        <g id="nb-nn-lines"></g>
        <circle class="nb-query-halo" cx="88" cy="70" r="54" fill="url(#nbGlow)"/>
        ${NB_VDB_POINTS.map((p) => `
          <g class="nb-pt" data-id="${p.id}" data-x="${p.x}" data-y="${p.y}" data-tokens="${p.tokens}" transform="translate(${p.x} ${p.y})">
            <circle r="8" />
            <text y="22" text-anchor="middle">${p.label}</text>
          </g>`).join('')}
        <g class="nb-query" id="nb-query" transform="translate(88 70)" style="cursor:grab">
          <circle r="8" fill="#f43f5e"/>
          <text y="-14" text-anchor="middle">query</text>
        </g>
      </svg>
      <p class="nb-viz-caption" id="nb-viz-caption">Drag the query. Vector mode lights nearest neighbors. Keyword only hits titles containing “redis”.</p>
    </div>
    <p class="nb-hand">closer = more similar. that’s RAG. keyword search is a spelling bee.</p>`;
}

function nbVdbToolsHtml() {
  return `
    <p class="nb-kicker">Ch.1 · Ingestion · 05</p>
    <h2 class="nb-serif">OSS tools vs cloud</h2>
    <p class="nb-lede">Same job, different landlords. Design 1 picks <strong>Chroma</strong> so the whole course runs on your laptop.</p>
    <div class="nb-viz-toolbar" data-tool-filter>
      <button type="button" class="nb-chip active" data-tool-kind="all">All</button>
      <button type="button" class="nb-chip" data-tool-kind="oss">Open source</button>
      <button type="button" class="nb-chip" data-tool-kind="cloud">Cloud managed</button>
    </div>
    <div class="nb-tool-cards" id="nb-tool-cards">
      ${NB_TOOLS.map((t) => `
        <article class="nb-tool-card" data-kind="${t.kind}">
          <span class="nb-tool-tag">${t.tag}</span>
          <h4>${t.name}</h4>
          <p>${t.vibe}</p>
          <small>${t.kind === 'oss' ? 'self-host / OSS' : 'managed cloud'}</small>
        </article>`).join('')}
    </div>
    <aside class="nb-sticky rotate-neg">pgvector is the “I already have Postgres” move. Chroma is the “I want RAG today” move.</aside>
    <h3 class="nb-serif" style="font-size:1.2rem;margin-top:20px">This course’s three designs</h3>
    ${typeof archDesignCompareHtml === 'function' ? archDesignCompareHtml('vector') : ''}`;
}

function nbVdbChromaHtml() {
  return `
    <p class="nb-kicker">Ch.1 · Ingestion · 06</p>
    <h2 class="nb-serif">Chroma in Design 1</h2>
    <p class="nb-lede">Markdown runbooks → chunk ~512 tokens → MiniLM 384-d → Chroma collection. Service: <code>runbook-ingestion :8092</code>.</p>
    <ol class="nb-steps">
      <li>Seed files live in <code>agent/rag/runbooks/</code></li>
      <li>Ingestion API embeds + upserts (token on writes)</li>
      <li>Agent / RAG MCP calls <code>retrieve_runbooks</code></li>
      <li>Eval gate checks the ID came back</li>
    </ol>
    ${typeof archDesignCompareHtml === 'function' ? archDesignCompareHtml('vector') : ''}
    <p>Open the live index when you’re done highlighting. Explorer label follows the design switcher — live data is still Chroma until D2/D3 profiles are up.</p>
    ${typeof nbFig === 'function' ? nbFig('step-01b-runbook-ingestion.png', 'Chroma explorer in the platform UI') : ''}
    <button type="button" class="nb-cta" data-nb-jump="ingestion" data-tab="ing-jobs">Open vector explorer →</button>`;
}

function nbOrchHtml() {
  return `
    <p class="nb-kicker">Ch.2 · Orchestration</p>
    <h2 class="nb-serif">LangGraph is the brain</h2>
    <p class="nb-lede">Standalone = one graph. Multi-agent = supervisor + workers. MCP mode = same reasoning, tools over HTTP.</p>
    <ul class="nb-why-list">
      <li><strong>Standalone</strong> — classify → RAG → logs → metrics → recommend → HITL → execute.</li>
      <li><strong>Multi</strong> — specialist workers, <code>delegation_events</code> in the UI tree.</li>
      <li><strong>MCP</strong> — tools hosted on :8081 / :8082 / :8083 with Basic Auth.</li>
    </ul>
    <button type="button" class="nb-cta" data-nb-jump="operations" data-tab="ops-incident">Run a pipeline →</button>`;
}

function nbMcpHtml() {
  return `
    <p class="nb-kicker">Ch.2 · Orchestration</p>
    <h2 class="nb-serif">MCP vs skills</h2>
    <p class="nb-lede">MCP = live tools with side effects. Skills = SKILL.md + scripts in agentregistry. Different jobs, same catalog.</p>
    <div class="nb-compare-mini">
      <div><h4>MCP</h4><p>query_logs, get_metrics, create_ticket — runtime, auth, OPA.</p></div>
      <div><h4>Skills</h4><p>Eval helpers, checklists, offline heuristics.</p></div>
    </div>
    <button type="button" class="nb-cta" data-nb-jump="mcp" data-tab="mcp-vs-skills">Open the decision guide →</button>`;
}

function nbEvalHtml() {
  return `
    <p class="nb-kicker">Ch.3 · Evaluation</p>
    <h2 class="nb-serif">Traces, evals, OTEL</h2>
    <p class="nb-lede">Each design teaches one eval tool in depth — traces, experiments, and LLM-as-judge in the same UI. OTEL stays for infra traces.</p>
    <p>If retrieval misses <code>checkout-redis-pool</code>, CI should fail — not your on-call.</p>
    <button type="button" class="nb-cta" data-nb-jump="evaluation" data-tab="eval-gate">Open eval gate →</button>`;
}

function nbGuardHtml() {
  return `
    <p class="nb-kicker">Ch.4 · Guardrails</p>
    <h2 class="nb-serif">OPA + HITL</h2>
    <p class="nb-lede">Rego decides allow/deny. LangGraph <code>interrupt_before</code> waits for a human. Policy MCP lets you preview without tickets.</p>
    <button type="button" class="nb-cta" data-nb-jump="mcp" data-tab="mcp-playground">Try Policy MCP →</button>`;
}

function nbActionHtml() {
  return `
    <p class="nb-kicker">Ch.5 · Action</p>
    <h2 class="nb-serif">Tickets &amp; the paper trail</h2>
    <p class="nb-lede">Approve → <code>create_ticket</code> → Postgres <code>OPS-xxxxxxxx</code>. That’s the exam: who said yes, against which runbook.</p>
    <button type="button" class="nb-cta" data-nb-jump="actions" data-tab="act-list">See tickets →</button>`;
}

function renderNotebook(opts) {
  const root = document.getElementById('nb-root');
  if (!root) return;
  const peelSnap = opts && opts.peelEl;
  const peelDir = opts && opts.peelDir;
  const page = nbCurrent();
  const ch = page.chapter;
  const bookmarked = nbBookmarks().includes(page.id);
  const note = nbNotesMap()[page.id] || '';
  nbState.read.add(page.id);
  if (page.kind !== 'cover') nbState.last = nbState.index;
  nbSaveProgress();

  root.innerHTML = `
    <div class="nb-desk nb-theme-${nbState.theme} nb-paper-${nbState.paper} nb-font-${nbState.font} nb-motion-${ch.id}${nbState.focus ? ' nb-focus' : ''}">
      <div class="nb-toolbar">
        <div class="nb-progress-wrap" title="${nbPercent()}% pages marked read">
          <div class="nb-progress" style="width:${nbPercent()}%"></div>
        </div>
        <span class="nb-progress-label">${nbPercent()}%</span>
        <span class="nb-eta">${nbMinsLeft()}m left</span>
        <button type="button" class="nb-tool-btn nb-theme-chip" data-nb-themes title="Reading theme">${nbThemeLabel()}</button>
        <button type="button" class="nb-tool-btn" data-nb-toc title="Contents">☰</button>
        <button type="button" class="nb-tool-btn" data-nb-search title="Search">⌕</button>
        <button type="button" class="nb-tool-btn${bookmarked ? ' on' : ''}" id="nb-bookmark-btn" title="Bookmark (B)">🔖</button>
        <button type="button" class="nb-tool-btn${nbState.focus ? ' on' : ''}" data-nb-focus title="Focus (F)">▣</button>
        <button type="button" class="nb-tool-btn" data-nb-paper title="Paper">▤</button>
        <button type="button" class="nb-tool-btn" data-nb-font title="Type size">Aa</button>
      </div>
      <div class="nb-kindle-device">
        <div class="nb-kindle-status">
          <span>${ch.title}</span>
          <span class="nb-kindle-clock">${nbKindleClock()}</span>
          <span>100%</span>
        </div>
        <div class="nb-book" id="nb-book">
        <div class="nb-spine"></div>
        <aside class="nb-left">
          <p class="nb-left-kicker">${ch.n ? `Ch.${ch.n}` : 'Front'}</p>
          <h3>${ch.title}</h3>
          <ol class="nb-left-toc">
            ${ch.pages.map((p) => `
              <li class="${p.id === page.id ? 'active' : ''} ${nbState.read.has(p.id) ? 'read' : ''}">
                <button type="button" data-nb-goto="${p.id}">${p.title}</button>
              </li>`).join('')}
          </ol>
          <div class="nb-doodle">read · dog-ear · scribble</div>
        </aside>
        <div class="nb-spread" id="nb-flip-stage">
          <div class="nb-page-left" aria-hidden="true">${nbLeftLeafHtml()}</div>
          <div class="nb-crease"></div>
          <div class="nb-right-wrap">
            <div class="nb-right nb-arrive" id="nb-stage">
              <div class="nb-paper-lines"></div>
              <div class="nb-gutter">${nbState.index + 1}</div>
              <article class="nb-article" id="nb-article">${nbApplyMarks(nbPageHtml(page), page.id)}</article>
              <label class="nb-note-field">
                <span>Margin note</span>
                <textarea id="nb-note" rows="2" placeholder="scribble something…"></textarea>
              </label>
            </div>
            <div class="nb-ribbon${bookmarked ? ' dropped' : ''}" id="nb-ribbon"></div>
          </div>
        </div>
        <button type="button" class="nb-hotspot left" id="nb-prev" aria-label="Previous page"></button>
        <button type="button" class="nb-hotspot right" id="nb-next" aria-label="Next page"></button>
        <div class="nb-eink-grain" aria-hidden="true"></div>
      </div>
        <div class="nb-kindle-footer">
          <div class="nb-kindle-ticks"><i style="width:${Math.round(((nbState.index + 1) / NB_FLAT.length) * 100)}%"></i></div>
          <span>Loc ${nbState.index + 1} of ${NB_FLAT.length} · ${nbPercent()}%</span>
        </div>
        <button type="button" class="nb-kindle-home" data-nb-goto="toc" aria-label="Kindle home"></button>
      </div>
      <div class="nb-pager">
        <button type="button" class="nb-page-btn" id="nb-prev-btn"${nbState.index === 0 ? ' disabled' : ''}>← prev</button>
        <span>${nbState.index + 1} / ${NB_FLAT.length}</span>
        <button type="button" class="nb-page-btn" id="nb-next-btn"${nbState.index === NB_FLAT.length - 1 ? ' disabled' : ''}>next →</button>
      </div>
      <div class="nb-hl-bar hidden" id="nb-hl-bar">
        <span>Highlight</span>
        <button type="button" data-hl="yellow" title="Yellow">●</button>
        <button type="button" data-hl="pink" title="Pink">●</button>
        <button type="button" data-hl="mint" title="Mint">●</button>
      </div>
      <div class="nb-overlay hidden" id="nb-overlay"></div>
    </div>`;

  const ta = root.querySelector('#nb-note');
  if (ta) ta.value = note;
  bindNotebook(root);
  if (page.id === 'vdb-viz') bindEmbedViz(root);
  if (page.id === 'vdb-tools') bindToolFilter(root);
  if (peelSnap && peelDir) nbPlayPeel(root, peelSnap, peelDir);
}

function nbThemeLabel() {
  const t = NB_THEMES.find((x) => x.id === nbState.theme);
  return t ? t.name : 'Theme';
}

function nbLeftLeafHtml() {
  if (nbState.index <= 0) {
    return `<div class="nb-leaf-cover"><p>AgentOps</p><span>field notes</span></div>`;
  }
  const prev = NB_FLAT[nbState.index - 1];
  return `
    <p class="nb-leaf-kicker">${prev.chapter.title}</p>
    <h4>${prev.title}</h4>
    <p class="nb-leaf-hint">${nbState.index} / ${NB_FLAT.length}</p>`;
}

function nbKindleClock() {
  try {
    return new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  } catch (_) {
    return '';
  }
}

function nbPlayPeel(root, snap, dir) {
  if (nbState.theme === 'kindle') {
    nbPlayKindleFlash(root, snap);
    return;
  }
  const wrap = root.querySelector('.nb-right-wrap') || root.querySelector('#nb-flip-stage');
  if (!wrap || !snap) {
    nbState.flipping = false;
    return;
  }
  snap.id = 'nb-peel';
  snap.classList.add(dir > 0 ? 'nb-peeling-fwd' : 'nb-peeling-back');
  const glare = document.createElement('div');
  glare.className = 'nb-curl-glare';
  snap.appendChild(glare);
  const shade = document.createElement('div');
  shade.className = 'nb-under-shade';
  wrap.appendChild(shade);
  wrap.appendChild(snap);
  const stage = root.querySelector('#nb-stage');
  stage?.classList.add(dir > 0 ? 'nb-arrive-fwd' : 'nb-arrive-back');
  let finished = false;
  const done = () => {
    if (finished) return;
    finished = true;
    snap.remove();
    shade.remove();
    nbState.flipping = false;
  };
  snap.addEventListener('animationend', done, { once: true });
  window.setTimeout(done, 980);
}

function nbPlayKindleFlash(root, snap) {
  const screen = root.querySelector('#nb-book') || root.querySelector('.nb-kindle-device');
  const wrap = root.querySelector('.nb-right-wrap');
  if (!screen) {
    nbState.flipping = false;
    return;
  }
  if (snap && wrap) {
    snap.id = 'nb-peel';
    snap.classList.add('nb-eink-ghost');
    wrap.appendChild(snap);
  }
  const flash = document.createElement('div');
  flash.className = 'nb-eink-flash';
  screen.appendChild(flash);
  let finished = false;
  const done = () => {
    if (finished) return;
    finished = true;
    flash.remove();
    snap?.remove();
    nbState.flipping = false;
  };
  flash.addEventListener('animationend', done, { once: true });
  window.setTimeout(done, 480);
}

function bindNotebook(root) {
  const go = (delta) => nbTurn(delta);
  root.querySelector('#nb-prev')?.addEventListener('click', () => go(-1));
  root.querySelector('#nb-next')?.addEventListener('click', () => go(1));
  root.querySelector('#nb-prev-btn')?.addEventListener('click', () => go(-1));
  root.querySelector('#nb-next-btn')?.addEventListener('click', () => go(1));
  root.querySelector('#nb-bookmark-btn')?.addEventListener('click', () => {
    const on = nbToggleBookmark(nbCurrent().id);
    root.querySelector('#nb-bookmark-btn')?.classList.toggle('on', on);
    root.querySelector('#nb-ribbon')?.classList.toggle('dropped', on);
  });
  root.querySelector('[data-nb-paper]')?.addEventListener('click', () => {
    nbState.paper = nbState.paper === 'cream' ? 'lined' : nbState.paper === 'lined' ? 'night' : 'cream';
    nbSaveSettings();
    renderNotebook();
  });
  root.querySelector('[data-nb-font]')?.addEventListener('click', () => {
    nbState.font = nbState.font === 's' ? 'm' : nbState.font === 'm' ? 'l' : 's';
    nbSaveSettings();
    renderNotebook();
  });
  root.querySelector('[data-nb-focus]')?.addEventListener('click', () => {
    nbState.focus = !nbState.focus;
    nbSaveSettings();
    renderNotebook();
  });
  root.querySelector('[data-nb-themes]')?.addEventListener('click', () => nbOpenThemes(root));
  root.querySelector('[data-nb-toc]')?.addEventListener('click', () => nbOpenToc(root));
  root.querySelector('[data-nb-search]')?.addEventListener('click', () => nbOpenSearch(root));
  let noteTimer;
  root.querySelector('#nb-note')?.addEventListener('input', (e) => {
    window.clearTimeout(noteTimer);
    noteTimer = window.setTimeout(() => nbSaveNote(nbCurrent().id, e.target.value), 350);
  });
  root.querySelectorAll('[data-nb-goto]').forEach((btn) => {
    btn.addEventListener('click', () => nbJump(btn.dataset.nbGoto));
  });
  root.querySelectorAll('[data-arch-design]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (typeof setArchDesignId === 'function') setArchDesignId(btn.dataset.archDesign);
      else renderNotebook();
    });
  });
  root.querySelectorAll('[data-nb-jump]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (window.switchSection) window.switchSection(btn.dataset.nbJump, btn.dataset.tab || undefined);
    });
  });
  root.querySelectorAll('[data-nb-quiz]').forEach((quiz) => {
    quiz.querySelectorAll('[data-quiz]').forEach((btn) => {
      btn.addEventListener('click', () => {
        quiz.querySelectorAll('.nb-quiz-answer').forEach((a) => a.classList.add('hidden'));
        quiz.querySelector(`[data-answer="${btn.dataset.quiz}"]`)?.classList.remove('hidden');
        quiz.querySelectorAll('[data-quiz]').forEach((b) => b.classList.toggle('picked', b === btn));
      });
    });
  });
  bindHighlights(root);
  bindSwipe(root);
  bindFigures(root);
  if (typeof archPickBind === 'function') archPickBind(root);
}

function bindFigures(root) {
  root.querySelectorAll('.nb-figure img').forEach((img) => {
    img.addEventListener('click', () => {
      nbOverlay(root, `
        <div class="nb-lightbox" data-nb-close>
          <img src="${img.src}" alt="${img.alt || ''}">
        </div>`);
    });
  });
}

function nbOpenThemes(root) {
  const el = nbOverlay(root, `
    <div class="nb-sheet">
      <header><h3>Reading theme</h3><button type="button" data-nb-close>✕</button></header>
      <p class="muted">Hardcover if you want a book. Kindle for e-ink. Stories if you don’t want a wall of text.</p>
      <div class="nb-theme-grid">
        ${NB_THEMES.map((t) => `
          <button type="button" class="nb-theme-pick${t.id === nbState.theme ? ' on' : ''}" data-theme="${t.id}">
            <strong>${t.name}</strong>
            <small>${t.blurb}</small>
          </button>`).join('')}
      </div>
    </div>`);
  el?.querySelectorAll('[data-theme]').forEach((btn) => {
    btn.addEventListener('click', () => {
      nbState.theme = btn.dataset.theme;
      nbSaveSettings();
      renderNotebook();
    });
  });
}

function bindHighlights(root) {
  const article = root.querySelector('#nb-article');
  const bar = root.querySelector('#nb-hl-bar');
  if (!article || !bar) return;
  article.addEventListener('mouseup', () => {
    const sel = window.getSelection();
    const text = sel && String(sel.toString() || '').trim();
    if (!text || text.length < 3) {
      bar.classList.add('hidden');
      return;
    }
    bar.classList.remove('hidden');
  });
  bar.querySelectorAll('[data-hl]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const sel = window.getSelection();
      const text = sel && String(sel.toString() || '').trim();
      if (text) nbAddHighlight(nbCurrent().id, text, btn.dataset.hl);
      bar.classList.add('hidden');
      window.getSelection()?.removeAllRanges();
      renderNotebook();
    });
  });
  article.querySelectorAll('mark.nb-hl').forEach((mark) => {
    mark.title = 'Click to remove highlight';
    mark.addEventListener('click', () => {
      nbRemoveHighlight(nbCurrent().id, mark.textContent);
      renderNotebook();
    });
  });
}

function bindSwipe(root) {
  const stage = root.querySelector('#nb-stage');
  if (!stage) return;
  let x0 = 0;
  const start = (x) => { x0 = x; };
  const end = (x) => {
    const dx = x - x0;
    const sel = window.getSelection();
    if (sel && String(sel.toString() || '').trim()) return;
    if (dx < -56) nbTurn(1);
    else if (dx > 56) nbTurn(-1);
  };
  stage.addEventListener('touchstart', (e) => start(e.changedTouches[0].clientX), { passive: true });
  stage.addEventListener('touchend', (e) => end(e.changedTouches[0].clientX));
  stage.addEventListener('mousedown', (e) => {
    if (e.target.closest('button, textarea, input, a, .nb-query')) return;
    start(e.clientX);
  });
  stage.addEventListener('mouseup', (e) => {
    if (e.target.closest('button, textarea, input, a, .nb-query')) return;
    end(e.clientX);
  });
}

function nbOverlay(root, html) {
  const el = root.querySelector('#nb-overlay');
  if (!el) return null;
  el.innerHTML = html;
  el.classList.remove('hidden');
  el.querySelector('[data-nb-close]')?.addEventListener('click', () => el.classList.add('hidden'));
  el.addEventListener('click', (e) => {
    if (e.target === el) el.classList.add('hidden');
  });
  return el;
}

function nbOpenToc(root) {
  const el = nbOverlay(root, `
    <div class="nb-sheet">
      <header><h3>Contents</h3><button type="button" data-nb-close>✕</button></header>
      ${NB_CHAPTERS.map((c) => `
        <section>
          <h4>${c.n ? `Ch.${c.n} ${c.title}` : c.title}</h4>
          ${c.pages.map((p) => `
            <button type="button" class="nb-toc-row" data-nb-goto="${p.id}">
              <span>${p.title}</span>
              ${nbBookmarks().includes(p.id) ? '<span>🔖</span>' : ''}
            </button>`).join('')}
        </section>`).join('')}
    </div>`);
  el?.querySelectorAll('[data-nb-goto]').forEach((btn) => {
    btn.addEventListener('click', () => nbJump(btn.dataset.nbGoto));
  });
}

function nbOpenSearch(root) {
  const el = nbOverlay(root, `
    <div class="nb-sheet">
      <header><h3>Find in notebook</h3><button type="button" data-nb-close>✕</button></header>
      <input id="nb-search-input" type="search" placeholder="vector, chroma, OPA…" autofocus>
      <div id="nb-search-hits"></div>
    </div>`);
  const input = el?.querySelector('#nb-search-input');
  const hits = el?.querySelector('#nb-search-hits');
  const run = () => {
    const q = (input.value || '').trim().toLowerCase();
    if (!q) {
      hits.innerHTML = '<p class="muted">Type to search titles + page text.</p>';
      return;
    }
    const found = NB_FLAT.filter((p) => {
      const hay = `${p.title} ${p.chapter.title} ${nbPageHtml(p)}`.replace(/<[^>]+>/g, ' ').toLowerCase();
      return hay.includes(q);
    }).slice(0, 12);
    hits.innerHTML = found.length
      ? found.map((p) => `<button type="button" class="nb-toc-row" data-nb-goto="${p.id}"><strong>${p.title}</strong><small>${p.chapter.title}</small></button>`).join('')
      : '<p class="muted">No hits.</p>';
    hits.querySelectorAll('[data-nb-goto]').forEach((btn) => {
      btn.addEventListener('click', () => nbJump(btn.dataset.nbGoto));
    });
  };
  input?.addEventListener('input', run);
  input?.focus();
  run();
}

function nbTurn(delta) {
  if (nbState.flipping) return;
  const next = nbState.index + delta;
  if (next < 0 || next >= NB_FLAT.length) return;
  const stage = document.getElementById('nb-stage');
  const snap = stage ? stage.cloneNode(true) : null;
  nbState.index = next;
  nbState.flipping = true;
  nbSaveProgress();
  renderNotebook({ peelEl: snap, peelDir: delta });
}

function nbJump(pageId) {
  const i = nbPageIndex(pageId);
  if (i < 0) return;
  nbState.index = i;
  renderNotebook();
}

function bindEmbedViz(root) {
  const svg = root.querySelector('#nb-embed-viz svg');
  const query = root.querySelector('#nb-query');
  const halo = root.querySelector('.nb-query-halo');
  const lines = root.querySelector('#nb-nn-lines');
  if (!svg || !query) return;
  let mode = 'vector';
  let qx = 88;
  let qy = 70;

  const toSvg = (evt) => {
    const pt = svg.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: qx, y: qy };
    const loc = pt.matrixTransform(ctm.inverse());
    return {
      x: Math.max(16, Math.min(384, loc.x)),
      y: Math.max(16, Math.min(244, loc.y)),
    };
  };

  const paint = () => {
    query.setAttribute('transform', `translate(${qx} ${qy})`);
    if (halo) {
      halo.setAttribute('cx', qx);
      halo.setAttribute('cy', qy);
    }
    root.querySelectorAll('[data-viz-mode]').forEach((b) => b.classList.toggle('active', b.dataset.vizMode === mode));
    const ranked = NB_VDB_POINTS
      .map((p) => ({ ...p, d: Math.hypot(p.x - qx, p.y - qy) }))
      .sort((a, b) => a.d - b.d);
    const vectorHits = new Set(ranked.slice(0, 2).map((p) => p.id));
    root.querySelectorAll('.nb-pt').forEach((g) => {
      const id = g.dataset.id || '';
      const tokens = g.dataset.tokens || '';
      const keywordHit = /\bredis\b/.test(tokens);
      const on = mode === 'vector' ? vectorHits.has(id) : keywordHit;
      g.classList.toggle('hit', on);
      g.classList.toggle('miss', !on);
    });
    if (lines) {
      lines.innerHTML = '';
      if (mode === 'vector') {
        ranked.slice(0, 2).forEach((p) => {
          const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          line.setAttribute('x1', qx);
          line.setAttribute('y1', qy);
          line.setAttribute('x2', p.x);
          line.setAttribute('y2', p.y);
          line.setAttribute('class', 'nb-nn-line');
          lines.appendChild(line);
        });
      }
    }
    const cap = root.querySelector('#nb-viz-caption');
    if (cap) {
      cap.textContent = mode === 'vector'
        ? `Nearest: ${ranked[0].label} + ${ranked[1].label}. Drag the query — neighbors update live.`
        : 'Keyword mode: only chunks whose tokens include “redis” light up. Synonyms go dark.';
    }
  };

  let dragging = false;
  query.addEventListener('pointerdown', (e) => {
    dragging = true;
    query.style.cursor = 'grabbing';
    query.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  query.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const loc = toSvg(e);
    qx = loc.x;
    qy = loc.y;
    paint();
  });
  query.addEventListener('pointerup', () => {
    dragging = false;
    query.style.cursor = 'grab';
  });
  root.querySelectorAll('[data-viz-mode]').forEach((btn) => {
    btn.addEventListener('click', () => {
      mode = btn.dataset.vizMode;
      paint();
    });
  });
  paint();
}

function bindToolFilter(root) {
  const cards = root.querySelectorAll('.nb-tool-card');
  root.querySelectorAll('[data-tool-kind]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const kind = btn.dataset.toolKind;
      root.querySelectorAll('[data-tool-kind]').forEach((b) => b.classList.toggle('active', b === btn));
      cards.forEach((c) => {
        c.classList.toggle('hidden', kind !== 'all' && c.dataset.kind !== kind);
      });
    });
  });
}

function renderNotebookBookmarks() {
  const el = document.getElementById('nb-bookmarks-body');
  if (!el) return;
  const ids = nbBookmarks();
  if (!ids.length) {
    el.innerHTML = '<div class="nb-empty card">No dog-ears yet. Open the notebook and tap 🔖 (or press B).</div>';
    return;
  }
  el.innerHTML = `
    <div class="nb-list card glossy-card">
      <h3>Bookmarks</h3>
      <ul>${ids.map((id) => {
        const p = NB_FLAT.find((x) => x.id === id);
        return `<li><button type="button" class="nb-toc-row" data-open="${id}"><strong>${p ? p.title : id}</strong><small>${p?.chapter?.title || ''}</small></button></li>`;
      }).join('')}</ul>
    </div>`;
  el.querySelectorAll('[data-open]').forEach((btn) => {
    btn.addEventListener('click', () => {
      nbJump(btn.dataset.open);
      if (window.switchSection) window.switchSection('learning', 'learn-notebook');
    });
  });
}

function renderNotebookNotes() {
  const el = document.getElementById('nb-notes-body');
  if (!el) return;
  const notes = nbNotesMap();
  const entries = Object.entries(notes);
  if (!entries.length) {
    el.innerHTML = '<div class="nb-empty card">Margin notes show up here. Scribble on any page.</div>';
    return;
  }
  el.innerHTML = `
    <div class="nb-list card glossy-card">
      <h3>Margin notes</h3>
      ${entries.map(([id, text]) => {
        const p = NB_FLAT.find((x) => x.id === id);
        return `<article class="nb-note-card"><h4>${p ? p.title : id}</h4><p>${nbEsc(text)}</p>
          <button type="button" class="btn-ghost btn-sm" data-open="${id}">Jump to page</button></article>`;
      }).join('')}
    </div>`;
  el.querySelectorAll('[data-open]').forEach((btn) => {
    btn.addEventListener('click', () => {
      nbJump(btn.dataset.open);
      if (window.switchSection) window.switchSection('learning', 'learn-notebook');
    });
  });
}

function renderNotebookHighlights() {
  const el = document.getElementById('nb-highlights-body');
  if (!el) return;
  const map = nbHighlightsMap();
  const rows = Object.entries(map).flatMap(([id, list]) => list.map((h) => ({ id, ...h })));
  if (!rows.length) {
    el.innerHTML = '<div class="nb-empty card">Select text on a page, then tap a highlight color. Click a mark to remove it.</div>';
    return;
  }
  el.innerHTML = `
    <div class="nb-list card glossy-card">
      <h3>Highlights</h3>
      ${rows.map((h) => {
        const p = NB_FLAT.find((x) => x.id === h.id);
        return `<article class="nb-note-card"><mark class="nb-hl nb-hl-${h.color}">${nbEsc(h.text)}</mark>
          <p class="muted">${p ? p.title : h.id}</p>
          <button type="button" class="btn-ghost btn-sm" data-open="${h.id}">Jump to page</button></article>`;
      }).join('')}
    </div>`;
  el.querySelectorAll('[data-open]').forEach((btn) => {
    btn.addEventListener('click', () => {
      nbJump(btn.dataset.open);
      if (window.switchSection) window.switchSection('learning', 'learn-notebook');
    });
  });
}

function initNotebookKeyboard() {
  if (window.__nbKeys) return;
  window.__nbKeys = true;
  document.addEventListener('keydown', (e) => {
    const learning = document.getElementById('sec-learning');
    if (!learning || learning.classList.contains('hidden')) return;
    const overlay = document.getElementById('nb-overlay');
    if (overlay && !overlay.classList.contains('hidden')) {
      if (e.key === 'Escape') overlay.classList.add('hidden');
      return;
    }
    if (e.target && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
      if (e.key === 'Escape') e.target.blur();
      return;
    }
    if (e.key === 'ArrowRight' || e.key === ' ') {
      e.preventDefault();
      nbTurn(1);
    }
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      nbTurn(-1);
    }
    if (e.key === 'b' || e.key === 'B') {
      nbToggleBookmark(nbCurrent().id);
      renderNotebook();
    }
    if (e.key === '/' && !e.metaKey && !e.ctrlKey) {
      e.preventDefault();
      const root = document.getElementById('nb-root');
      if (root) nbOpenSearch(root);
    }
    if (e.key === 'f' || e.key === 'F') {
      nbState.focus = !nbState.focus;
      nbSaveSettings();
      renderNotebook();
    }
    if (e.key === 'Escape') {
      document.getElementById('nb-overlay')?.classList.add('hidden');
    }
  });
}

function renderDesignsTab() {
  const el = document.getElementById('nb-designs-body');
  if (!el) return;
  el.innerHTML = typeof archPickHtml === 'function' ? archPickHtml() : '';
  if (typeof archPickBind === 'function') archPickBind(el);
  el.querySelectorAll('[data-arch-design]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (typeof setArchDesignId === 'function') setArchDesignId(btn.dataset.archDesign);
    });
  });
}

function bindTeachingHub() {
  const frame = document.getElementById('topic-slides-frame');
  const topics = document.getElementById('teach-topics');
  const present = document.getElementById('teach-present');
  const grids = {
    t1: document.getElementById('topic-slides-grid-t1'),
    t2: document.getElementById('topic-slides-grid-t2'),
  };
  const home = {
    t1: '/static/learn/topic-01-ingestion/index.html',
    t2: '/static/learn/topic-02-evals/index.html',
  };

  function showTopic(id) {
    topics?.querySelectorAll('.teach-topic').forEach((btn) => {
      const on = btn.dataset.topic === id;
      btn.classList.toggle('is-on', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    Object.entries(grids).forEach(([key, el]) => {
      if (!el) return;
      el.hidden = key !== id;
    });
    if (present) present.href = home[id] || home.t1;
    if (frame && home[id]) frame.src = home[id];
  }

  if (topics && !topics.dataset.bound) {
    topics.dataset.bound = '1';
    topics.addEventListener('click', (e) => {
      const btn = e.target.closest('.teach-topic');
      if (btn?.dataset.topic) showTopic(btn.dataset.topic);
    });
  }
  document.querySelectorAll('#topic-slides-grid-t1, #topic-slides-grid-t2').forEach((grid) => {
    if (grid.dataset.bound) return;
    grid.dataset.bound = '1';
    grid.addEventListener('click', (e) => {
      const a = e.target.closest('.topic-slide-card');
      if (!a || !frame || e.metaKey || e.ctrlKey) return;
      e.preventDefault();
      frame.src = a.getAttribute('href');
      if (present) present.href = a.getAttribute('href');
    });
  });
}

function initLearningSection(tabId) {
  nbLoadState();
  const tab = tabId || 'learn-slides';
  if (tab === 'learn-slides') {
    bindTeachingHub();
    return;
  }
  if (tab === 'learn-bookmarks') {
    renderNotebookBookmarks();
    return;
  }
  if (tab === 'learn-notes') {
    renderNotebookNotes();
    return;
  }
  if (tab === 'learn-highlights') {
    renderNotebookHighlights();
    return;
  }
  if (tab === 'learn-designs') {
    renderDesignsTab();
    return;
  }
  initNotebookKeyboard();
  renderNotebook();
}

if (!window.__nbDesignListener) {
  window.__nbDesignListener = true;
  window.addEventListener('agentops-design-change', () => {
    const learning = document.getElementById('sec-learning');
    if (!learning || learning.classList.contains('hidden')) return;
    const notebookOn = !document.getElementById('tab-learn-notebook')?.classList.contains('hidden');
    const designsOn = !document.getElementById('tab-learn-designs')?.classList.contains('hidden');
    if (notebookOn) renderNotebook();
    if (designsOn) renderDesignsTab();
  });
}
