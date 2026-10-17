import { chromium } from 'playwright';

async function check500() {
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

  page.on('response', resp => {
    if (resp.status() >= 400) {
      console.log(`[HTTP ${resp.status()}]: ${resp.url()}`);
    }
  });

  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' });
  await browser.close();
}

check500().catch(console.error);
