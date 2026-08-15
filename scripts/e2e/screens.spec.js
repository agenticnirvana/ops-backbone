const { test, expect } = require('@playwright/test');
const { login, openSection, openTab, SCREENS } = require('./helpers');

test.describe('Every screen and tab', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  for (const screen of SCREENS) {
    test(`${screen.section} opens and every tab renders`, async ({ page }) => {
      await openSection(page, screen.section);
      for (const tab of screen.tabs) {
        await openTab(page, tab);
        const panel = page.locator(`#tab-${tab}`);
        await expect(panel).toBeAttached();
        await expect(panel).not.toHaveClass(/hidden/);
      }
    });
  }

  test('admin section is available after admin login', async ({ browser }) => {
    const adminPage = await browser.newPage();
    await login(adminPage, { email: 'admin@agentops.local', password: 'admin123' });
    await expect(adminPage.getByTestId('nav-admin')).not.toHaveClass(/hidden/);
    await openSection(adminPage, 'admin');
    for (const tab of ['adm-overview', 'adm-agents', 'adm-users', 'adm-activity']) {
      await openTab(adminPage, tab);
      await expect(adminPage.locator(`#tab-${tab}`)).not.toHaveClass(/hidden/);
    }
    await adminPage.close();
  });
});
