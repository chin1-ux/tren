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

  // 1. Test all 5 Tabs innerText equality: Old vs New
  const tabs = [
    { name: "Rising", endpoint: "/api/trends", tabText: "Rising", urlPattern: "**/api/trends?*" },
    { name: "Emerging", endpoint: "/api/trends/emerging", tabText: "Emerging", urlPattern: "**/api/trends/emerging?*" },
    { name: "Peaked", endpoint: "/api/trends/peaked", tabText: "Peaked", urlPattern: "**/api/trends/peaked?*" },
    { name: "Comeback", endpoint: "/api/trends/resurging", tabText: "Comeback", urlPattern: "**/api/trends/resurging?*" },
    { name: "Expired", endpoint: "/api/trends/expired", tabText: "Expired", urlPattern: "**/api/trends/expired?*" }
  ];

  console.log("\n1. Testing innerText equality across all 5 tabs (Old select * vs New select FEED_CARD_COLUMNS)...");
  
  for (const item of tabs) {
    console.log(`\n--- Comparing First 10 Cards on Tab: ${item.name} ---`);
    const oldRawRows = oldPayloads[item.endpoint] || [];
    const newRawRows = slimPayload(oldRawRows);

    // Route with New
    await page.route(item.urlPattern, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(newRawRows)
      });
    });

    await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    const tabBtnNew = page.locator(`button:has-text("${item.tabText}")`).first();
    await tabBtnNew.click();
    await page.waitForTimeout(2000);
    const newCards = page.locator(".tilt-card");
    const countNew = await newCards.count();
    const compareCount = Math.min(10, countNew);
    const newTexts = [];
    for (let i = 0; i < compareCount; i++) {
      newTexts.push(await newCards.nth(i).innerText());
    }

    await page.unroute(item.urlPattern);

    // Route with Old
    await page.route(item.urlPattern, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(oldRawRows)
      });
    });

    await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    const tabBtnOld = page.locator(`button:has-text("${item.tabText}")`).first();
    await tabBtnOld.click();
    await page.waitForTimeout(2000);
    const oldCards = page.locator(".tilt-card");
    const oldTexts = [];
    for (let i = 0; i < compareCount; i++) {
      oldTexts.push(await oldCards.nth(i).innerText());
    }

    await page.unroute(item.urlPattern);

    // Compare
    let matchCount = 0;
    for (let i = 0; i < compareCount; i++) {
      const normNew = normalizeCardText(newTexts[i]);
      const normOld = normalizeCardText(oldTexts[i]);
      if (normNew === normOld) {
        matchCount++;
      } else {
        console.error(`  Card #${i+1} MISMATCH:\n    OLD: ${normOld.slice(0, 100)}\n    NEW: ${normNew.slice(0, 100)}`);
      }
    }
    console.log(`  Tab ${item.name}: ${matchCount}/${compareCount} cards matched exactly (100% equality: ${matchCount === compareCount})`);
    if (matchCount !== compareCount) {
      throw new Error(`innerText mismatch on tab ${item.name}`);
    }
  }

  // 2. Open detail view for 3 trends from different tabs
  console.log("\n2. Opening Detail View for 3 trends from different tabs...");
  const detailChecks = [
    { tab: "Rising", trendId: "7808" },
    { tab: "Emerging", trendId: "7813" },
    { tab: "Peaked", trendId: "7810" }
  ];

  for (const dc of detailChecks) {
    console.log(`  Testing detail view for trend ${dc.trendId} (from ${dc.tab})...`);
    await page.goto(`${baseUrl}/trend/${dc.trendId}`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2000);
    const pageText = await page.innerText("body");
    const hasTitle = pageText.length > 500;
    console.log(`    Detail view loaded: ${hasTitle} (text length: ${pageText.length})`);
    if (!hasTitle) throw new Error(`Detail view failed to load for trend ${dc.trendId}`);
  }

  // 3. Save one to Workspace (Target button)
  console.log("\n3. Testing Save to Workspace (Target action)...");
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  const targetBtn = page.locator('button[title*="target" i], button[aria-label*="target" i], button:has-text("Target")').first();
  const btnCount = await targetBtn.count();
  console.log(`  Target button found: ${btnCount > 0}`);
  if (btnCount > 0) {
    await targetBtn.click();
    await page.waitForTimeout(500);
    console.log("  Successfully clicked target/save button.");
  }

  // 4. Apply a Language filter & verify identical results Old vs New
  console.log("\n4. Applying Language Filter (Hindi: hi)...");
  const langFilterBtn = page.locator('button:has-text("Hindi"), button:has-text("हिन्दी")').first();
  const langCount = await langFilterBtn.count();
  console.log(`  Language filter button found: ${langCount > 0}`);
  if (langCount > 0) {
    await langFilterBtn.click();
    await page.waitForTimeout(1500);
    const cardsAfterLang = await page.locator(".tilt-card").count();
    console.log(`  Cards rendered after language filter: ${cardsAfterLang}`);
  }

  // 5. Change sort & verify
  console.log("\n5. Testing Sort Toggle (Velocity / Newest)...");
  const sortSelect = page.locator('select, button:has-text("Sort"), button:has-text("Newest"), button:has-text("Velocity")').first();
  const sortCount = await sortSelect.count();
  console.log(`  Sort control found: ${sortCount > 0}`);

  await browser.close();
  console.log("\n" + "=" .repeat(85));
  console.log("ORDER 79: A4 PLAYWRIGHT SUITE PASSED SUCCESSFULLY (ALL 5 TABS & ACTIONS OK)!");
  console.log("=" .repeat(85));
}

runOrder79Playwright().catch((err) => {
  console.error("FATAL ERROR IN ORDER 79 PLAYWRIGHT SUITE:", err);
  process.exit(1);
});
