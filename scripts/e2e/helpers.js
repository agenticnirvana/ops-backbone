const { expect } = require('@playwright/test');

async function login(page, { email = 'operator@agentops.local', password = 'operator123' } = {}) {
  await page.goto('/');
  await page.fill('#email', email);
  await page.fill('#password', password);
  await page.click('#login-form button[type="submit"]');
  await expect(page.locator('#app-screen')).toBeVisible({ timeout: 20000 });
  await expect(page.locator('#login-screen')).toBeHidden();
  await expect(page.locator('#page-title')).toHaveText(/Operations/i, { timeout: 25000 });
  await expect(page.locator('body')).toHaveAttribute('data-boot', '1', { timeout: 25000 });
  await expect(page.locator('#oss-tools-grid')).toHaveAttribute('data-ready', '1', { timeout: 15000 });
  await expect(page.locator('#oss-tools-grid .tool-tile').first()).toBeAttached();
}

async function openSection(page, section) {
  await page.getByTestId(`nav-${section}`).click();
  await expect(page.locator(`#sec-${section}`)).not.toHaveClass(/hidden/);
}

async function openTab(page, tabId) {
  await page.locator(`.workspace-tab[data-tab="${tabId}"]`).click();
  await expect(page.locator(`#tab-${tabId}`)).not.toHaveClass(/hidden/);
}

async function selectDesign(page, id) {
  await page.getByTestId(`design-${id}`).click();
  await expect(page.getByTestId(`design-${id}`)).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#oss-tools-grid')).toHaveAttribute('data-ready', '1');
  await expect(page.getByTestId('explore-vector')).toBeAttached();
}

const SCREENS = [
  { section: 'operations', tabs: ['ops-incident', 'ops-pipeline', 'ops-multi', 'ops-mcp', 'ops-response'] },
  { section: 'mcp', tabs: ['mcp-playground', 'mcp-skills', 'mcp-vs-skills'] },
  { section: 'simulation', tabs: ['auto-change', 'auto-opa', 'auto-history', 'auto-logs'] },
  { section: 'guardrails', tabs: ['grd-overview', 'grd-audit', 'grd-editor'] },
  { section: 'ingestion', tabs: ['ing-pipeline', 'ing-status', 'ing-jobs'] },
  { section: 'learning', tabs: ['learn-notebook', 'learn-designs', 'learn-bookmarks', 'learn-notes', 'learn-highlights'] },
  { section: 'observability', tabs: ['obs-simulator', 'obs-alert', 'obs-logs', 'obs-metrics'] },
  { section: 'evaluation', tabs: ['eval-analytics', 'eval-trace', 'eval-gate', 'eval-tools'] },
  { section: 'governance', tabs: ['gov-overview', 'gov-pipelines', 'gov-promotions', 'gov-controls', 'gov-github'] },
  { section: 'actions', tabs: ['act-detail', 'act-list'] },
];

const EXPLORE_ROLES = ['vector', 'logs', 'metrics', 'dashboards', 'llmops', 'evals'];

const DESIGNS = {
  d1: {
    open: /Open Chroma/i,
    consolePath: '/static/tools/chroma.html',
    metricsHref: /localhost:9090/,
    metricsForbidden: /8428/,
  },
  d2: {
    open: /Open Weaviate/i,
    consolePath: '/static/tools/weaviate.html',
    metricsHref: /8428\/vmui/,
    metricsForbidden: /9090/,
  },
  d3: {
    open: /Open OpenSearch/i,
    consolePath: 'localhost:5602',
    metricsHref: /localhost:3001/,
    metricsForbidden: /9009|8428/,
  },
};

module.exports = { login, openSection, openTab, selectDesign, SCREENS, EXPLORE_ROLES, DESIGNS };
