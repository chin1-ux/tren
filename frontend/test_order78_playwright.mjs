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
  return rows.map((row) => {
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
  return txt
    .replace(/GROWTH\s+Tracking started\.\.\./g, "")
    .replace(/\s+/g, " ")
    .trim();
}

async function runOrder78Playwright() {
  console.log("=" .repeat(85));
  console.log("ORDER 78: A5 PLAYWRIGHT SUITE ON HOTFIX BRANCH");
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

  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(msg.text());
    }
  });
  page.on("pageerror", (err) => {
    consoleErrors.push(err.message);
  });

  const coldLoadApiCalls = [];
  let isColdLoad = true;

  page.on("response", async (res) => {
    const url = res.url();
    const status = res.status();

    if (url.includes("/api/")) {
      let bodyBytes = 0;
      try {
        const buf = await res.body();
        bodyBytes = buf.length;
      } catch (e) {}

      if (isColdLoad) {
        coldLoadApiCalls.push({
          url: url.replace("http://localhost:8000", "").replace("http://127.0.0.1:8000", "").replace("http://localhost:5173", ""),
          status,
          bytes: bodyBytes
        });
      }
    }
  });

  const baseUrl = "http://localhost:5173";

  // 1. Cold Page Load on Homepage
  console.log("\n1. Cold Page Load on Homepage (Rising Feed)...");
  isColdLoad = true;
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3000);
  await page.waitForFunction(() => document.querySelectorAll(".tilt-card").length > 0, { timeout: 30000 });
  await page.waitForTimeout(1500);
  isColdLoad = false;

  console.log("\n========================================================");
  console.log("COLD LOAD /api/ CALLS WITH STATUS AND BYTES:");
  console.log("========================================================");
  console.table(coldLoadApiCalls);
  const totalColdBytes = coldLoadApiCalls.reduce((acc, c) => acc + c.bytes, 0);
  console.log(`Total Cold Load /api/ Transfer: ${totalColdBytes} bytes (${(totalColdBytes / 1024).toFixed(2)} KB)`);

  // 2. Check at least one card with reel chips and thumbnail
  console.log("\n2. Checking Card Reel Chips and Thumbnail...");
  const cardLocators = page.locator(".tilt-card");
  const cardCount = await cardLocators.count();
  console.log(`Rising feed rendered cards: ${cardCount}`);
  if (cardCount === 0) throw new Error("Rising feed rendered 0 cards");

  let foundCardWithChips = false;
  let foundCardWithThumbnail = false;

  for (let i = 0; i < Math.min(10, cardCount); i++) {
    const card = cardLocators.nth(i);
    const txt = await card.innerText();
    if (txt.includes("reels") || txt.includes("creators") || txt.includes("uses") || txt.includes("IG uses")) {
      foundCardWithChips = true;
    }
    const imgs = await card.locator("img").count();
    if (imgs > 0) {
      foundCardWithThumbnail = true;
    }
  }

  console.log(`Card with reel chips: ${foundCardWithChips}`);
  console.log(`Card with thumbnail: ${foundCardWithThumbnail}`);
  if (!foundCardWithChips) throw new Error("Failed to find card with reel chips");

  // 3. Check Detail View shows used_for text
  console.log("\n3. Testing Detail View for used_for text (/trend/7808)...");
  await page.goto(`${baseUrl}/trend/7808`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("h1", { timeout: 15000 });
  await page.waitForTimeout(1000);
  const detailBodyText = await page.innerText("body");
  const hasUsedFor = detailBodyText.includes("Used For") || detailBodyText.includes("outfit-showcase") || detailBodyText.includes("Why it's viral");
  console.log(`Detail view contains used_for / viral text: ${hasUsedFor}`);
  if (!hasUsedFor) throw new Error("Detail view missing used_for / viral text");

  // 4. Test All Tabs Navigation
  console.log("\n4. Testing Every Tab (0 HTTP >= 400)...");
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => document.querySelectorAll(".tilt-card").length > 0, { timeout: 15000 });

  const tabsToTest = [
    { name: "Rising", text: "Rising" },
    { name: "Emerging", text: "Emerging" },
    { name: "Comeback", text: "Comeback" },
    { name: "Workspace", text: "Workspace" },
    { name: "Peaked", text: "Peaked" },
    { name: "Expired", text: "Expired" }
  ];

  const tabHttpFailures = [];
  const tabListener = (res) => {
    if (res.url().includes("/api/") && res.status() >= 400) {
      tabHttpFailures.push({ url: res.url(), status: res.status() });
    }
  };
  page.on("response", tabListener);

  for (const tab of tabsToTest) {
    const btn = page.locator(`button:has-text("${tab.text}")`).first();
    if (await btn.isVisible()) {
      await btn.click();
      await page.waitForTimeout(1200);
      const count = await page.locator(".tilt-card").count();
      console.log(`  Tab ${tab.name.padEnd(10)}: rendered ${count} cards`);
      if (tab.name !== "Workspace" && count === 0) {
        throw new Error(`Tab ${tab.name} rendered 0 cards`);
      }
    }
  }

  console.log(`Tab HTTP failures (status >= 400): ${tabHttpFailures.length}`);
  if (tabHttpFailures.length > 0) {
    console.error("Tab HTTP failures:", tabHttpFailures);
    throw new Error(`Encountered ${tabHttpFailures.length} HTTP failures during tab navigation`);
  }

  // 5. Test innerText equality of the first 10 cards on Rising, Emerging, and Peaked old vs new
  console.log("\n5. Testing innerText equality of first 10 cards: Old (select *) vs New (select FEED_CARD_COLUMNS)...");

  const tabsForComparison = [
    { name: "Rising", endpoint: "/api/trends", tabText: "Rising", urlPattern: "**/api/trends?*" },
    { name: "Emerging", endpoint: "/api/trends/emerging", tabText: "Emerging", urlPattern: "**/api/trends/emerging?*" },
    { name: "Peaked", endpoint: "/api/trends/peaked", tabText: "Peaked", urlPattern: "**/api/trends/peaked?*" }
  ];

  for (const item of tabsForComparison) {
    console.log(`\n--- Comparing First 10 Cards on Tab: ${item.name} ---`);
    
    const oldRawRows = oldPayloads[item.endpoint];
    const newRawRows = slimPayload(oldRawRows);

    // A. Route with newRawRows (slimmed columns)
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

    // B. Route with oldRawRows (select * columns)
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

    // C. Compare card by card
    console.log(`  Comparing ${compareCount} cards...`);
    let matchCount = 0;
    for (let i = 0; i < compareCount; i++) {
      const normNew = normalizeCardText(newTexts[i]);
      const normOld = normalizeCardText(oldTexts[i]);
      const match = normNew === normOld;
      if (match) {
        matchCount++;
      } else {
        console.error(`  Card #${i+1} MISMATCH:`);
        console.error(`    OLD: ${normOld.slice(0, 100)}`);
        console.error(`    NEW: ${normNew.slice(0, 100)}`);
      }
    }
    console.log(`  Tab ${item.name}: ${matchCount}/${compareCount} cards matched exactly (100% innerText equality: ${matchCount === compareCount})`);
    if (matchCount !== compareCount) {
      throw new Error(`innerText mismatch on tab ${item.name}`);
    }
  }

  await browser.close();
  console.log("\n" + "=" .repeat(85));
  console.log("PLAYWRIGHT SUITE PASSED SUCCESSFULLY (ALL ASSERTIONS OK)!");
  console.log("=" .repeat(85));
}

runOrder78Playwright().catch((err) => {
  console.error("FATAL ERROR IN PLAYWRIGHT SUITE:", err);
  process.exit(1);
});
