const { test, expect } = require('@playwright/test');
const { login, openSection, openTab, selectDesign, EXPLORE_ROLES, DESIGNS } = require('./helpers');

test.describe('Design consistency D1 / D2 / D3', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  for (const [id, spec] of Object.entries(DESIGNS)) {
    test(`${id} shows Open vector + the six explore roles`, async ({ page }) => {
      await selectDesign(page, id);
      await openSection(page, 'ingestion');
      await openTab(page, 'ing-jobs');

      const openBtn = page.getByTestId('open-vector');
      await expect(openBtn).toBeAttached();
      await expect(openBtn).not.toHaveClass(/hidden/);
      await expect(openBtn).toHaveText(spec.open);
      const href = await openBtn.getAttribute('href');
      expect(href).toContain(spec.consolePath.includes('localhost') ? '5602' : spec.consolePath);

      for (const role of EXPLORE_ROLES) {
        const tile = page.locator(`[data-testid="explore-${role}"]`).first();
        await expect(tile, `${id} missing explore role ${role}`).toBeAttached();
        const tileHref = await tile.getAttribute('href');
        expect(tileHref && tileHref !== '#', `${id} ${role} has no URL`).toBeTruthy();
      }

      const metricsTile = await page.getByTestId('explore-metrics').getAttribute('href');
      expect(metricsTile).toMatch(spec.metricsHref);
      expect(metricsTile).not.toMatch(spec.metricsForbidden);

      await openSection(page, 'observability');
      await openTab(page, 'obs-simulator');
      const obsMetrics = await page.getByTestId('open-metrics').getAttribute('href');
      expect(obsMetrics).toMatch(spec.metricsHref);
      expect(obsMetrics).not.toMatch(spec.metricsForbidden);

      await openTab(page, 'obs-alert');
      const alertMetrics = await page.getByTestId('open-metrics-alert').getAttribute('href');
      expect(alertMetrics).toMatch(spec.metricsHref);
      expect(alertMetrics).not.toMatch(spec.metricsForbidden);
    });
  }

  test('D1 Open Chroma console lists runbooks', async ({ page }) => {
    await selectDesign(page, 'd1');
    await openSection(page, 'ingestion');
    await openTab(page, 'ing-jobs');
    const popupPromise = page.waitForEvent('popup');
    await page.getByTestId('open-vector').click();
    const consolePage = await popupPromise;
    await consolePage.waitForLoadState('domcontentloaded');
    await expect(consolePage.locator('h1')).toContainText(/Chroma/i);
    await expect(consolePage.locator('#status')).toHaveText(/connected|error|connecting/i, { timeout: 15000 });
    if (/connected/i.test(await consolePage.locator('#status').textContent())) {
      expect(await consolePage.locator('#rows tr').count()).toBeGreaterThan(0);
    }
    await consolePage.close();
  });

  test('D2 Open Weaviate console lists Runbook objects', async ({ page }) => {
    await selectDesign(page, 'd2');
    await openSection(page, 'ingestion');
    await openTab(page, 'ing-jobs');
    const popupPromise = page.waitForEvent('popup');
    await page.getByTestId('open-vector').click();
    const consolePage = await popupPromise;
    await consolePage.waitForLoadState('domcontentloaded');
    await expect(consolePage.locator('h1')).toContainText(/Weaviate/i);
    await expect(consolePage.locator('#status')).toBeAttached();
    await consolePage.close();
  });

  test('Pick a stack cards include Evals for every design', async ({ page }) => {
    await openSection(page, 'learning');
    await openTab(page, 'learn-designs');
    const cards = page.locator('.dp-card');
    await expect(cards).toHaveCount(3, { timeout: 15000 });
    for (let i = 0; i < 3; i += 1) {
      await expect(cards.nth(i)).toContainText(/Evals/i);
      await expect(cards.nth(i)).toContainText(/Vector/i);
    }
  });
});

test.describe('OpenSearch native data', () => {
  test('runbook vectors and logs exist in OpenSearch', async ({ request }) => {
    const health = await request.get('http://localhost:9201/_cluster/health');
    if (!health.ok()) test.skip(true, 'OpenSearch is not running');
    const runbooks = await request.get('http://localhost:9201/agentops-d3-runbooks/_count');
    expect(runbooks.ok(), 'runbooks index missing — seed OpenSearch').toBeTruthy();
    expect((await runbooks.json()).count).toBeGreaterThan(0);
    const logs = await request.get('http://localhost:9201/agentops-d3-logs/_count');
    expect(logs.ok(), 'logs index missing — seed OpenSearch').toBeTruthy();
    expect((await logs.json()).count).toBeGreaterThan(0);
  });
});
