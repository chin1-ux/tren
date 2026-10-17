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

  page.on('request', req => console.log('REQ:', req.method(), req.url()));
  page.on('response', resp => console.log('RESP:', resp.status(), resp.url()));
  page.on('requestfailed', req => console.log('FAILED:', req.method(), req.url(), req.failure()?.errorText));

  await page.goto('http://127.0.0.1:5173/');
  await page.waitForTimeout(6000);

  await browser.close();
}

test().catch(console.error);
