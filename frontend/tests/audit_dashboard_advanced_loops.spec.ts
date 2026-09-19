import { test, expect } from '@playwright/test';

test.describe('Advanced Dashboard Re-Render & Race Condition Audit', () => {

  test('Scenario 1: Rapid Tab-Switching (50ms intervals)', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: Error[] = [];

    page.on('console', (msg) => {
      const text = msg.text();
      if (text.includes('Maximum update depth') || text.includes('Too many re-renders') || text.includes('Rendered more hooks')) {
        console.log(`[RE-RENDER LOOP DETECTED] ${text}`);
        consoleErrors.push(text);
      }
    });

    page.on('pageerror', (err) => {
      console.error(`[PAGE ERROR] ${err.message}`);
      pageErrors.push(err);
    });

    await page.goto('http://localhost:8080/dashboard');

    const tab1 = page.locator('button[value="early-detection"]').first();
    const tab2 = page.locator('button[value="breaking-news"]').first();
    const tab3 = page.locator('button[value="analytics"]').first();

    // Rapid switching loop (10 cycles)
    for (let i = 0; i < 10; i++) {
      if (await tab1.isVisible().catch(() => false)) await tab1.click({ force: true });
      await page.waitForTimeout(50);
      if (await tab2.isVisible().catch(() => false)) await tab2.click({ force: true });
      await page.waitForTimeout(50);
      if (await tab3.isVisible().catch(() => false)) await tab3.click({ force: true });
      await page.waitForTimeout(50);
    }

    await page.waitForTimeout(2000);
    expect(consoleErrors).toHaveLength(0);
    expect(pageErrors).toHaveLength(0);
  });

  test('Scenario 2: Mid-Session 401 & Expired Session Token', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      const text = msg.text();
      if (text.includes('Maximum update depth') || text.includes('Too many re-renders') || text.includes('Rendered more hooks')) {
        console.log(`[RE-RENDER LOOP DETECTED] ${text}`);
        consoleErrors.push(text);
      }
    });

    // Intercept API calls to return 401 Unauthorized mid-session
    await page.route('**/api/**', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Session token expired' }),
      });
    });

    await page.goto('http://localhost:8080/dashboard');
    await page.waitForTimeout(3000);

    expect(consoleErrors).toHaveLength(0);
  });

  test('Scenario 3: Delayed Latency & Empty API Payloads', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      const text = msg.text();
      if (text.includes('Maximum update depth') || text.includes('Too many re-renders') || text.includes('Rendered more hooks')) {
        console.log(`[RE-RENDER LOOP DETECTED] ${text}`);
        consoleErrors.push(text);
      }
    });

    // Simulate 1000ms network latency with empty arrays
    await page.route('**/api/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('http://localhost:8080/dashboard');
    await page.waitForTimeout(4000);

    expect(consoleErrors).toHaveLength(0);
  });
});
