import { chromium } from 'playwright';
import path from 'path';

(async () => {
  console.log('=== RUNNING PLAYWRIGHT LIVE VERIFICATION ===');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();

  const baseUrl = process.argv[2] || 'https://trendrop-black.vercel.app';
  console.log(`Target site: ${baseUrl}`);

  try {
    // 1. Visit /login, set demo session in localStorage, and navigate to homepage
    await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.evaluate(() => {
      localStorage.setItem("trendrop_session_token", "demo_guest_token");
      localStorage.setItem("trendrop_user_email", "demo@trendrop.app");
      localStorage.setItem("trendrop_user_plan", "pro");
      localStorage.setItem("trendrop_user_niche", "all");
      localStorage.setItem("trendrop_user_language", "all");
    });
    await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);
















    console.log('\n--- TESTING RISING TAB ---');
    const risingText = await page.evaluate(() => document.body.innerText);
    console.log('Rising Tab preview:');
    console.log(risingText.slice(0, 600));

    console.log('\n--- TESTING EMERGING TAB ---');
    await page.click('button:has-text("EMERGING")');
    await page.waitForTimeout(2000);

    const emergingText = await page.evaluate(() => document.body.innerText);
    console.log('Emerging Tab preview:');
    console.log(emergingText.slice(0, 600));

    // Capture screenshot of live UI
    const ssPath = path.resolve('scratch/playwright_live_success.png');
    await page.screenshot({ path: ssPath, fullPage: true });
    console.log(`\nScreenshot saved to ${ssPath}`);

    const hasRisingTrend = risingText.includes('Chole Bhature') || risingText.includes('WANG');
    const hasEmergingTrend = emergingText.includes('To Brazil!') || emergingText.includes('San Gauri Ganapaticha Aala');

    console.log('\n==================================================');
    console.log(`  Rising Feed Verified: ${hasRisingTrend}`);
    console.log(`  Emerging Feed Verified: ${hasEmergingTrend}`);
    console.log('==================================================');

    if (hasRisingTrend && hasEmergingTrend) {
      console.log('🎉 E2E TEST COMPLETE: Both Rising and Emerging feeds show live scraped trends!');
    }

  } catch (err) {
    console.error('Playwright Test Error:', err);
  } finally {
    await browser.close();
  }
})();
