/** Shared design loader — each pack lives in designs/{id}/stack.js */

const ARCH_LIVE_ID = 'd2';
const ARCH_EXPLORE_ROLES = ['vector', 'logs', 'metrics', 'dashboards', 'llmops', 'evals'];
const ARCH_TOOLS_UP = ['d2', 'd3'];
const ARCH_DESIGN_KEY = 'agentops-active-design';

const ARCH_DESIGNS = Object.assign({}, window.ARCH_DESIGN_PACKS || {});
if (!ARCH_DESIGNS.d1 || !ARCH_DESIGNS.d2 || !ARCH_DESIGNS.d3) {
  console.warn('Design packs missing — load designs/d1/stack.js, d2/stack.js, d3/stack.js before designs.js');
} else {
  Object.values(ARCH_DESIGNS).forEach((d) => {
    const roles = (d.explore || []).map((x) => x.role);
    ARCH_EXPLORE_ROLES.forEach((role) => {
      if (!roles.includes(role)) console.warn(`Design ${d.id} missing explore role: ${role}`);
    });
  });
}

function getArchDesignId() {
  try {
    const id = localStorage.getItem(ARCH_DESIGN_KEY);
    if (id && ARCH_DESIGNS[id]) return id;
  } catch (_) { /* ignore */ }
  return ARCH_LIVE_ID || 'd2';
}

function getArchDesign(id) {
  const resolved = id || getArchDesignId();
  return ARCH_DESIGNS[resolved] || ARCH_DESIGNS[ARCH_LIVE_ID] || ARCH_DESIGNS.d2 || ARCH_DESIGNS.d1 || null;
}

function archFill(text, design) {
  const d = design || getArchDesign();
  if (text == null || !d) return text == null ? '' : String(text);
  const map = {
    vector: d.vector,
    logs: d.logs,
    metrics: d.metrics,
    dashboards: d.dashboards,
    llmops: d.llmops,
    evals: d.evals || d.llmops,
    traces: d.traces,
    policy: d.policy,
    safety: d.safety,
    vectorUrl: d.vectorUrl || 'in-console explorer',
    ingestTab: d.ingestTab,
    name: d.name,
    stack: d.stack,
    ci: d.ci,
    policyConsole: d.policyConsole || d.policy,
    logsQuery: d.logsQuery || d.logs,
    alertFiring: d.alertFiring || d.metrics,
    vectorApiList: d.vectorApiList || d.vector,
    vectorApiQuery: d.vectorApiQuery || 'query',
  };
  return String(text).replace(/\{(\w+)\}/g, (_, k) => (map[k] != null ? map[k] : `{${k}}`));
}

function applyArchCopy(root) {
  const scope = root || document;
  scope.querySelectorAll('[data-arch-copy]').forEach((el) => {
    const tpl = el.getAttribute('data-arch-copy');
    if (tpl == null) return;
    const filled = archFill(tpl);
    if (/<[a-z][\s\S]*>/i.test(filled)) el.innerHTML = filled;
    else el.textContent = filled;
  });
}

function isArchDesignLive(id) {
  return (id || getArchDesignId()) === ARCH_LIVE_ID;
}

function isArchToolsUp(id) {
  return (typeof ARCH_TOOLS_UP !== 'undefined' ? ARCH_TOOLS_UP : [ARCH_LIVE_ID])
    .includes(id || getArchDesignId());
}

function setArchDesignId(id) {
  if (!ARCH_DESIGNS[id]) return getArchDesign();
  try { localStorage.setItem(ARCH_DESIGN_KEY, id); } catch (_) { /* ignore */ }
  window.dispatchEvent(new CustomEvent('agentops-design-change', { detail: { id } }));
  return ARCH_DESIGNS[id];
}

function archDesignCompareHtml(highlight) {
  const rows = [
    ['Vector / RAG', 'vector'],
    ['Logs', 'logs'],
    ['Metrics', 'metrics'],
    ['Dashboards', 'dashboards'],
    ['LLM ops', 'llmops'],
    ['Evals / CI', 'evals'],
    ['Traces', 'traces'],
    ['Policy', 'policy'],
    ['Safety', 'safety'],
  ];
  return `
    <div class="design-compare-table">
      <table>
        <thead>
          <tr>
            <th></th>
            ${Object.values(ARCH_DESIGNS).map((d) => `<th${d.id === getArchDesignId() ? ' class="on"' : ''}>${d.name}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          ${rows.map(([label, key]) => `
            <tr class="${highlight === key ? 'hl' : ''}">
              <th>${label}</th>
              ${Object.values(ARCH_DESIGNS).map((d) => `<td${d.id === getArchDesignId() ? ' class="on"' : ''}>${d[key]}</td>`).join('')}
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

function archPickIcon(kind) {
  const paths = {
    vector: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
    logs: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
    metrics: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    llmops: '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z"/>',
    evals: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  };
  return `<span class="dp-orb dp-orb-${kind}" aria-hidden="true"><span class="dp-orb-shine"></span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">${paths[kind] || ''}</svg></span>`;
}

function archPickHtml() {
  const active = getArchDesignId();
  const specs = [
    { key: 'vector', label: 'Vector' },
    { key: 'logs', label: 'Logs' },
    { key: 'metrics', label: 'Metrics' },
    { key: 'llmops', label: 'LLM ops' },
    { key: 'evals', label: 'Evals' },
  ];
  return `
    <div class="dp-stage">
      <div class="dp-aurora" aria-hidden="true">
        <i class="dp-blob dp-blob-a"></i>
        <i class="dp-blob dp-blob-b"></i>
        <i class="dp-blob dp-blob-c"></i>
      </div>
      <header class="dp-hero">
        <p class="dp-kicker">Reference architectures</p>
        <h2 class="dp-title">Pick a stack</h2>
        <p class="dp-sub">Same five phases. Three landlords. D2 is live on this laptop.</p>
      </header>
      <div class="dp-grid">
        ${Object.values(ARCH_DESIGNS).map((d, i) => `
          <article class="dp-card tone-${d.id}${d.id === active ? ' on' : ''}${d.id === ARCH_LIVE_ID ? ' is-live' : ''}" style="--dp-i:${i}">
            <div class="dp-card-glass"></div>
            <div class="dp-card-head">
              <span class="dp-num">0${d.n}</span>
              ${d.id === ARCH_LIVE_ID
                ? '<span class="dp-pill live">Live</span>'
                : '<span class="dp-pill soon">Compare</span>'}
            </div>
            <h3>${d.name}</h3>
            <p class="dp-tag">${d.tagline}</p>
            <p class="dp-blurb">${d.pick}</p>
            <div class="dp-specs">
              ${specs.map((s) => `
                <div class="dp-spec">
                  ${archPickIcon(s.key)}
                  <div>
                    <small>${s.label}</small>
                    <strong>${d[s.key]}</strong>
                  </div>
                </div>`).join('')}
            </div>
            <button type="button" class="dp-cta" data-arch-design="${d.id}">
              <span>${d.id === active ? 'Selected' : `Use ${d.name}`}</span>
              <i></i>
            </button>
            ${d.id !== ARCH_LIVE_ID ? `<code class="dp-deploy">${d.deploy}</code>` : '<span class="dp-deploy ghost">Running on :8080</span>'}
          </article>`).join('')}
      </div>
      <button type="button" class="dp-compare-toggle" data-dp-compare>Full comparison</button>
      <div class="dp-compare-wrap hidden" data-dp-compare-panel>
        ${archDesignCompareHtml()}
      </div>
    </div>`;
}

function archPickBind(root) {
  if (!root) return;
  root.querySelector('[data-dp-compare]')?.addEventListener('click', (e) => {
    const panel = root.querySelector('[data-dp-compare-panel]');
    const on = panel?.classList.toggle('hidden') === false;
    e.currentTarget.classList.toggle('on', on);
    e.currentTarget.textContent = on ? 'Hide comparison' : 'Full comparison';
  });
  root.querySelectorAll('.dp-card').forEach((card) => {
    card.addEventListener('pointermove', (ev) => {
      const r = card.getBoundingClientRect();
      const x = ((ev.clientX - r.left) / r.width - 0.5) * 8;
      const y = ((ev.clientY - r.top) / r.height - 0.5) * -8;
      card.style.setProperty('--rx', `${y}deg`);
      card.style.setProperty('--ry', `${x}deg`);
    });
    card.addEventListener('pointerleave', () => {
      card.style.setProperty('--rx', '0deg');
      card.style.setProperty('--ry', '0deg');
    });
  });
}
