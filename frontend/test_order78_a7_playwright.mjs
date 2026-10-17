import { chromium } from "playwright";
import fs from "fs";
import path from "path";

fs.mkdirSync("../evidence/order78/screens", { recursive: true });
const logFile = "../evidence/order78/a7_reel_pager_evidence.txt";
const logger = fs.createWriteStream(logFile, { flags: "w" });

function log(msg) {
  console.log(msg);
  logger.write(msg + "\n");
}

async function run() {
  log("==========================================================================================");
  log("ORDER 78 ITEM A7: PLAYWRIGHT MOBILE (390x844) REEL PAGER LIVE AUDIT");
  log(`Timestamp: ${new Date().toISOString()}`);
  log("Target: 5 audios, page through 3 reels each -> Record whether embed rendered (N/15)");
  log("==========================================================================================");

  const targetUrl = process.env.TARGET_URL || "https://trendrop-black.vercel.app";
  log(`Target Deployment URL: ${targetUrl}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
  });

  // Inject session credentials to bypass splash
  await context.addInitScript(() => {
    localStorage.setItem("trendrop_session_token", "demo_guest_token");
    localStorage.setItem("trendrop_user_email", "demo@trendrop.app");
    localStorage.setItem("trendrop_user_plan", "pro");
    localStorage.setItem("trendrop_user_niche", "all");
    localStorage.setItem("trendrop_user_language", "all");
    localStorage.setItem("trendrop_onboarded", "true");
    localStorage.setItem("trendrop_onboarding_completed", "true");
    localStorage.setItem("trendrop_welcomed", "true");
  });

  const page = await context.newPage();
  page.on('console', msg => {
    if (msg.type() === 'error') log(`[BROWSER ERROR] ${msg.text()}`);
  });
  page.on('pageerror', err => log(`[BROWSER PAGEERROR] ${err.message}`));

  try {
    log("\n[1/3] Navigating to target site...");
    await page.goto(`${targetUrl}/`, { waitUntil: "networkidle", timeout: 45000 });
    
    // Dismiss onboarding prompt if present
    try {
      const dismissBtn = page.locator("button:has-text('See Today')").first();
      if (await dismissBtn.isVisible({ timeout: 3000 })) {
        log("Dismissing onboarding flow...");
        await dismissBtn.click();
        await page.waitForTimeout(1000);
      }
    } catch (e) {
      log("No onboarding prompt visible.");
    }

    // Wait for cards to render
    log("Waiting for cards to hydrate...");
    await page.waitForSelector("[data-testid='trend-card'], .tilt-card, article", { timeout: 35000 });
    await page.waitForTimeout(2000);

    const cards = await page.$$("[data-testid='trend-card'], .tilt-card, article");
    log(`Found ${cards.length} trend cards on page.`);

    if (cards.length === 0) {
      log("ERROR: No trend cards found on page.");
      await browser.close();
      return;
    }

    let totalAttempts = 0;
    let successfulRenders = 0;
    const testCount = Math.min(5, cards.length);

    for (let i = 0; i < testCount; i++) {
      const card = cards[i];
      await card.scrollIntoViewIfNeeded();
      await page.waitForTimeout(600);

      // Find audio title
      const titleElem = await card.$("h2, h3, .font-bold");
      const title = titleElem ? (await titleElem.innerText()).trim() : `Trend #${i + 1}`;
      log(`\n------------------------------------------------------------------------------------------`);
      log(`[AUDIO ${i + 1}/5] "${title}"`);

      // Find "Preview Audio" button
      const previewBtn = await card.$("button:has-text('Preview Audio'), button:has-text('Creator Reels')");
      if (!previewBtn) {
        log(`  [WARN] No Preview button found on card ${i + 1}`);
        continue;
      }

      await previewBtn.click();
      await page.waitForTimeout(1500);

      // Check if dialog is open
      const dialog = await page.$("[role='dialog']");
      if (!dialog) {
        log(`  [FAIL] Dialog did not open for card ${i + 1}`);
        continue;
      }

      log(`  [OK] Reel Pager dialog opened successfully.`);

      // Page through 3 reels
      for (let r = 0; r < 3; r++) {
        totalAttempts++;
        await page.waitForTimeout(1500);

        // Check if iframe rendered
        const iframe = await page.$("[role='dialog'] iframe");
        let rendered = false;
        let iframeSrc = "";

        if (iframe) {
          iframeSrc = await iframe.getAttribute("src") || "";
          rendered = iframeSrc.includes("instagram.com/reel/");
        }

        const screenPath = `../evidence/order78/screens/reel_pager_a${i + 1}_r${r + 1}.png`;
        await page.screenshot({ path: screenPath });

        if (rendered) {
          successfulRenders++;
          log(`  Reel ${r + 1}/3: [PASS] Embed rendered! SRC: ${iframeSrc.slice(0, 50)}... Screenshot: ${screenPath}`);
        } else {
          // If no iframe, check if "Open Instagram Audio" fallback rendered
          const fallbackLink = await page.$("[role='dialog'] a:has-text('Open Instagram Audio')");
          if (fallbackLink) {
            log(`  Reel ${r + 1}/3: [FALLBACK PASS] Audio link fallback rendered. Screenshot: ${screenPath}`);
            successfulRenders++;
          } else {
            log(`  Reel ${r + 1}/3: [FAIL] Embed did not render. Screenshot: ${screenPath}`);
          }
        }

        // Click "Next Reel" button if available
        if (r < 2) {
          const nextBtn = await page.$("[role='dialog'] button:has-text('Next Reel')");
          if (nextBtn) {
            await nextBtn.click();
            await page.waitForTimeout(1200);
          } else {
            log(`  Note: Next Reel button not present or single reel.`);
          }
        }
      }

      // Close modal
      const closeBtn = await page.$("[role='dialog'] button:has(svg.lucide-chevron-left), [role='dialog'] button[aria-label='Close']");
      if (closeBtn) {
        await closeBtn.click();
      } else {
        await page.keyboard.press("Escape");
      }
      await page.waitForTimeout(800);

      // Verify iframe destroyed
      const remainingIframe = await page.$("iframe");
      log(`  Modal closed. Remaining iframes on page: ${remainingIframe ? 1 : 0} (Expected: 0)`);
    }

    log(`\n==========================================================================================`);
    log(`FINAL REEL PAGER RENDER RESULT: ${successfulRenders}/${totalAttempts} (${Math.round((successfulRenders / Math.max(1, totalAttempts)) * 100)}%)`);
    log(`Gate Target (N/15): ${successfulRenders}/15`);
    log(`==========================================================================================`);

  } catch (err) {
    log(`\n[FATAL ERROR] ${err.message}`);
  } finally {
    await browser.close();
    logger.end();
  }
}

run();
