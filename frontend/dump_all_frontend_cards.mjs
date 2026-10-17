import { chromium } from "playwright";

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });

  await context.addInitScript(() => {
    localStorage.setItem('trendrop_session_token', 'demo_guest_token');
    localStorage.setItem('trendrop_user_email', 'demo@trendrop.app');
    localStorage.setItem('trendrop_user_plan', 'pro');
    localStorage.setItem('trendrop_user_niche', 'all');
    localStorage.setItem('trendrop_user_language', 'all');
    localStorage.setItem('trendrop_theme', 'dark');
  });

  const page = await context.newPage();

  page.on("console", msg => {
    if (msg.type() === "error") console.log("[BROWSER CONSOLE ERROR]", msg.text());
  });

  console.log("Navigating to http://127.0.0.1:5173/ ...");
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".tilt-card", { timeout: 15000 });

  console.log("\n=======================================================");
  console.log("1. DEFAULT UNFILTERED FEED (First 5 cards on screen):");
  console.log("=======================================================");
  const defaultCards = await page.$$(".tilt-card");
  console.log(`Total rendered default cards: ${defaultCards.length}`);
  for (let i = 0; i < Math.min(5, defaultCards.length); i++) {
    const text = await defaultCards[i].innerText();
    const firstLines = text.split("\n").map(s => s.trim()).filter(Boolean).slice(0, 5);
    console.log(`[Default Card #${i + 1}]: ${firstLines.join(" | ")}`);
  }

  // 2. OPEN FILTER MODAL & SELECT "GLOBAL"
  console.log("\n=======================================================");
  console.log("2. APPLYING '🌐 Global' FILTER...");
  console.log("=======================================================");
  const openFiltersBtn = page.locator('#open-filters-modal-btn');
  await openFiltersBtn.click();
  await page.waitForTimeout(600);

  const globalChip = page.locator('button:has-text("🌐 Global")').first();
  await globalChip.click();
  await page.waitForTimeout(300);

  const applyBtn = page.locator('button:has-text("Apply Filters")');
  await applyBtn.click();
  await page.waitForTimeout(2000);

  // 3. READ ALL CARDS ON SCREEN WITH GLOBAL FILTER
  const globalCards = await page.$$(".tilt-card");
  console.log(`\nTOTAL RENDERED CARDS UNDER 'GLOBAL' FILTER: ${globalCards.length}\n`);

  for (let i = 0; i < globalCards.length; i++) {
    const text = await globalCards[i].innerText();
    const lines = text.split("\n").map(s => s.trim()).filter(Boolean);
    console.log(`--- [GLOBAL CARD #${i + 1}] ---`);
    console.log(`Summary: ${lines.slice(0, 6).join(" | ")}`);
  }

  await page.screenshot({ path: "screenshot_global_filter.png", fullPage: false });
  console.log("\nSaved screenshot: screenshot_global_filter.png");

  await browser.close();
}

run().catch(err => {
  console.error("Error:", err);
  process.exit(1);
});
