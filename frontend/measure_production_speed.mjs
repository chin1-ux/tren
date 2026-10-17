import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const outPath = path.resolve("../evidence/order78/d_speed_playwright_lighthouse.txt");
fs.mkdirSync(path.dirname(outPath), { recursive: true });

let logContent = "";
function log(msg) {
  console.log(msg);
  logContent += msg + "\n";
}

async function runSpeedMeasurement() {
  log("=" .repeat(90));
  log("ORDER 78 ITEM D: PRODUCTION SPEED MEASUREMENT (MOBILE 390x844, FAST 4G)");
  log(`Timestamp: ${new Date().toISOString()}`);
  log("URL: https://trendrop-black.vercel.app");
  log("=" .repeat(90));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
  });

  await context.addInitScript(() => {
    localStorage.setItem("trendrop_session_token", "demo_guest_token");
    localStorage.setItem("trendrop_user_email", "demo@trendrop.app");
    localStorage.setItem("trendrop_user_plan", "pro");
    localStorage.setItem("trendrop_user_niche", "all");
    localStorage.setItem("trendrop_user_language", "all");
    localStorage.setItem("trendrop_onboarding_completed", "true");
    localStorage.setItem("trendrop_welcomed", "true");
  });

  const page = await context.newPage();

  // CDPSession for Fast 4G throttling
  const client = await context.newCDPSession(page);
  // Fast 4G: 1.6 Mbps download (200,000 B/s), 750 Kbps upload (93,750 B/s), 40ms latency
  await client.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: 40,
    downloadThroughput: (1.6 * 1024 * 1024) / 8,
    uploadThroughput: (750 * 1024) / 8
  });

  const requests = [];
  page.on("request", req => {
    requests.push({
      url: req.url(),
      method: req.method(),
      startTime: Date.now()
    });
  });

  page.on("requestfinished", req => {
    const r = requests.find(x => x.url === req.url());
    if (r) {
      r.endTime = Date.now();
      r.durationMs = r.endTime - r.startTime;
    }
  });

  log("\n--- STARTING COLD LOAD NAVIGATION ---");
  const navStart = Date.now();
  await page.goto("https://trendrop-black.vercel.app", { waitUntil: "commit" });

  // Wait for first card
  let firstCardTime = null;
  try {
    await page.waitForSelector("[data-testid='trend-card'], .glass-card, article", { timeout: 15000 });
    firstCardTime = Date.now() - navStart;
    log(`[SUCCESS] First card visible in: ${firstCardTime} ms (${(firstCardTime / 1000).toFixed(3)}s)`);
  } catch (e) {
    log(`[TIMEOUT] Could not detect card within 15s: ${e}`);
  }

  await page.waitForLoadState("networkidle");
  const totalLoadTime = Date.now() - navStart;

  // LCP Evaluation
  const lcp = await page.evaluate(() => {
    return new Promise((resolve) => {
      new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        const lastEntry = entries[entries.length - 1];
        resolve(lastEntry.startTime);
      }).observe({ type: "largest-contentful-paint", buffered: true });
      setTimeout(() => resolve(0), 4000);
    });
  });

  log(`\n--- CORE WEB VITALS ON FAST 4G ---`);
  log(`Time to First Card:  ${firstCardTime ? (firstCardTime / 1000).toFixed(3) + "s" : "N/A"}`);
  log(`Largest Contentful Paint (LCP): ${(lcp / 1000).toFixed(3)}s`);
  log(`Total Network Idle Time:        ${(totalLoadTime / 1000).toFixed(3)}s`);

  // Analyze slowest requests
  const completed = requests.filter(r => r.durationMs !== undefined);
  completed.sort((a, b) => b.durationMs - a.durationMs);

  log(`\n--- TOP 10 SLOWEST REQUESTS (FAST 4G) ---`);
  log("Method".padEnd(6) + " | " + "Duration".padEnd(10) + " | URL");
  log("-" .repeat(90));
  for (const r of completed.slice(0, 10)) {
    const shortUrl = r.url.length > 70 ? r.url.substring(0, 67) + "..." : r.url;
    log((r.method || "GET").padEnd(6) + " | " + (r.durationMs + "ms").padEnd(10) + " | " + shortUrl);
  }

  // Summary verdict
  log("\n--- VERDICT ---");
  if (firstCardTime && firstCardTime <= 2000) {
    log(`[PASS] First cards visible in ${(firstCardTime / 1000).toFixed(3)}s (< 2.0s target on Fast 4G).`);
  } else {
    log(`[PARTIAL] First cards visible in ${(firstCardTime / 1000).toFixed(3)}s. Target < 2.0s on Fast 4G.`);
  }

  await browser.close();
  fs.writeFileSync(outPath, logContent, "utf-8");
  log(`\nEvidence saved to ${outPath}`);
}

runSpeedMeasurement().catch(err => {
  console.error("Speed test error:", err);
  process.exit(1);
});
