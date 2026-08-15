const DECK_PAGES = window.DECK_PAGES || [
  { file: 'index.html', id: 'cover', n: '00', title: 'Cover' },
  { file: '01-ingestion-pipeline.html', id: 'ingest', n: '01', title: 'Ingestion' },
  { file: '02-rag.html', id: 'rag', n: '02', title: 'RAG' },
  { file: '03-vector-database.html', id: 'vdb', n: '03', title: 'Vector DB' },
  { file: '04-embeddings.html', id: 'emb', n: '04', title: 'Embeddings' },
  { file: '05-runbook-pipeline.html', id: 'parse', n: '05', title: 'Parse & store' },
];

const ICO = {
  layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
  db: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>',
  pulse: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
  spark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="m12 3-1.9 5.8H4.4l4.8 3.5-1.9 5.8L12 14.6l4.7 3.5-1.9-5.8 4.8-3.5h-6.1z"/></svg>',
  user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>',
  cpu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/></svg>',
  flow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
};

function mac(name, variant = 'teal', size = 'md') {
  return `<span class="mac-icon mac-icon-${size} mac-${variant}" aria-hidden="true"><span class="mac-icon-shine"></span>${ICO[name] || ICO.spark}</span>`;
}

function currentFile() {
  return location.pathname.split('/').pop() || 'index.html';
}

function pageIndex() {
  const i = DECK_PAGES.findIndex((p) => p.file === currentFile());
  return i < 0 ? 0 : i;
}

function renderChrome() {
  const here = DECK_PAGES[pageIndex()];
  const nav = document.getElementById('page-nav');
  if (nav) {
    nav.innerHTML = DECK_PAGES.map((p) =>
      `<a href="${p.file}" class="${p.file === here.file ? 'is-here' : ''}">${p.n} ${p.title}</a>`
    ).join('');
  }
  const title = document.getElementById('deck-page-title');
  if (title) title.textContent = here.title;
  document.querySelectorAll('[data-ico]').forEach((el) => {
    const [name, variant, size] = (el.dataset.ico || '').split(':');
    el.innerHTML = mac(name, variant || 'teal', size || 'md');
  });
}

function slides() {
  return [...document.querySelectorAll('.slide')];
}

function fragments(slide) {
  return [...slide.querySelectorAll('.frag')];
}

const state = { i: 0, f: 0 };

function show(i, f = 0, { hash = true } = {}) {
  const list = slides();
  if (!list.length) return;
  state.i = Math.max(0, Math.min(i, list.length - 1));
  const slide = list[state.i];
  list.forEach((el, n) => el.classList.toggle('is-on', n === state.i));
  const frags = fragments(slide);
  state.f = Math.max(0, Math.min(f, frags.length));
  frags.forEach((el, n) => el.classList.toggle('is-in', n < state.f));
  restartAnims(slide);
  updateHud();
  const notes = document.getElementById('notes');
  if (notes) notes.textContent = slide.dataset.notes || 'No speaker notes on this slide.';
  if (hash) history.replaceState(null, '', `#s${state.i + 1}`);
}

function restartAnims(slide) {
  slide.querySelectorAll('[data-restart]').forEach((el) => {
    el.style.animation = 'none';
    void el.offsetWidth;
    el.style.animation = '';
  });
}

function updateHud() {
  const list = slides();
  const dots = document.getElementById('dots');
  if (dots) {
    dots.innerHTML = list.map((_, n) =>
      `<button type="button" class="${n === state.i ? 'on' : ''}" data-go="${n}" aria-label="Slide ${n + 1}"></button>`
    ).join('');
  }
  const label = document.getElementById('slide-num');
  if (label) label.textContent = `${state.i + 1} / ${list.length}`;
  const bar = document.getElementById('progress');
  if (bar) bar.style.width = `${((state.i + 1) / list.length) * 100}%`;
}

function next() {
  const list = slides();
  const slide = list[state.i];
  const frags = fragments(slide);
  if (state.f < frags.length) { show(state.i, state.f + 1); return; }
  if (state.i < list.length - 1) { show(state.i + 1, 0); return; }
  const nxt = DECK_PAGES[pageIndex() + 1];
  if (nxt) location.href = nxt.file;
}

function prev() {
  if (state.f > 0) { show(state.i, state.f - 1); return; }
  if (state.i > 0) {
    const prevSlide = slides()[state.i - 1];
    show(state.i - 1, fragments(prevSlide).length);
    return;
  }
  const prv = DECK_PAGES[pageIndex() - 1];
  if (prv) location.href = prv.file;
}

function toggleFs() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen?.();
    document.body.classList.add('is-fs');
  } else {
    document.exitFullscreen?.();
    document.body.classList.remove('is-fs');
  }
}

function toggleNotes() {
  const notes = document.getElementById('notes');
  if (!notes) return;
  notes.hidden = !notes.hidden;
}

function parseHash() {
  const m = location.hash.match(/s(\d+)/i);
  return m ? Number(m[1]) - 1 : 0;
}

function bind() {
  renderChrome();
  document.getElementById('next-btn')?.addEventListener('click', next);
  document.getElementById('prev-btn')?.addEventListener('click', prev);
  document.getElementById('fs-btn')?.addEventListener('click', toggleFs);
  document.getElementById('notes-btn')?.addEventListener('click', toggleNotes);
  document.getElementById('dots')?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-go]');
    if (btn) show(Number(btn.dataset.go), 0);
  });
  document.querySelector('.stage')?.addEventListener('click', (e) => {
    if (e.target.closest('a,button')) return;
    next();
  });
  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') { e.preventDefault(); next(); }
    if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); prev(); }
    if (e.key === 'Home') show(0, 0);
    if (e.key === 'End') show(slides().length - 1, fragments(slides().at(-1)).length);
    if (e.key === 'f' || e.key === 'F') toggleFs();
    if (e.key === 'n' || e.key === 'N') toggleNotes();
  });
  document.addEventListener('fullscreenchange', () => {
    document.body.classList.toggle('is-fs', !!document.fullscreenElement);
  });
  show(parseHash(), 0, { hash: false });
}

document.addEventListener('DOMContentLoaded', bind);
