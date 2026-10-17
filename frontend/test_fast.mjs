import { chromium } from 'playwright';

async function test() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  await context.addInitScript(() => {
    localStorage.setItem('trendrop_session_token', 'demo_guest_token');
    localStorage.setItem('trendrop_user_email', 'demo@trendrop.app');
    localStorage.setItem('trendrop_user_plan', 'pro');
    localStorage.setItem('trendrop_user_niche', 'all');
    localStorage.setItem('trendrop_user_language', 'all');
  });
  const page = await context.newPage();

  console.log('--- NAV 1: Initial cold Vite load ---');
  let t0 = performance.now();
  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'domcontentloaded' });
  console.log(`[NAV 1] DOMContentLoaded: ${(performance.now() - t0).toFixed(0)}ms`);
  await page.waitForSelector('.tilt-card', { timeout: 30000 });
  console.log(`[NAV 1] First Card Rendered: ${(performance.now() - t0).toFixed(0)}ms`);

  console.log('\n--- NAV 2: Warm Vite & API cache reload ---');
  t0 = performance.now();
  await page.reload({ waitUntil: 'domcontentloaded' });
  console.log(`[NAV 2] DOMContentLoaded: ${(performance.now() - t0).toFixed(0)}ms`);
  await page.waitForSelector('.tilt-card', { timeout: 15000 });
  console.log(`[NAV 2] First Card Rendered: ${(performance.now() - t0).toFixed(0)}ms`);

  console.log('\n--- NAV 3: Switch to Global Filter ---');
  t0 = performance.now();
  const globalChip = page.locator('button:has-text("Global")').first();
  await globalChip.click();
  await page.waitForTimeout(100);
  await page.waitForSelector('.tilt-card', { timeout: 10000 });
  console.log(`[NAV 3] Global Switch Time: ${(performance.now() - t0).toFixed(0)}ms`);

  await browser.close();
}

test().catch(console.error);
