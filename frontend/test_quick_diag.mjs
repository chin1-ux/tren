import { chromium } from "playwright";

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  await context.addInitScript(() => {
    localStorage.setItem("trendrop_session_token", "demo_guest_token");
    localStorage.setItem("trendrop_user_email", "demo@trendrop.app");
    localStorage.setItem("trendrop_user_plan", "pro");
    localStorage.setItem("trendrop_user_niche", "all");
    localStorage.setItem("trendrop_user_language", "all");
  });
  const page = await context.newPage();
  page.on('console', m => console.log('LOG:', m.type(), m.text()));
  page.on('pageerror', e => console.log('PAGE ERROR:', e.message));
  page.on('request', r => {
    if (r.url().includes('/api/')) console.log('REQ:', r.method(), r.url());
  });
  page.on('response', async r => {
    if (r.url().includes('/api/')) {
      let b = 0;
      try { b = (await r.body()).length; } catch {}
      console.log('RESP:', r.status(), r.url(), `${b} bytes`);
    }
  });
  page.on('requestfailed', r => {
    if (r.url().includes('/api/')) console.log('FAILED:', r.url(), r.failure()?.errorText);
  });

  console.log("Navigating to http://localhost:5173/...");
  await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(6000);
  const cardCount = await page.locator('.tilt-card').count();
  console.log("Card count:", cardCount);
  const bodyText = await page.innerText('body');
  console.log("Body snippet:", bodyText.slice(0, 300).replace(/\n/g, ' '));
  await browser.close();
}

main().catch(console.error);
