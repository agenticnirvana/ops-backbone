const { test, expect } = require('@playwright/test');
const { login } = require('./helpers');

test.describe('Login', () => {
  test('operator can sign in and see the console', async ({ page }) => {
    await login(page);
    await expect(page.locator('#page-title')).toBeVisible();
    await expect(page.getByTestId('nav-operations')).toBeVisible();
  });

  test('bad password stays on login', async ({ page }) => {
    await page.goto('/');
    await page.fill('#email', 'operator@agentops.local');
    await page.fill('#password', 'wrong-password');
    await page.click('#login-form button[type="submit"]');
    await expect(page.locator('#login-screen')).toBeVisible();
    await expect(page.locator('#app-screen')).toBeHidden();
  });
});
