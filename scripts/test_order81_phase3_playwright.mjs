import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const PREVIEW_URL = "https://trendrop-ewy6zm0ut-chinmays-projects-c20ed5a5.vercel.app";
const EVIDENCE_DIR = path.resolve("evidence/order81");
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

  const page = await context.newPage();
  const logEntries = [];
  function log(msg) {
    console.log(msg);
    logEntries.push(msg);
  }

  log(`--- ORDER 81 PHASE 3 PLAYWRIGHT VERIFICATION ---`);
  log(`Preview URL: ${PREVIEW_URL}`);
  log(`Timestamp: ${new Date().toISOString()}`);

  const startTime = Date.now();
  await page.goto(PREVIEW_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  log(`DOM Content Loaded in ${Date.now() - startTime}ms`);

  // Wait for initial render or card
  try {
    await page.waitForSelector("[data-testid='deck-card-face'], [data-testid='deck-empty'], [data-testid='deck-view']", { timeout: 15000 });
    const firstCardTime = Date.now() - startTime;
    log(`First Deck View / Card Visible: ${firstCardTime}ms (Target: < 2000ms)`);
  } catch (e) {
    log(`Card selector wait warning: ${e.message}`);
  }

  await page.waitForTimeout(2000); // Allow render to settle

  // Take screenshot of initial Deck view
  const deckViewPath = path.join(EVIDENCE_DIR, "phase3_deck_view.png");
  await page.screenshot({ path: deckViewPath, fullPage: false });
  log(`Saved screenshot: ${deckViewPath}`);

  // Check card elements
  const cardFace = await page.$("[data-testid='deck-card-face']");
  if (cardFace) {
    const title = await page.$eval("[data-testid='card-title']", el => el.textContent.trim()).catch(() => "N/A");
    const artist = await page.$eval("[data-testid='card-artist']", el => el.textContent.trim()).catch(() => "N/A");
    const stagePill = await page.$eval("[data-testid='card-stage-pill']", el => el.textContent.trim()).catch(() => "N/A");
    const proofLine = await page.$eval("[data-testid='card-proof-line']", el => el.textContent.trim()).catch(() => "N/A");
    const groundedLine = await page.$eval("[data-testid='card-grounded-line']", el => el.textContent.trim()).catch(() => "N/A");

    log(`Top Card Title: "${title}"`);
    log(`Top Card Artist: "${artist}"`);
    log(`Top Card Stage Pill: "${stagePill}"`);
    log(`Top Card Proof Line: "${proofLine}"`);
    log(`Top Card Grounded Reason: "${groundedLine}"`);

    // Count interactive elements on card face
    const interactiveElements = await cardFace.$$("button, a, input, select, textarea, [role='button'], [tabindex='0']");
    log(`Interactive elements count on card face: ${interactiveElements.length} (Requirement: <= 6)`);

    // Test Opening Info Sheet
    const infoBtn = await page.$("#card-info-btn");
    if (infoBtn) {
      log(`Tapping Info Button (#card-info-btn)...`);
      await infoBtn.click();
      await page.waitForTimeout(800);
      const infoSheetPath = path.join(EVIDENCE_DIR, "phase3_info_sheet.png");
      await page.screenshot({ path: infoSheetPath, fullPage: false });
      log(`Saved Info Sheet screenshot: ${infoSheetPath}`);

      const proofReelsCount = await page.$$eval("[data-testid='proof-reel-item']", els => els.length).catch(() => 0);
      const timelineVisible = await page.$eval("[data-testid='card-timeline']", el => el.textContent.trim()).catch(() => "N/A");
      const igLink = await page.$eval("[data-testid='card-outbound-ig']", el => el.getAttribute("href")).catch(() => "N/A");

      log(`Proof Reels in Info Sheet: ${proofReelsCount} items`);
      log(`Timeline text: "${timelineVisible}"`);
      log(`Outbound IG Link: "${igLink}"`);

      // Close info sheet
      const closeBtn = await page.$("#info-sheet-close");
      if (closeBtn) {
        await closeBtn.click();
        await page.waitForTimeout(500);
      }
    }

    // Test Skip Interaction
    const skipBtn = await page.$("#card-skip-btn");
    if (skipBtn) {
      log(`Tapping Skip Button (#card-skip-btn)...`);
      await skipBtn.click();
      await page.waitForTimeout(800);
      const newTitle = await page.$eval("[data-testid='card-title']", el => el.textContent.trim()).catch(() => "None/Empty");
      log(`Next Card Title after Skip: "${newTitle}"`);
    }

    // Test Undo Interaction
    const undoBtn = await page.$("#card-undo-btn");
    if (undoBtn) {
      log(`Tapping Undo Button (#card-undo-btn)...`);
      await undoBtn.click();
      await page.waitForTimeout(800);
      const restoredTitle = await page.$eval("[data-testid='card-title']", el => el.textContent.trim()).catch(() => "None/Empty");
      log(`Restored Card Title after Undo: "${restoredTitle}"`);
    }
  } else {
    log(`Note: No deck card face found directly (check if login wall or caught-up state)`);
  }

  // Test Explore Tab
  log(`Switching to Explore Tab...`);
  const exploreTabBtn = await page.$("a[href*='tab=explore'], button:has-text('Explore')");
  if (exploreTabBtn) {
    await exploreTabBtn.click();
    await page.waitForTimeout(1500);
    const exploreShotPath = path.join(EVIDENCE_DIR, "phase3_explore_view.png");
    await page.screenshot({ path: exploreShotPath, fullPage: false });
    log(`Saved Explore View screenshot: ${exploreShotPath}`);

    const searchInput = await page.$("#explore-ai-search");
    const stagePills = await page.$$eval("[data-testid='explore-stage-pill']", els => els.length).catch(() => 0);
    const nicheChips = await page.$$eval("[data-testid='explore-niche-chip']", els => els.length).catch(() => 0);
    const radarItems = await page.$$eval("[data-testid='radar-row-item']", els => els.length).catch(() => 0);

    log(`Explore AI Search Input Present: ${!!searchInput}`);
    log(`Explore Stage Pills Count: ${stagePills}`);
    log(`Explore Niche Chips Count: ${nicheChips}`);
    log(`Radar Early Signals Count: ${radarItems}`);
  }

  // Test Picks Tab
  log(`Switching to Picks Tab...`);
  const picksTabBtn = await page.$("a[href*='tab=picks'], button:has-text('Picks')");
  if (picksTabBtn) {
    await picksTabBtn.click();
    await page.waitForTimeout(1500);
    const picksShotPath = path.join(EVIDENCE_DIR, "phase3_picks_view.png");
    await page.screenshot({ path: picksShotPath, fullPage: false });
    log(`Saved Picks View screenshot: ${picksShotPath}`);

    const picksCards = await page.$$eval("[data-testid='picks-item']", els => els.length).catch(() => 0);
    log(`Picks Items Count: ${picksCards}`);
  }

  // Write Evidence File
  const reportPath = path.join(EVIDENCE_DIR, "phase3_frontend_rebuild.txt");
  fs.writeFileSync(reportPath, logEntries.join("\n"), "utf-8");
  log(`Saved full report to ${reportPath}`);

  await browser.close();
}

run().catch(err => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
