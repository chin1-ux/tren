import { test, expect } from '@playwright/test';

test.describe('Dashboard Tabs Infinite Loop Audit', () => {
  test('Audit all 3 dashboard tabs for Maximum update depth exceeded or re-render loops', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: Error[] = [];

    page.on('console', (msg) => {
      const text = msg.text();
      if (msg.type() === 'error' || text.includes('Maximum update depth') || text.includes('Too many re-renders') || text.includes('React has detected')) {
        console.log(`[BROWSER CONSOLE ERROR] ${text}`);
        consoleErrors.push(text);
      }
    });

    page.on('pageerror', (err) => {
      console.error(`[BROWSER PAGE ERROR] ${err.stack || err.message}`);
      pageErrors.push(err);
    });

    // Mock authenticated user session
    await page.route('**/api/auth/verify', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          valid: true,
          user: {
            email: 'test@trendrop.internal',
            niche: 'fitness',
            language: 'en',
            plan: 'pro',
          },
        }),
      });
    });

    await page.addInitScript(() => {
      window.localStorage.setItem('trendrop_session_token', 'mock_pro_token');
      window.localStorage.setItem('trendrop_user_email', 'test@trendrop.internal');
      window.localStorage.setItem('trendrop_user_niche', 'fitness');
      window.localStorage.setItem('trendrop_user_plan', 'pro');
    });

    console.log("Navigating to http://localhost:8080/dashboard ...");
    await page.goto('http://localhost:8080/dashboard', { waitUntil: 'networkidle' });

    // 1. Audit Tab 1: Spotify Viral
    console.log("Auditing Tab 1: Spotify Viral...");
    const tab1 = page.locator('button[value="early-detection"], [role="tab"]:has-text("Spotify")').first();
    if (await tab1.isVisible().catch(() => false)) {
      await tab1.click({ force: true });
      await page.waitForTimeout(3000);
    }

    // 2. Audit Tab 2: Viral News
    console.log("Auditing Tab 2: Viral News...");
    const tab2 = page.locator('button[value="breaking-news"], [role="tab"]:has-text("Viral News")').first();
    if (await tab2.isVisible().catch(() => false)) {
      await tab2.click({ force: true });
      await page.waitForTimeout(3000);
    }

    // 3. Audit Tab 3: Analytics & AI
    console.log("Auditing Tab 3: Analytics & AI...");
    const tab3 = page.locator('button[value="analytics"], [role="tab"]:has-text("Analytics")').first();
    if (await tab3.isVisible().catch(() => false)) {
      await tab3.click({ force: true });
      await page.waitForTimeout(3000);
    }

    console.log(`Audit finished. Captured ${consoleErrors.length} console errors and ${pageErrors.length} page errors.`);
  });
});
