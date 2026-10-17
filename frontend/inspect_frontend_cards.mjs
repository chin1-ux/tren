import { chromium } from "playwright";

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log("Navigating to http://127.0.0.1:5173/ ...");
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });

  // Wait for initial cards
  await page.waitForSelector("[data-testid='trend-card'], .trend-card, article", { timeout: 15000 });
  
  console.log("Page loaded. Initial cards count on all feed:");
  const initialCards = await page.$$("[data-testid='trend-card'], .trend-card, article");
  console.log("Initial count:", initialCards.length);

  // Print first 3 cards from all feed
  for (let i = 0; i < Math.min(3, initialCards.length); i++) {
    const text = await initialCards[i].innerText();
    console.log(`Initial Card #${i + 1}:`, text.split("\n").filter(Boolean).slice(0, 3).join(" | "));
  }

  // Click Filters
  console.log("\nLooking for Filter modal trigger...");
  const filterBtn = page.getByRole("button", { name: /Filters/i });
  await filterBtn.click();
  await page.waitForTimeout(500);

  // Click Global filter option
  console.log("Looking for Global button in filter sheet...");
  const globalBtn = page.getByRole("button", { name: /Global/i }).first();
  await globalBtn.click();
  await page.waitForTimeout(500);

  // Click Apply / Close if needed or check if it applies automatically
  // In Trendrop, clicking the language pill in the Filter Sheet sets filters.language
  // Let's close the sheet if there's a close button or backdrop
  const closeBtn = page.locator("[aria-label='Close'], button:has-text('✕'), button:has-text('Close'), button:has-text('Apply')").first();
  if (await closeBtn.isVisible().catch(() => false)) {
    await closeBtn.click();
  } else {
    // Click outside
    await page.keyboard.press("Escape");
  }
  await page.waitForTimeout(2000);

  // Now inspect all cards on screen
  const cards = await page.$$("[data-testid='trend-card'], .trend-card, article");
  console.log(`\n=== DISPLAYED CARDS WITH 'GLOBAL' FILTER ACTIVE (Count: ${cards.length}) ===`);

  for (let i = 0; i < cards.length; i++) {
    const card = cards[i];
    const text = await card.innerText();
    const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
    console.log(`\n[Card ${i + 1}]`);
    console.log(lines.slice(0, 5).join(" | "));
  }

  await browser.close();
}

main().catch(err => {
  console.error("Test error:", err);
  process.exit(1);
});
