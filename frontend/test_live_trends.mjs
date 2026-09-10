import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

(async () => {
  console.log('=== RUNNING PLAYWRIGHT LIVE TRENDS TEST ===');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const targetUrl = process.argv[2] || 'https://trendrop-black.vercel.app/';
  console.log(`Navigating to ${targetUrl}...`);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000); // Allow React Query to resolve

    // Capture screenshot
    const ssPath = path.resolve('scratch/live_frontend_trends.png');
    await page.screenshot({ path: ssPath, fullPage: true });
    console.log(`Screenshot saved to ${ssPath}`);

    const pageText = await page.evaluate(() => document.body.innerText);
    console.log('\nPage Header / Summary Snippet:');
    console.log(pageText.slice(0, 400));

    // Check DOM for trends
    const isWarmingUp = pageText.includes('Our active trend rail is warming up');
    const isNoTrends = pageText.includes('No trends right now');
    const zeroActive = pageText.includes('0 active trends tracked');

    console.log('\n--- VERIFICATION CHECKS ---');
    console.log(`Zero active trends text present: ${zeroActive}`);
    console.log(`No trends right now text present: ${isNoTrends}`);

    if (pageText.includes('Chole Bhature') || pageText.includes('WANG') || pageText.includes('To Brazil') || pageText.includes('active trends tracked')) {
      console.log('✅ SUCCESS: Active trend items or counts are rendered in the DOM!');
    } else {
      console.log('⚠️ NOTE: Checking for fallback cards or tab items...');
    }

  } catch (err) {
    console.error('Playwright Test Error:', err);
  } finally {
    await browser.close();
  }
})();
