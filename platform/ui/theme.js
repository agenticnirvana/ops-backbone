const THEME_STORAGE_KEY = 'agentops-theme';
const THEME_SKY_MS = 2000;
const THEME_COMMIT_MS = 720;

let themeSkyTimer = null;
let themeSkyMidTimer = null;
let themeSkyBusy = false;

function getTheme() {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  return stored === 'dark' ? 'dark' : 'light';
}

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function currentThemeAttr() {
  const attr = document.documentElement.getAttribute('data-theme');
  return attr === 'dark' || attr === 'light' ? attr : getTheme();
}

function commitTheme(theme) {
  const next = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem(THEME_STORAGE_KEY, next);
  syncThemeControls(next);
}

function starFieldHtml() {
  const specs = [
    [6, 8], [14, 22], [22, 11], [31, 28], [38, 6], [47, 18], [55, 9],
    [63, 25], [71, 12], [79, 7], [86, 21], [93, 14], [11, 41], [27, 36],
    [42, 44], [58, 33], [74, 39], [88, 31], [18, 54], [34, 49], [51, 57],
    [67, 52], [82, 48], [8, 63], [45, 16], [96, 42], [3, 31], [60, 4],
  ];
  return specs.map(([left, top], i) => (
    `<span class="theme-star" style="left:${left}%;top:${top}%;animation-delay:${(i % 9) * 0.11}s"></span>`
  )).join('');
}

function ensureThemeSky() {
  let el = document.getElementById('theme-sky');
  if (el) return el;
  el = document.createElement('div');
  el.id = 'theme-sky';
  el.className = 'theme-sky';
  el.setAttribute('aria-hidden', 'true');
  el.innerHTML = `
    <div class="theme-sky-wash"></div>
    <div class="theme-stars">${starFieldHtml()}</div>
    <div class="theme-glow"></div>
    <div class="theme-sun-track">
      <div class="theme-sun">
        <span class="theme-sun-rays"></span>
        <span class="theme-sun-core"></span>
      </div>
    </div>
    <div class="theme-horizon"></div>
  `;
  document.body.appendChild(el);
  return el;
}

function playThemeSky(to) {
  const sky = ensureThemeSky();
  sky.classList.remove('is-rise', 'is-set', 'is-playing');
  void sky.offsetWidth;
  sky.classList.add('is-playing', to === 'light' ? 'is-rise' : 'is-set');
  document.documentElement.classList.add('theme-sky-active');
}

function finishThemeSky() {
  const sky = document.getElementById('theme-sky');
  sky?.classList.remove('is-playing', 'is-rise', 'is-set');
  document.documentElement.classList.remove('theme-sky-active');
  themeSkyBusy = false;
}

function applyTheme(theme, opts = {}) {
  const next = theme === 'dark' ? 'dark' : 'light';
  const current = currentThemeAttr();
  const shouldAnimate = opts.animate !== false
    && current !== next
    && document.body
    && !prefersReducedMotion();

  if (!shouldAnimate) {
    commitTheme(next);
    return;
  }
  if (themeSkyBusy) return;
  themeSkyBusy = true;
  clearTimeout(themeSkyTimer);
  clearTimeout(themeSkyMidTimer);
  playThemeSky(next);
  themeSkyMidTimer = setTimeout(() => commitTheme(next), THEME_COMMIT_MS);
  themeSkyTimer = setTimeout(finishThemeSky, THEME_SKY_MS);
}

function syncThemeControls(theme) {
  document.querySelectorAll('.theme-switch-btn').forEach((btn) => {
    const active = btn.dataset.themeValue === theme;
    btn.classList.toggle('is-active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
}

function initTheme() {
  applyTheme(getTheme(), { animate: false });
  document.querySelectorAll('.theme-switch-btn').forEach((btn) => {
    if (btn.dataset.themeBound) return;
    btn.dataset.themeBound = '1';
    btn.addEventListener('click', () => applyTheme(btn.dataset.themeValue));
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTheme);
} else {
  initTheme();
}

window.applyTheme = applyTheme;
window.initTheme = initTheme;
