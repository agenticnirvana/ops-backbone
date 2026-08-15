const THEME_STORAGE_KEY = 'agentops-theme';

function getTheme() {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  return stored === 'dark' ? 'dark' : 'light';
}

function applyTheme(theme) {
  const next = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem(THEME_STORAGE_KEY, next);
  syncThemeControls(next);
}

function syncThemeControls(theme) {
  document.querySelectorAll('.theme-switch-btn').forEach((btn) => {
    const active = btn.dataset.themeValue === theme;
    btn.classList.toggle('is-active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
}

function initTheme() {
  applyTheme(getTheme());
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
