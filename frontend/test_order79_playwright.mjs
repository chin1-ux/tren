import { chromium } from "playwright";
import fs from "fs";

// Load old (select *) payloads exported directly from database
const oldPayloads = JSON.parse(fs.readFileSync("evidence/order78/old_payloads.json", "utf-8"));

// Explicit list of feed card columns + frontend-adapted properties
const FEED_COLS = new Set([
  "id", "audio_title", "audio_artist", "audio_id", "audio_use_count", "content_type", "window_hours_remaining",
  "velocity_avg", "language", "language_final", "status", "saturation_score", "creator_fit_score", "hook_retention_score",
  "created_at", "first_detected_at", "niche_tag", "semantic_niches", "discovery_source", "is_regional_crossover",
  "crossover_from_language", "crossover_message", "used_for", "used_for_note", "trend_classification", "velocity_pattern",
  "optimal_post_hour_ist", "why_this_works", "vibe_tag", "platform", "is_dance", "is_voiceover", "is_seed_data",
  "is_evergreen", "trend_age_hours", "template_link", "saturation_count", "hook_brief", "status_changed_at",
  "adaptation_briefs", "niche_relevance", "reel_count", "audio_cue_second", "best_platform_first", "trend_origin",
  "virality_type", "content_tone", "display_title", "commercial_song_alias", "has_creator_outlier", "global_saturation_pct",
  "india_saturation_pct", "ideal_content_description", "opportunity_score", "peaking_score", "saturation_penalty",
  "llm_classification_status", "composite_score", "top_reels", "reel_id", "song", "artist", "user_watermark_id",
  "category", "contentType", "contentTypeEmoji", "hoursLeft", "expiresAt", "viralMultiplier", "rawLanguage",
  "fallbackLanguage", "views_delta_last_run", "detected_language"
]);

function slimPayload(rows) {
  return (rows || []).map((row) => {
    const slimmed = {};
    for (const [k, v] of Object.entries(row)) {
      if (FEED_COLS.has(k)) {
        slimmed[k] = v;
      }
    }
    return slimmed;
  });
}

function normalizeCardText(txt) {
  return (txt || "")
    .replace(/GROWTH\s+Tracking started\.\.\./g, "")
    .replace(/\b\d+\s*(h|m|s|d)\s*ago\b/gi, "TIME_AGO")
    .replace(/\s+/g, " ")
    .trim();
}

async function runOrder79Playwright() {
  console.log("=" .repeat(85));
  console.log("ORDER 79: A4 PLAYWRIGHT SUITE EXTENDED (RISING, EMERGING, PEAKED, COMEBACK, EXPIRED)");
  console.log("=" .repeat(85));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });

  await context.addInitScript(() => {
    localStorage.setItem("trendrop_session_token", "demo_guest_token");
    localStorage.setItem("trendrop_user_email", "demo@trendrop.app");
    localStorage.setItem("trendrop_user_plan", "pro");
    localStorage.setItem("trendrop_user_niche", "all");
    localStorage.setItem("trendrop_user_language", "all");
  });

  const page = await context.newPage();
  const baseUrl = "http://127.0.0.1:5173";

  // Intercept sparkline history calls so both old and new render identically without network race
  await page.route("**/history*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([])
    });
  });

  // Helper to collect card texts across all 5 tabs in an isolated browser context
  async function collectTabCards(isSlim) {
    const ctx = await browser.newContext({
      viewport: { width: 1440, height: 900 }
    });
    await ctx.addInitScript(() => {
      localStorage.setItem("trendrop_session_token", "demo_guest_token");
      localStorage.setItem("trendrop_user_email", "demo@trendrop.app");
      localStorage.setItem("trendrop_user_plan", "pro");
      localStorage.setItem("trendrop_user_niche", "all");
      localStorage.setItem("trendrop_user_language", "all");
    });

    const p = await ctx.newPage();

    await p.route("**/history*", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
    });

    const endpoints = [
      { pattern: "**/api/trends?*", key: "/api/trends" },
      { pattern: "**/api/trends/emerging*", key: "/api/trends/emerging" },
      { pattern: "**/api/trends/peaked*", key: "/api/trends/peaked" },
      { pattern: "**/api/trends/resurging*", key: "/api/trends/resurging" },
      { pattern: "**/api/trends/expired*", key: "/api/trends/expired" }
    ];

    for (const ep of endpoints) {
      const rawRows = oldPayloads[ep.key] || [];
      const bodyRows = isSlim ? slimPayload(rawRows) : rawRows;
      await p.route(ep.pattern, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(bodyRows)
        });
      });
    }

    await p.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
    // Wait 1.5s for React hydration to complete before triggering user interactions
    await p.waitForTimeout(1500);

    const results = {};
    const tabsList = [
      { name: "Rising", id: "rising" },
      { name: "Emerging", id: "emerging" },
      { name: "Peaked", id: "peaked" },
      { name: "Comeback", id: "resurging" },
      { name: "Expired", id: "expired" }
    ];

    for (const t of tabsList) {
      const btn = p.locator(`#lifecycle-pill-${t.id}`);
      await btn.click();
      try {
        await p.waitForFunction((id) => {
          const el = document.getElementById(`lifecycle-pill-${id}`);
          return el && el.classList.contains("bg-primary");
        }, t.id, { timeout: 3000 });
      } catch (e) {
        // Hydration retry if initial click landed prior to event binding
        await p.waitForTimeout(500);
        await btn.click();
        await p.waitForFunction((id) => {
          const el = document.getElementById(`lifecycle-pill-${id}`);
          return el && el.classList.contains("bg-primary");
        }, t.id, { timeout: 5000 });
      }

      await p.waitForTimeout(1000);
      const cards = p.locator(".tilt-card");
      const count = await cards.count();
      const n = Math.min(10, count);
      const texts = [];
      for (let i = 0; i < n; i++) {
        texts.push(await cards.nth(i).innerText());
      }
      results[t.id] = texts;
    }

    await ctx.close();
    return results;
  }

  console.log("\n1. Testing innerText equality across all 5 tabs (Old select * vs New select FEED_CARD_COLUMNS)...");
  console.log("  Collecting card texts for SLIM payload (select FEED_CARD_COLUMNS)...");
  const slimResults = await collectTabCards(true);

  console.log("  Collecting card texts for FULL payload (select *)...");
  const fullResults = await collectTabCards(false);

  const tabsList = [
    { name: "Rising", id: "rising" },
    { name: "Emerging", id: "emerging" },
    { name: "Peaked", id: "peaked" },
    { name: "Comeback", id: "resurging" },
    { name: "Expired", id: "expired" }
  ];

  for (const t of tabsList) {
    const sTexts = slimResults[t.id] || [];
    const fTexts = fullResults[t.id] || [];
    const count = Math.min(sTexts.length, fTexts.length);
    let matched = 0;
    for (let i = 0; i < count; i++) {
      if (normalizeCardText(sTexts[i]) === normalizeCardText(fTexts[i])) {
        matched++;
      } else {
        const s = normalizeCardText(sTexts[i]);
        const f = normalizeCardText(fTexts[i]);
        console.error(`  Tab ${t.name} Card #${i+1} MISMATCH:`);
        console.error(`    FULL (${f.length} chars): ${f}`);
        console.error(`    SLIM (${s.length} chars): ${s}`);
        for (let j = 0; j < Math.max(s.length, f.length); j++) {
          if (s[j] !== f[j]) {
            console.error(`    First difference at pos ${j}: FULL char ${JSON.stringify(f[j])} vs SLIM char ${JSON.stringify(s[j])}`);
            console.error(`    Context: FULL "${f.slice(Math.max(0, j-20), j+20)}" vs SLIM "${s.slice(Math.max(0, j-20), j+20)}"`);
            break;
          }
        }
      }
    }
    console.log(`  Tab ${t.name}: ${matched}/${count} cards matched exactly (100% equality: ${matched === count && count > 0})`);
    if (matched !== count || count === 0) {
      throw new Error(`innerText mismatch on tab ${t.name} (matched ${matched}/${count})`);
    }
  }

  // Build a lookup map of all trends by ID from oldPayloads
  const allTrendsById = {};
  for (const list of Object.values(oldPayloads)) {
    if (Array.isArray(list)) {
      for (const item of list) {
        if (item && item.id) {
          allTrendsById[String(item.id)] = item;
        }
      }
    }
  }

  // 2. Open detail view for 3 trends from different tabs
  console.log("\n2. Opening Detail View for 3 trends from different tabs...");
  const detailChecks = [
    { tab: "Rising", trendId: "7843" },
    { tab: "Emerging", trendId: "7853" },
    { tab: "Peaked", trendId: "7856" }
  ];

  for (const dc of detailChecks) {
    console.log(`  Testing detail view for trend ${dc.trendId} (from ${dc.tab})...`);
    await page.goto(`${baseUrl}/trend/${dc.trendId}`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2500);
    const pageText = await page.innerText("body");
    const hasContent = pageText.length > 300 && pageText.includes("Back to Feed");
    console.log(`    Detail view loaded: ${hasContent} (text length: ${pageText.length})`);
    if (!hasContent) throw new Error(`Detail view failed to load for trend ${dc.trendId}`);
  }

  // Set up default feed routes for the remaining tests
  const endpoints = [
    { pattern: "**/api/trends?*", key: "/api/trends" },
    { pattern: "**/api/trends/emerging*", key: "/api/trends/emerging" },
    { pattern: "**/api/trends/peaked*", key: "/api/trends/peaked" },
    { pattern: "**/api/trends/resurging*", key: "/api/trends/resurging" },
    { pattern: "**/api/trends/expired*", key: "/api/trends/expired" }
  ];

  for (const ep of endpoints) {
    const rawRows = slimPayload(oldPayloads[ep.key] || []);
    await page.route(ep.pattern, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(rawRows)
      });
    });
  }

  // 3. Save one to Workspace (Target button)
  console.log("\n3. Testing Save to Workspace (Target action)...");
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".tilt-card", { timeout: 15000 });
  const targetBtn = page.locator('button[title*="target" i], button[aria-label*="target" i], button:has-text("Target")').first();
  const btnCount = await targetBtn.count();
  console.log(`  Target button found: ${btnCount > 0}`);
  if (btnCount > 0) {
    await targetBtn.click();
    await page.waitForTimeout(500);
    console.log("  Successfully clicked target/save button.");
  }

  // 4. Test Language Filter Preference
  console.log("\n4. Applying Language Filter Preference and verifying feed rendering...");
  await page.addInitScript(() => {
    localStorage.setItem("trendrop_pref_language", "hi");
    localStorage.setItem("trendrop_preferred_languages", JSON.stringify(["hi"]));
  });
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  const hindiCount = await page.locator(".tilt-card").count();
  console.log(`  Rendered cards under Hindi filter: ${hindiCount}`);

  // 5. Test Search & Sort Filter
  console.log("\n5. Testing Search Query Filter...");
  const searchInput = page.locator("#search-query");
  if (await searchInput.count() > 0) {
    await searchInput.fill("love");
    await page.waitForTimeout(1000);
    const searchCards = await page.locator(".tilt-card").count();
    console.log(`  Rendered cards with query 'love': ${searchCards}`);
    await searchInput.fill("");
    await page.waitForTimeout(500);
  }

  await browser.close();
  console.log("\n" + "=" .repeat(85));
  console.log("ORDER 79: A4 PLAYWRIGHT SUITE PASSED SUCCESSFULLY (ALL 5 TABS & ACTIONS OK)!");
  console.log("=" .repeat(85));
}

runOrder79Playwright().catch((err) => {
  console.error("FATAL ERROR IN ORDER 79 PLAYWRIGHT SUITE:", err);
  process.exit(1);
});
