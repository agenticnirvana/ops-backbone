const { test, expect } = require('@playwright/test');
const { login, openSection, openTab, selectDesign, DESIGNS, EXPLORE_ROLES } = require('./helpers');

async function expectReachable(request, url, label) {
  const target = url.startsWith('http') ? url : `http://localhost:8080${url}`;
  const res = await request.get(target, { timeout: 12000, maxRedirects: 5 });
  expect(res.status(), `${label} ${target}`).toBeLessThan(500);
}

test.describe('Recording-ready walkthrough', () => {
  test.describe.configure({ timeout: 90000 });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('theme switch light and dark', async ({ page }) => {
    await page.locator('[data-theme-value="dark"]').click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await page.locator('[data-theme-value="light"]').click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  });

  test('operations dropdowns and mode permutations', async ({ page }) => {
    await openSection(page, 'operations');
    await openTab(page, 'ops-incident');
    await expect(page.locator('#scenario option')).toHaveCount(await page.locator('#scenario option').count());
    expect(await page.locator('#scenario option').count()).toBeGreaterThan(1);
    expect(await page.locator('#service option').count()).toBeGreaterThan(0);
    for (const sev of ['P1', 'P2', 'P3']) {
      await page.selectOption('#severity', sev);
      await expect(page.locator('#severity')).toHaveValue(sev);
    }
    const modes = await page.locator('#agent-mode-select option').evaluateAll((opts) => opts.map((o) => o.value));
    expect(modes.length).toBeGreaterThanOrEqual(3);
    for (const mode of modes) {
      await page.selectOption('#agent-mode-select', mode);
      await expect(page.locator('#agent-mode-select')).toHaveValue(mode);
    }
    await expect(page.locator('#run-pipeline-btn')).toBeAttached();
  });

  test('observability walkthrough fills live pipeline and step breakdown', async ({ page }) => {
    await openSection(page, 'observability');
    await openTab(page, 'obs-simulator');
    await expect(page.locator('#alert-type-grid .alert-type-card').first()).toBeAttached({ timeout: 15000 });
    await expect(page.locator('#alert-journey-track .journey-node').first()).toBeAttached({ timeout: 25000 });
    expect(await page.locator('#alert-journey-track .journey-node').count()).toBeGreaterThan(5);
    await expect(page.locator('#obs-sim-step-select option').first()).toBeAttached();
    await expect(page.locator('#obs-sim-step-visual')).not.toHaveText(/Run a walkthrough/i);
    await expect(page.locator('#obs-sim-flow-status')).not.toHaveText(/Select an alert/i);

    for (const phase of ['all', 'ingestion', 'agent', 'guardrails', 'hitl']) {
      await page.locator(`.alert-phase-tab[data-phase="${phase}"]`).click();
      await expect(page.locator('#alert-journey-track .journey-node').first()).toBeAttached();
    }
    await page.locator('.alert-phase-tab[data-phase="all"]').click();

    const firstStep = await page.locator('#obs-sim-step-select option').first().getAttribute('value');
    const lastStep = await page.locator('#obs-sim-step-select option').last().getAttribute('value');
    await page.selectOption('#obs-sim-step-select', lastStep);
    await page.selectOption('#obs-sim-step-select', firstStep);
  });

  test('D3 live pipeline uses OpenSearch/Mimir not Chroma/Loki', async ({ page }) => {
    await selectDesign(page, 'd3');
    await openSection(page, 'observability');
    await openTab(page, 'obs-simulator');
    await expect(page.locator('#alert-journey-track .journey-node').first()).toBeAttached({ timeout: 25000 });
    const titles = await page.locator('#alert-journey-track .journey-node strong').allTextContents();
    const blob = titles.join(' | ');
    expect(blob).not.toMatch(/Chroma/i);
    expect(blob).not.toMatch(/Loki/i);
    expect(blob).toMatch(/OpenSearch/i);
    expect(blob).toMatch(/Mimir/i);
    const metricsHover = await page.getByTestId('explore-metrics').getAttribute('title');
    expect(metricsHover || '').toMatch(/METRICS/i);
    expect(metricsHover || '').toMatch(/not logs/i);
    const logsHover = await page.getByTestId('explore-logs').getAttribute('title');
    expect(logsHover || '').toMatch(/LOGS/i);
  });

  test('D1 live pipeline uses Chroma and Loki', async ({ page }) => {
    await selectDesign(page, 'd1');
    await openSection(page, 'observability');
    await openTab(page, 'obs-simulator');
    await expect(page.locator('#alert-journey-track .journey-node').first()).toBeAttached({ timeout: 25000 });
    const blob = (await page.locator('#alert-journey-track .journey-node strong').allTextContents()).join(' | ');
    expect(blob).toMatch(/Chroma/i);
    expect(blob).toMatch(/Loki/i);
    expect(blob).not.toMatch(/Weaviate/i);
  });

  test('D2 live pipeline uses Weaviate and Elasticsearch', async ({ page }) => {
    await selectDesign(page, 'd2');
    await openSection(page, 'observability');
    await openTab(page, 'obs-simulator');
    await expect(page.locator('#alert-journey-track .journey-node').first()).toBeAttached({ timeout: 25000 });
    const blob = (await page.locator('#alert-journey-track .journey-node strong').allTextContents()).join(' | ');
    expect(blob).toMatch(/Weaviate/i);
    expect(blob).toMatch(/Elasticsearch/i);
    expect(blob).not.toMatch(/Chroma/i);
    expect(blob).not.toMatch(/Loki/i);
  });

  test('custom alert fills live pipeline', async ({ page }) => {
    await openSection(page, 'observability');
    await openTab(page, 'obs-simulator');
    await expect(page.locator('#alert-type-grid .alert-type-card').first()).toBeAttached({ timeout: 15000 });
    await page.selectOption('#obs-custom-service', 'payment-api');
    await page.selectOption('#obs-custom-severity', 'P2');
    await page.fill('#obs-custom-summary', 'HTTP 500 spike on /pay');
    await page.fill('#obs-custom-log', 'connection pool timeout');
    await page.click('#obs-custom-use');
    await expect(page.locator('#obs-custom-alert-form')).toHaveClass(/is-active-custom/);
    await expect(page.locator('#alert-journey-track .journey-node').first()).toBeAttached({ timeout: 25000 });
    expect(await page.locator('#alert-journey-track .journey-node').count()).toBeGreaterThan(5);
    await expect(page.locator('#obs-sim-step-visual')).not.toHaveText(/Run a walkthrough/i);
  });

  test('preset cards each start a walkthrough', async ({ page }) => {
    await openSection(page, 'observability');
    await openTab(page, 'obs-simulator');
    const cards = page.locator('#alert-type-grid .alert-type-card');
    await expect(cards.first()).toBeAttached({ timeout: 15000 });
    const n = await cards.count();
    expect(n).toBeGreaterThanOrEqual(4);
    for (let i = 0; i < n; i += 1) {
      await cards.nth(i).click();
      await expect(page.locator('#alert-journey-track .journey-node').first()).toBeAttached({ timeout: 20000 });
    }
  });

  test('mcp, simulation, guardrails, evaluation, actions, learning controls', async ({ page }) => {
    await openSection(page, 'mcp');
    await openTab(page, 'mcp-playground');
    await expect(page.locator('#tab-mcp-playground')).not.toHaveClass(/hidden/);
    await openTab(page, 'mcp-skills');
    await expect(page.locator('#tab-mcp-skills')).not.toHaveClass(/hidden/);
    await openTab(page, 'mcp-vs-skills');
    await expect(page.locator('#tab-mcp-vs-skills')).not.toHaveClass(/hidden/);

    await openSection(page, 'simulation');
    await openTab(page, 'auto-change');
    await expect(page.locator('#tab-auto-change')).not.toHaveClass(/hidden/);
    await openTab(page, 'auto-opa');
    await expect(page.locator('#tab-auto-opa')).not.toHaveClass(/hidden/);

    await openSection(page, 'guardrails');
    await openTab(page, 'grd-overview');
    await expect(page.locator('#tab-grd-overview')).not.toHaveClass(/hidden/);
    await openTab(page, 'grd-editor');
    await expect(page.locator('#grd-rego-editor, #tab-grd-editor textarea, #tab-grd-editor').first()).toBeAttached();

    await openSection(page, 'evaluation');
    await openTab(page, 'eval-gate');
    await expect(page.locator('#eval-gate-run')).toBeAttached();
    await openTab(page, 'eval-tools');
    await expect(page.locator('#eval-tools-grid .tool-tile, #eval-tools-grid a').first()).toBeAttached();

    await openSection(page, 'governance');
    await openTab(page, 'gov-overview');
    await expect(page.locator('#gov-posture-banner')).toBeVisible();
    await expect(page.locator('#gov-overview-checks tr').first()).toBeAttached({ timeout: 15000 });
    await openTab(page, 'gov-github');
    await expect(page.locator('#gov-github-snippet')).toContainText('YOUR_GITHUB_ORG');

    await openSection(page, 'actions');
    await openTab(page, 'act-list');
    await expect(page.locator('#tab-act-list')).not.toHaveClass(/hidden/);

    await openSection(page, 'learning');
    await openTab(page, 'learn-notebook');
    await expect(page.locator('#tab-learn-notebook')).not.toHaveClass(/hidden/);
    await openTab(page, 'learn-designs');
    await expect(page.locator('.dp-card')).toHaveCount(3, { timeout: 15000 });
  });
});

test.describe('Native tools per design', () => {
  test.describe.configure({ timeout: 60000 });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  for (const [id, spec] of Object.entries(DESIGNS)) {
    test(`${id} Open buttons and explore tiles are reachable`, async ({ page, request }) => {
      await selectDesign(page, id);
      await openSection(page, 'ingestion');
      await openTab(page, 'ing-jobs');
      const vectorHref = await page.getByTestId('open-vector').getAttribute('href');
      expect(vectorHref).toBeTruthy();
      await expectReachable(request, vectorHref, `${id} open-vector`);

      for (const role of EXPLORE_ROLES) {
        const href = await page.getByTestId(`explore-${role}`).getAttribute('href');
        expect(href && href !== '#', `${id} ${role}`).toBeTruthy();
        await expectReachable(request, href, `${id} explore-${role}`);
      }

      await openSection(page, 'observability');
      await openTab(page, 'obs-simulator');
      for (const testId of ['open-metrics', 'open-dashboards', 'open-logs']) {
        const href = await page.getByTestId(testId).getAttribute('href');
        expect(href, `${id} ${testId}`).toBeTruthy();
        await expectReachable(request, href, `${id} ${testId}`);
      }
    });
  }
});
