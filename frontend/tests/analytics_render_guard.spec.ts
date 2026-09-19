import { test, expect } from '@playwright/test';

test.describe('Creator Analytics Dashboard Render Guard', () => {
  test('should render CreatorAnalyticsDashboard tab cleanly with metrics=null without crashing', async ({ page }) => {
    const pageErrors: Error[] = [];
    page.on('pageerror', (error) => {
      console.error('[Browser PageError]', error);
      pageErrors.push(error);
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        console.error('[Browser Console Error]', msg.text());
      }
    });

    // Intercept auth verification to simulate a valid Free-tier logged-in user
    await page.route('**/api/auth/verify', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          valid: true,
          user: {
            email: 'free_test@trendrop.internal',
            niche: 'fitness',
            language: 'en',
            plan: 'free',
          },
        }),
      });
    });

    // Intercept creator metrics endpoint to explicitly return metrics: null (Free-tier / missing metrics)
    await page.route('**/api/creator/metrics*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          metrics: null,
          has_connected_account: false,
        }),
      });
    });

    // Set auth token in localStorage before page load
    await page.addInitScript(() => {
      window.localStorage.setItem('trendrop_session_token', 'mock_valid_token');
      window.localStorage.setItem('trendrop_user_email', 'free_test@trendrop.internal');
      window.localStorage.setItem('trendrop_user_niche', 'fitness');
      window.localStorage.setItem('trendrop_user_plan', 'free');
    });

    // Navigate to dashboard
    await page.goto('http://localhost:8080/dashboard', { waitUntil: 'domcontentloaded' });

    // Click on the Analytics & AI tab
    const analyticsTab = page.locator('button[value="analytics"], [role="tab"]:has-text("Analytics")').first();
    await analyticsTab.waitFor({ state: 'visible', timeout: 10000 });
    await analyticsTab.click();

    // Wait 3 seconds for component render to complete
    await page.waitForTimeout(3000);

    // 1. Verify ZERO unhandled exceptions or React #310 / null-pointer crashes occurred
    expect(pageErrors).toHaveLength(0);

    // 2. Save full page screenshot as concrete evidence of clean UI render
    await page.screenshot({ path: 'scratch/analytics_null_metrics_render.png', fullPage: true });

    // 3. Verify key UI elements render safely in fallback / null state
    const pageText = await page.innerText('body');
    expect(pageText).toContain('Instagram Account Connection');
    expect(pageText).toContain('Total Views');
    expect(pageText).toContain('Avg Engagement');
    expect(pageText).toContain('Not enough data yet');
  });
});
