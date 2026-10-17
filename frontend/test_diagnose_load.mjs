import { chromium } from 'playwright';

async function diagnose() {
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

  const reqStarts = new Map();

  page.on('request', req => {
    if (req.url().includes('127.0.0.1:8000') || req.url().includes('/api/')) {
      reqStarts.set(req.url(), performance.now());
      console.log(`[REQ START] ${req.method()} ${req.url()}`);
    }
  });

  page.on('requestfinished', req => {
    if (req.url().includes('127.0.0.1:8000') || req.url().includes('/api/')) {
      const start = reqStarts.get(req.url());
      const dur = start ? (performance.now() - start).toFixed(0) : '?';
      console.log(`[REQ DONE ${dur}ms] ${req.method()} ${req.url()}`);
    }
  });

  page.on('requestfailed', req => {
    console.log(`[REQ FAILED] ${req.url()} - ${req.failure()?.errorText}`);
  });

  page.on('console', msg => {
    console.log(`[CONSOLE ${msg.type()}] ${msg.text()}`);
  });

  console.log('Navigating to http://127.0.0.1:5173/ ...');
  const t0 = performance.now();
  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'domcontentloaded' });
  console.log(`DOMContentLoaded at ${(performance.now() - t0).toFixed(0)}ms`);

  // Check when cards appear
  try {
    await page.waitForSelector('.tilt-card', { timeout: 15000 });
    console.log(`First card rendered at ${(performance.now() - t0).toFixed(0)}ms`);
    const cardCount = await page.locator('.tilt-card').count();
    console.log(`Found ${cardCount} cards`);
  } catch (e) {
    console.log(`Cards not found within 15s: ${e.message}`);
  }

  // Check what buttons exist for language / filters
  const buttons = await page.$$eval('button', btns => btns.map(b => b.innerText.trim()).filter(Boolean));
  console.log('Buttons on page:', buttons.slice(0, 20));

  await browser.close();
}

diagnose().catch(console.error);
