const { test, expect } = require('@playwright/test');
const { login, openSection, openTab } = require('./helpers');

test.describe('Core features', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('operations incident form has Run Pipeline', async ({ page }) => {
    await openSection(page, 'operations');
    await openTab(page, 'ops-incident');
    await expect(page.locator('#run-pipeline-btn')).toBeAttached();
  });

  test('ingestion pipeline and explore native UIs card render', async ({ page }) => {
    await openSection(page, 'ingestion');
    await openTab(page, 'ing-pipeline');
    await expect(page.locator('#stack-explore-grid')).toBeAttached();
    await expect(page.locator('#stack-explore-grid .stack-explore-item').first()).toBeAttached();
    await openTab(page, 'ing-jobs');
    await expect(page.getByTestId('open-vector')).toBeAttached();
    await expect(page.getByTestId('open-vector')).not.toHaveClass(/hidden/);
  });

  test('observability alert flow panel is present', async ({ page }) => {
    await openSection(page, 'observability');
    await openTab(page, 'obs-simulator');
    await expect(page.locator('#alert-journey-track')).toBeAttached();
    await expect(page.locator('#obs-sim-preview')).toBeAttached();
    await expect(page.locator('#obs-sim-fire')).toBeAttached();
    await expect(page.locator('#obs-custom-use')).toBeAttached();
  });

  test('evaluation gate tab has run control', async ({ page }) => {
    await openSection(page, 'evaluation');
    await openTab(page, 'eval-gate');
    await expect(page.locator('#tab-eval-gate')).not.toHaveClass(/hidden/);
    await expect(page.locator('#eval-gate-run')).toBeAttached();
  });

  test('sidebar OSS tiles exist for all six roles', async ({ page }) => {
    expect(await page.locator('#oss-tools-grid .tool-tile').count()).toBeGreaterThanOrEqual(6);
    for (const role of ['vector', 'logs', 'metrics', 'dashboards', 'llmops', 'evals']) {
      await expect(page.getByTestId(`explore-${role}`)).toBeAttached();
    }
  });

  test('mcp playground and guardrails overview render', async ({ page }) => {
    await openSection(page, 'mcp');
    await openTab(page, 'mcp-playground');
    await expect(page.locator('#tab-mcp-playground')).not.toHaveClass(/hidden/);
    await openSection(page, 'guardrails');
    await openTab(page, 'grd-overview');
    await expect(page.locator('#tab-grd-overview')).not.toHaveClass(/hidden/);
  });

  test('governance section renders pipelines and github placeholders', async ({ page }) => {
    await openSection(page, 'governance');
    await openTab(page, 'gov-overview');
    await expect(page.locator('#tab-gov-overview')).not.toHaveClass(/hidden/);
    await expect(page.locator('#gov-posture-banner')).toBeVisible();
    await openTab(page, 'gov-github');
    await expect(page.locator('#gov-github-snippet')).toContainText('YOUR_GITHUB_ORG');
  });

  test('simulation and actions sections render', async ({ page }) => {
    await openSection(page, 'simulation');
    await openTab(page, 'auto-change');
    await expect(page.locator('#tab-auto-change')).not.toHaveClass(/hidden/);
    await openSection(page, 'actions');
    await openTab(page, 'act-list');
    await expect(page.locator('#tab-act-list')).not.toHaveClass(/hidden/);
  });
});
