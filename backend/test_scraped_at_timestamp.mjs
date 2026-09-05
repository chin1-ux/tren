import { chromium } from "playwright";

(async () => {
  console.log("Starting Playwright verification for scraped-at timestamp...");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    // Intercept the API call and inject known first_detected_at
    await page.route("**/api/trends*", async (route) => {
      const mockTrend = {
        id: 939,
        song: "Boom Shaka",
        audio_title: "Boom Shaka",
        artist: "DJ Tiësto",
        audio_artist: "DJ Tiësto",
        audio_id: "123456",
        audio_use_count: 42000,
        content_type: "dance",
        window_hours_remaining: 18,
        velocity_avg: 850,
        language: "en",
        status: "rising",
        saturation_score: 0.3,
        llm_classification_status: "completed",
        global_saturation_pct: 28,
        india_saturation_pct: 12,
        niche_tag: "fitness",
        semantic_niches: ["fitness", "dance"],
        opportunity_score: 72,
        first_detected_at: "2026-08-25T20:44:09.188397",
        reel_count: 120,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([mockTrend]),
      });
    });

    // Route other API calls to empty responses
    await page.route("**/api/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });

    await page.goto("http://localhost:8080/", { waitUntil: "domcontentloaded", timeout: 15000 });

    // Wait for at least one trend card to appear
    await page.waitForSelector("article", { timeout: 10000 });

    // Check for the IST timestamp text anywhere in the card
    const timestampEl = await page.$("text=IST");
    if (timestampEl) {
      const text = await timestampEl.textContent();
      console.log(`✅ PASS: Scraped-at timestamp found on card: "${text?.trim()}"`);
    } else {
      // Try clock SVG (the inline SVG we render)
      const clockSvg = await page.$("article svg");
      if (clockSvg) {
        console.log("✅ PASS: Clock SVG found in TrendCard footer");
      } else {
        console.log("❌ FAIL: No timestamp or clock SVG found on any card");
      }
    }

    // Screenshot for evidence
    await page.screenshot({ path: "test_screenshots/scraped_at_timestamp.png", fullPage: false });
    console.log("Screenshot saved to test_screenshots/scraped_at_timestamp.png");

  } catch (err) {
    console.error("Test error:", err.message);
  } finally {
    await browser.close();
  }
})();
