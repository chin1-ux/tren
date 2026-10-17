import { chromium } from 'playwright';

async function test() {
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

  page.on('console', msg => console.log('LOG:', msg.text()));

  await page.goto('http://127.0.0.1:5173/');
  await page.waitForTimeout(1000);

  const lsState = await page.evaluate(() => {
    return {
      session_token: localStorage.getItem("trendrop_session_token"),
      email: localStorage.getItem("trendrop_user_email"),
      allKeys: Object.keys(localStorage),
    };
  });
  console.log('LocalStorage State:', lsState);

  await page.waitForTimeout(3000);

  const lsState2 = await page.evaluate(() => {
    return {
      session_token: localStorage.getItem("trendrop_session_token"),
      email: localStorage.getItem("trendrop_user_email"),
      allKeys: Object.keys(localStorage),
    };
  });
  console.log('LocalStorage State after 4s:', lsState2);

  const text = await page.evaluate(() => document.body.innerText);
  console.log('Body text:\n', text.slice(0, 300));

  await browser.close();
}

test().catch(console.error);
