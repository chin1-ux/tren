import { chromium } from "playwright";
import fs from "fs";
import path from "path";

async function runFullVerification() {
  console.log("=== STARTING PLAYWRIGHT LIVE VERIFICATION ===");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(msg.text());
    }
  });

  const screenshotsDir = path.join(process.cwd(), "scratch", "playwright_screenshots");
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  try {
    // 1. Trends Page Verification
    console.log("Navigating to https://trendrop-black.vercel.app/ ...");
    await page.goto("https://trendrop-black.vercel.app/", { waitUntil: "networkidle" });
    await page.waitForTimeout(3000);
    
    const trendsScreenshot = path.join(screenshotsDir, "01_trends_tab.png");
    await page.screenshot({ path: trendsScreenshot, fullPage: false });
    console.log(`Saved screenshot: ${trendsScreenshot}`);

    // Verify Rising cards content
    const trendCards = await page.locator(".rounded-2xl").count();
    console.log(`Found ${trendCards} UI trend cards on main Trends page.`);

    // 2. Dashboard Page Verification
    console.log("Navigating to https://trendrop-black.vercel.app/dashboard ...");
    await page.goto("https://trendrop-black.vercel.app/dashboard", { waitUntil: "networkidle" });
    await page.waitForTimeout(3000);

    const dashboardScreenshot = path.join(screenshotsDir, "02_dashboard_early_audio.png");
    await page.screenshot({ path: dashboardScreenshot, fullPage: false });
    console.log(`Saved screenshot: ${dashboardScreenshot}`);

    // Click on Spotify Viral filter pill if present
    const spotifyPill = page.locator("button:has-text('Spotify Viral')");
    if (await spotifyPill.isVisible()) {
      console.log("Clicking 'Spotify Viral' pill...");
      await spotifyPill.click();
      await page.waitForTimeout(2000);
      const spotifyScreenshot = path.join(screenshotsDir, "03_spotify_viral_pill.png");
      await page.screenshot({ path: spotifyScreenshot, fullPage: false });
      console.log(`Saved screenshot: ${spotifyScreenshot}`);
    }

    // Click on Live News tab
    const newsTab = page.locator("button:has-text('Viral News')");
    if (await newsTab.isVisible()) {
      console.log("Clicking 'Viral News' tab...");
      await newsTab.click();
      await page.waitForTimeout(2000);
      const newsScreenshot = path.join(screenshotsDir, "04_viral_news_tab.png");
      await page.screenshot({ path: newsScreenshot, fullPage: false });
      console.log(`Saved screenshot: ${newsScreenshot}`);
    }

    // Click on Live Festivals tab
    const festivalTab = page.locator("button:has-text('Live Festivals')");
    if (await festivalTab.isVisible()) {
      console.log("Clicking 'Live Festivals' tab...");
      await festivalTab.click();
      await page.waitForTimeout(2000);
      const festivalScreenshot = path.join(screenshotsDir, "05_live_festivals_tab.png");
      await page.screenshot({ path: festivalScreenshot, fullPage: false });
      console.log(`Saved screenshot: ${festivalScreenshot}`);
    }

    console.log("\n=== PLAYWRIGHT AUDIT RESULT ===");
    console.log(`Console errors captured: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) {
      console.log("Console Errors:", consoleErrors);
    } else {
      console.log("✅ PERFECT! 0 console errors captured.");
    }
  } catch (err) {
    console.error("Playwright execution error:", err);
  } finally {
    await browser.close();
  }
}

runFullVerification();
