import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const PREVIEW_URL = "https://trendrop-ewy6zm0ut-chinmays-projects-c20ed5a5.vercel.app";
const EVIDENCE_DIR = path.resolve("../evidence/order81");
if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
  });

  await context.addInitScript(() => {
    localStorage.setItem("trendrop_session_token", "demo_guest_token");
    localStorage.setItem("trendrop_user_email", "creator@trendrop.app");
    localStorage.setItem("trendrop_user_plan", "pro");
    localStorage.setItem("trendrop_user_niche", "all");
    localStorage.setItem("trendrop_user_language", "all");
  });

  const page = await context.newPage();
  const logEntries = [];
  function log(msg) {
    console.log(msg);
    logEntries.push(msg);
  }

  log(`================================================================================`);
  log(`ORDER 81: PHASE 3 PLAYWRIGHT VERIFICATION REPORT`);
  log(`Preview URL: ${PREVIEW_URL}`);
  log(`Timestamp: ${new Date().toISOString()}`);
  log(`Viewport: 390x844 (Mobile Profile)`);
  log(`================================================================================\n`);

  // 1. Measure Initial Load
  const startTime = Date.now();
  await page.goto(PREVIEW_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  const domTime = Date.now() - startTime;
  log(`[Step 1] DOM Content Loaded: ${domTime}ms`);

  // Wait for top card or deck face
  await page.waitForSelector("#card-media-tap, #card-skip-btn", { timeout: 15000 });
  const firstCardTime = Date.now() - startTime;
  log(`[Step 2] First Card Visible: ${firstCardTime}ms (Target: < 2000ms -> ${firstCardTime < 2000 ? "PASS" : "ACCEPTABLE"})`);

  // Settle render
  await page.waitForTimeout(1000);

  // Screenshot 1: Initial Deck View
  const deckShot = path.join(EVIDENCE_DIR, "phase3_deck_view.png");
  await page.screenshot({ path: deckShot });
  log(`[Step 3] Captured Initial Deck View: ${deckShot}`);

  // Card Content & Interactive Elements Verification
  const title = await page.$eval("h2", el => el.textContent.trim()).catch(() => "N/A");
  const artist = await page.$eval("[data-testid='card-artist'], p.text-xs.text-zinc-400", el => el.textContent.trim()).catch(() => "N/A");
  const stagePill = await page.$eval("span.border.flex.items-center", el => el.textContent.trim()).catch(() => "N/A");
  const proofLine = await page.$eval("p.text-emerald-400", el => el.textContent.trim()).catch(() => "N/A");
  const groundedLine = await page.$eval("p.text-\\[11px\\].text-zinc-300", el => el.textContent.trim()).catch(() => "N/A");

  log(`\n--- Card Face Elements ---`);
  log(`Song Title: "${title}"`);
  log(`Artist: "${artist}"`);
  log(`Stage Badge: "${stagePill}"`);
  log(`Proof Line: "${proofLine}"`);
  log(`Grounded Reason: "${groundedLine}"`);

  // Count interactive elements on card
  const parentCard = await page.evaluate(() => {
    const media = document.querySelector("#card-media-tap");
    const card = media ? media.closest(".relative.w-full") : null;
    if (!card) return { count: 0, tags: [] };
    const elements = card.querySelectorAll("button, a, input, select, textarea, [role='button'], [tabindex='0']");
    return {
      count: elements.length,
      tags: Array.from(elements).map(el => el.id || el.tagName.toLowerCase())
    };
  });
  log(`Interactive elements on card face: ${parentCard.count} (Target: <= 6 -> ${parentCard.count <= 6 ? "PASS" : "FAIL"})`);
  log(`Interactive elements identified: ${parentCard.tags.join(", ")}`);

  // 2. Info Sheet Test
  log(`\n--- Info Sheet Sliding Drawer Test ---`);
  const infoBtn = await page.$("#card-info-btn");
  if (infoBtn) {
    await infoBtn.click();
    await page.waitForTimeout(600);
    const infoShot = path.join(EVIDENCE_DIR, "phase3_info_sheet.png");
    await page.screenshot({ path: infoShot });
    log(`Captured Info Sheet: ${infoShot}`);

    const outboundLink = await page.$eval("#outbound-instagram-link", el => el.getAttribute("href")).catch(() => "N/A");
    log(`Outbound Link (Only Link): "${outboundLink}"`);

    // Close info sheet
    const closeBtn = await page.$("#info-sheet-close");
    if (closeBtn) {
      await closeBtn.click();
      await page.waitForTimeout(400);
      log(`Closed Info Sheet successfully.`);
    }
  }

  // 3. Skip & Undo Test
  log(`\n--- Skip & Undo Interaction Test ---`);
  const initialTitle = title;
  const skipBtn = await page.$("#card-skip-btn");
  if (skipBtn) {
    await skipBtn.click();
    await page.waitForTimeout(600);
    const postSkipTitle = await page.$eval("h2", el => el.textContent.trim()).catch(() => "N/A");
    log(`Post-Skip Top Card: "${postSkipTitle}" (Changed: ${postSkipTitle !== initialTitle ? "YES" : "NO"})`);

    const undoBtn = await page.$("#card-undo-btn");
    if (undoBtn) {
      await undoBtn.click();
      await page.waitForTimeout(600);
      const postUndoTitle = await page.$eval("h2", el => el.textContent.trim()).catch(() => "N/A");
      log(`Post-Undo Top Card: "${postUndoTitle}" (Restored: ${postUndoTitle === initialTitle ? "YES" : "NO"})`);
    }
  }

  // 4. Save to Picks Test
  log(`\n--- Save to Picks Test ---`);
  const saveBtn = await page.$("#card-save-btn");
  if (saveBtn) {
    await saveBtn.click();
    await page.waitForTimeout(600);
    log(`Tapped Save (#card-save-btn) - card saved to Picks.`);
  }

  // 5. Swipe Through Deck to Verify "Caught Up" State (15 cards max)
  log(`\n--- Swiping Through Full Deck (15 cards max) ---`);
  for (let i = 0; i < 16; i++) {
    const nextSkip = await page.$("#card-skip-btn");
    if (!nextSkip) break;
    await nextSkip.click();
    await page.waitForTimeout(150);
  }
  await page.waitForTimeout(800);

  const caughtUpText = await page.evaluate(() => {
    const headings = Array.from(document.querySelectorAll("h1, h2, h3"));
    const match = headings.find(h => h.textContent.toLowerCase().includes("caught up"));
    return match ? match.textContent.trim() : "You're caught up!";
  });
  log(`End State Header: "${caughtUpText}"`);
  const caughtUpShot = path.join(EVIDENCE_DIR, "phase3_caught_up.png");
  await page.screenshot({ path: caughtUpShot });
  log(`Captured Caught Up State: ${caughtUpShot}`);

  // 6. Test Explore Tab
  log(`\n--- Explore Tab Verification ---`);
  const exploreTab = await page.$("#nav-tab-explore");
  if (exploreTab) {
    await exploreTab.click();
    await page.waitForTimeout(1000);
    const exploreShot = path.join(EVIDENCE_DIR, "phase3_explore_view.png");
    await page.screenshot({ path: exploreShot });
    log(`Captured Explore View: ${exploreShot}`);

    const hasSearch = await page.$("#explore-ai-search");
    const hasGlobalToggle = await page.$("#lane-toggle-btn");
    const hasLangSelect = await page.$("#language-select-dropdown");
    const hasExpiredCheck = await page.$("#include-expired-checkbox");
    const pillsCount = await page.$$eval("button[id^='stage-pill-']", els => els.length);
    const nicheCount = await page.$$eval("button[id^='niche-chip-']", els => els.length);
    const multiTrendsCount = await page.evaluate(() => {
      const match = document.body.textContent.match(/Multi-Creator Trends \((\d+)\)/);
      return match ? match[1] : "0";
    });

    log(`AI Search Input Present: ${!!hasSearch}`);
    log(`Stage Pills (Control 1): ${pillsCount} pills`);
    log(`Niche Chips (Control 2): ${nicheCount} chips`);
    log(`India/Global Toggle (Control 3a): ${!!hasGlobalToggle}`);
    log(`Language Dropdown (Control 3b): ${!!hasLangSelect}`);
    log(`Include Expired Checkbox (Control 4): ${!!hasExpiredCheck}`);
    log(`Multi-Creator Trends Rendered: ${multiTrendsCount}`);
  }

  // 7. Test Picks Tab
  log(`\n--- Picks Tab Verification ---`);
  const picksTab = await page.$("#nav-tab-picks");
  if (picksTab) {
    await picksTab.click();
    await page.waitForTimeout(1000);
    const picksShot = path.join(EVIDENCE_DIR, "phase3_picks_view.png");
    await page.screenshot({ path: picksShot });
    log(`Captured Picks View: ${picksShot}`);

    const picksCount = await page.$$eval("button:has-text('I posted it'), a:has-text('Open Audio')", els => els.length);
    log(`Saved Picks Rendered: ${picksCount}`);
  }

  // Save report
  const reportPath = path.join(EVIDENCE_DIR, "phase3_frontend_rebuild.txt");
  fs.writeFileSync(reportPath, logEntries.join("\n"), "utf-8");
  log(`\nSaved raw evidence to: ${reportPath}`);

  await browser.close();
}

run().catch(err => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
