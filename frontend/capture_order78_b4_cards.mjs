import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const outDir = path.resolve("../evidence/order78/screens");
fs.mkdirSync(outDir, { recursive: true });

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
  });

  await context.addInitScript(() => {
    localStorage.setItem("trendrop_session_token", "demo_guest_token");
    localStorage.setItem("trendrop_user_email", "demo@trendrop.app");
    localStorage.setItem("trendrop_user_plan", "pro");
    localStorage.setItem("trendrop_user_niche", "all");
    localStorage.setItem("trendrop_user_language", "all");
    localStorage.setItem("trendrop_onboarding_completed", "true");
    localStorage.setItem("trendrop_welcomed", "true");
  });

  const page = await context.newPage();

  console.log("Navigating to https://trendrop-black.vercel.app...");
  await page.goto("https://trendrop-black.vercel.app", { waitUntil: "networkidle", timeout: 30000 });

  // Dismiss onboarding modal if present (click "See Today's 5" or dismiss)
  try {
    const dismissBtn = page.locator("button:has-text('See Today')").first();
    if (await dismissBtn.isVisible({ timeout: 3000 })) {
      console.log("Dismissing onboarding flow...");
      await dismissBtn.click();
      await page.waitForTimeout(1000);
    }
  } catch (e) {
    console.log("No onboarding prompt visible.");
  }

  // Wait for trend cards
  await page.waitForSelector("[data-testid='trend-card'], .glass-card, article", { timeout: 15000 });
  const cards = await page.$$("[data-testid='trend-card'], .glass-card, article");
  console.log(`Found ${cards.length} cards on live page.`);

  for (let i = 0; i < Math.min(3, cards.length); i++) {
    const card = cards[i];
    await card.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    const shotPath = path.join(outDir, `card_dual_date_${i + 1}.png`);
    await card.screenshot({ path: shotPath });
    console.log(`Saved screenshot of Card ${i + 1} to ${shotPath}`);
  }

  await browser.close();
  console.log("Done capturing live trend card screenshots.");
}

main().catch(err => {
  console.error("Error:", err);
  process.exit(1);
});
