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

  async function getCards() {
    return await page.evaluate(() => {
      const cards = Array.from(document.querySelectorAll('.tilt-card'));
      return cards.map(c => {
        const h3 = c.querySelector('h3');
        const p = c.querySelector('h3 + p, .text-xs.text-muted-foreground');
        const statusBadge = c.querySelector('span')?.innerText?.trim();
        return {
          title: h3?.innerText?.trim() || '',
          artist: p?.innerText?.trim() || '',
          status: statusBadge || ''
        };
      });
    });
  }

  async function setFilter(langLabel, nicheLabel) {
    await page.locator('#open-filters-modal-btn').click();
    await page.waitForTimeout(500);

    // Reset filters inside modal if Reset button exists
    const resetBtn = page.locator('button:has-text("Reset All"), button:has-text("Clear")').first();
    if (await resetBtn.isVisible().catch(() => false)) {
      await resetBtn.click();
      await page.waitForTimeout(300);
    }

    if (langLabel) {
      const langChip = page.locator(`button:has-text("${langLabel}")`).first();
      if (await langChip.isVisible().catch(() => false)) {
        await langChip.click();
        await page.waitForTimeout(200);
      }
    }

    if (nicheLabel) {
      const nicheChip = page.locator(`button:has-text("${nicheLabel}")`).first();
      if (await nicheChip.isVisible().catch(() => false)) {
        await nicheChip.click();
        await page.waitForTimeout(200);
      }
    }

    await page.locator('button:has-text("Apply Filters")').click();
    await page.waitForTimeout(1500);
  }

  const tests = [
    { name: "Global Filter", lang: "🌐 Global" },
    { name: "Hindi Filter", lang: "🇮🇳 Hindi" },
    { name: "Punjabi Filter", lang: "🇮🇳 Punjabi" },
    { name: "Spanish Filter", lang: "🇪🇸 Spanish" },
    { name: "Portuguese Filter", lang: "🇧🇷 Portuguese" },
    { name: "Korean Filter", lang: "🇰🇷 Korean" },
    { name: "Fitness Niche", niche: "Fitness & Gym" },
    { name: "Food Niche", niche: "Food & Cooking" },
    { name: "Fashion Niche", niche: "Fashion & Beauty" },
  ];

  console.log("=== COMPREHENSIVE LIVE FRONTEND FILTER AUDIT ===");

  for (const t of tests) {
    await setFilter(t.lang, t.niche);
    const cards = await getCards();
    console.log(`\n----------------------------------------------------`);
    console.log(`[FILTER: ${t.name}] -> Cards on screen: ${cards.length}`);
    cards.slice(0, 5).forEach((c, idx) => {
      console.log(`  #${idx + 1}: "${c.title}" by ${c.artist} (${c.status})`);
    });
  }

  await browser.close();
}

main().catch(console.error);
