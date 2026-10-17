import { chromium } from 'playwright';

async function main() {
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
  
  page.on('console', msg => {
    if (msg.type() === 'error') console.log('[CONSOLE ERROR]:', msg.text());
  });
  page.on('pageerror', err => console.log('[PAGE ERROR EXCEPTION]:', err.message, '\n', err.stack));

  await page.goto('http://127.0.0.1:5173/');
  await page.waitForTimeout(4000);

  const html = await page.content();
  console.log('Page HTML length:', html.length);
  
  const tiltCount = await page.locator('.tilt-card').count();
  const skeletonCount = await page.locator('.animate-pulse').count();
  console.log('Tilt Cards:', tiltCount, '| Skeletons:', skeletonCount);

  // Check what's inside div.space-y-4
  const spaceY4 = await page.locator('.space-y-4').allInnerTexts();
  console.log('space-y-4 text chunks:', spaceY4.map(t => t.slice(0, 100)));

  await browser.close();
}

main().catch(console.error);
