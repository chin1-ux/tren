import { chromium } from 'playwright';
import fs from 'fs';

async function inspect() {
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

  page.on('console', msg => console.log(`[BROWSER ${msg.type()}]:`, msg.text()));
  page.on('pageerror', err => console.log(`[PAGE ERROR]:`, err.message));

  console.log('Navigating to http://localhost:8080/ ...');
  await page.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
  
  await page.screenshot({ path: 'inspect_page.png' });
  const html = await page.content();
  fs.writeFileSync('inspect_dom.txt', html.slice(0, 3000));

  const text = await page.innerText('body');
  console.log('Body text sample:\n', text.slice(0, 500));

  await browser.close();
}

inspect().catch(console.error);
