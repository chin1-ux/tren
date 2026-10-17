import { chromium } from "playwright";

const TEST_CONFIGS = [
  {
    name: "Global (🌐 Global)",
    storage: {
      trendrop_pref_language: "global",
      trendrop_pref_niches: '["all"]'
    }
  },
  {
    name: "Hindi (🇮🇳 Hindi)",
    storage: {
      trendrop_pref_language: "hi",
      trendrop_pref_niches: '["all"]'
    }
  },
  {
    name: "Punjabi (🇮🇳 Punjabi)",
    storage: {
      trendrop_pref_language: "pa",
      trendrop_pref_niches: '["all"]'
    }
  },
  {
    name: "Spanish (🇪🇸 Spanish)",
    storage: {
      trendrop_pref_language: "es",
      trendrop_pref_niches: '["all"]'
    }
  },
  {
    name: "Portuguese (🇧🇷 Portuguese)",
    storage: {
      trendrop_pref_language: "pt",
      trendrop_pref_niches: '["all"]'
    }
  },
  {
    name: "Korean (🇰🇷 Korean)",
    storage: {
      trendrop_pref_language: "ko",
      trendrop_pref_niches: '["all"]'
    }
  },
  {
    name: "Fitness Niche (💪 Fitness)",
    storage: {
      trendrop_pref_language: "all",
      trendrop_pref_niches: '["fitness"]'
    }
  },
  {
    name: "Food Niche (🍔 Food)",
    storage: {
      trendrop_pref_language: "all",
      trendrop_pref_niches: '["food"]'
    }
  },
  {
    name: "Fashion Niche (👗 Fashion)",
    storage: {
      trendrop_pref_language: "all",
      trendrop_pref_niches: '["fashion"]'
    }
  },
  {
    name: "Comedy Niche (🎭 Comedy)",
    storage: {
      trendrop_pref_language: "all",
      trendrop_pref_niches: '["comedy"]'
    }
  }
];

async function main() {
  const browser = await chromium.launch({ headless: true });

  console.log("======================================================================");
  console.log("   LIVE FRONTEND FILTER VERIFICATION (NO FABRICATION, RAW DOM READ)   ");
  console.log("======================================================================\n");

  for (const cfg of TEST_CONFIGS) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });

    await context.addInitScript((storage) => {
      localStorage.setItem('trendrop_session_token', 'demo_guest_token');
      localStorage.setItem('trendrop_user_email', 'demo@trendrop.app');
      localStorage.setItem('trendrop_user_plan', 'pro');
      localStorage.setItem('trendrop_theme', 'dark');
      for (const [k, v] of Object.entries(storage)) {
        localStorage.setItem(k, v);
      }
    }, cfg.storage);

    const page = await context.newPage();
    try {
      await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
      await page.waitForSelector(".tilt-card", { timeout: 12000 });
      // Short delay to let React settle
      await page.waitForTimeout(1000);

      const cards = await page.evaluate(() => {
        const els = Array.from(document.querySelectorAll('.tilt-card'));
        return els.map(c => {
          const h3 = c.querySelector('h3');
          const p = c.querySelector('h3 + p, .text-xs.text-muted-foreground');
          const statusBadge = c.querySelector('span')?.innerText?.trim();
          const allText = c.innerText.split('\n').map(s => s.trim()).filter(Boolean);
          return {
            title: h3?.innerText?.trim() || 'Untitled',
            artist: p?.innerText?.trim() || 'Unknown',
            status: statusBadge || '',
            snippet: allText.slice(0, 5).join(' | ')
          };
        });
      });

      console.log(`\n----------------------------------------------------------------------`);
      console.log(`FILTER: ${cfg.name} -> Rendered Cards Count: ${cards.length}`);
      console.log(`----------------------------------------------------------------------`);
      if (cards.length === 0) {
        console.log("  [No cards rendered for this filter]");
      } else {
        cards.slice(0, 6).forEach((c, i) => {
          console.log(`  Card #${i + 1}: "${c.title}" by ${c.artist} [${c.status}]`);
        });
        if (cards.length > 6) {
          console.log(`  ... and ${cards.length - 6} more cards.`);
        }
      }
    } catch (err) {
      console.log(`FILTER: ${cfg.name} -> Error or 0 cards: ${err.message}`);
    } finally {
      await context.close();
    }
  }

  await browser.close();
  console.log("\n======================================================================");
  console.log("   AUDIT COMPLETE   ");
  console.log("======================================================================");
}

main().catch(console.error);
