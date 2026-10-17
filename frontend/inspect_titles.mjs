import { chromium } from "playwright";

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });

  await context.addInitScript(() => {
    localStorage.setItem('trendrop_session_token', 'demo_guest_token');
    localStorage.setItem('trendrop_user_email', 'demo@trendrop.app');
    localStorage.setItem('trendrop_user_plan', 'pro');
    localStorage.setItem('trendrop_theme', 'dark');
  });

  const page = await context.newPage();
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".tilt-card", { timeout: 15000 });

  // Open filter modal and select Global
  await page.locator('#open-filters-modal-btn').click();
  await page.waitForTimeout(500);
  await page.locator('button:has-text("🌐 Global")').first().click();
  await page.waitForTimeout(300);
  await page.locator('button:has-text("Apply Filters")').click();
  await page.waitForTimeout(2000);

  // Extract all cards data cleanly
  const cardsData = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll('.tilt-card'));
    return cards.map(c => {
      const h3 = c.querySelector('h3');
      const artistEl = c.querySelector('h3 + p, .text-xs.text-muted-foreground');
      const badgeStatus = c.querySelector('span')?.innerText;
      return {
        title: h3?.innerText || 'NO_H3',
        allText: c.innerText.split('\n').filter(Boolean)
      };
    });
  });

  console.log("Found Global cards:", cardsData.length);
  cardsData.forEach((c, idx) => {
    console.log(`Card #${idx + 1}: Title="${c.title}"`);
    console.log(`   Text lines:`, c.allText.slice(0, 8).join(" /// "));
  });

  await browser.close();
}

main().catch(console.error);
