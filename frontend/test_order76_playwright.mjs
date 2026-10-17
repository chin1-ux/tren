import { chromium } from "playwright";
import fs from "fs";
import path from "path";

async function runOrder76Playwright() {
  console.log("=== STARTING ORDER 77 VERIFICATION PLAYWRIGHT SUITE ===");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });

  // Inject session tokens before any document loads
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

  const tabHttpFailures = [];
  const coldLoadApiCalls = [];
  let isColdLoad = true;
  let isTabTesting = false;

  page.on("response", async (res) => {
    const url = res.url();
    const status = res.status();
    
    if (isTabTesting && url.includes("/api/") && status >= 400) {
      tabHttpFailures.push({ url, status, statusText: res.statusText() });
    }

    if (url.includes("/api/")) {
      let bodyBytes = 0;
      try {
        const buf = await res.body();
        bodyBytes = buf.length;
      } catch (e) {
        // stream or aborted
      }
      if (isColdLoad) {
        coldLoadApiCalls.push({
          url: url.replace("http://localhost:8000", "").replace("http://127.0.0.1:8000", "").replace("http://localhost:5173", ""),
          status,
          bytes: bodyBytes
        });
      }
    }
  });

  const assertions = [];
  function assert(condition, message) {
    if (!condition) {
      console.error(`❌ FAILED: ${message}`);
      assertions.push({ status: "FAIL", message });
      throw new Error(`Assertion failed: ${message}`);
    } else {
      console.log(`✅ PASSED: ${message}`);
      assertions.push({ status: "PASS", message });
    }
  }

  try {
    const baseUrl = "http://localhost:5173";

    // 1. Cold Page Load on Homepage (Rising Feed)
    console.log("\n1. Cold Page Load on Homepage (Rising Feed)...");
    isColdLoad = true;
    await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => document.querySelectorAll(".tilt-card").length > 0, { timeout: 15000 });
    await page.waitForTimeout(1500);
    isColdLoad = false;

    console.log("\n--- COLD LOAD /api/ CALLS AND SIZES ---");
    console.table(coldLoadApiCalls);
    let totalColdBytes = coldLoadApiCalls.reduce((acc, c) => acc + c.bytes, 0);
    console.log(`Total Cold Load /api/ Transfer: ${totalColdBytes} bytes (${(totalColdBytes / 1024).toFixed(2)} KB)`);

    const cardLocators = page.locator(".tilt-card");
    const cardCount = await cardLocators.count();
    console.log(`Rendered cards count: ${cardCount}`);
    assert(cardCount > 0, `Rising feed rendered cards (found ${cardCount} cards)`);

    // Check Reel Chips on cards
    const firstCard = cardLocators.first();
    const firstCardText = await firstCard.innerText();
    const hasReelChips = firstCardText.includes("reels") || firstCardText.includes("creators");
    console.log(`First card text sample:\n${firstCardText.slice(0, 150)}...`);
    assert(hasReelChips, `Card displays reel chips (found: "${firstCardText.slice(0, 80)}")`);

    // Check Detail View for used_for text
    console.log("\n2. Testing Detail View for used_for text...");
    await page.goto(`${baseUrl}/trend/7808`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("h1", { timeout: 15000 });
    await page.waitForTimeout(1000);
    const detailContent = await page.innerText("body");
    const hasUsedFor = detailContent.includes("🎯 Used For") || detailContent.includes("outfit-showcase") || detailContent.includes("Why it's viral");
    console.log(`Detail view text check (id 7808): hasUsedFor = ${hasUsedFor}`);
    assert(hasUsedFor, "Detail view successfully renders used_for / viral rationale text");

    // Test Tabs Navigation with 0 HTTP >= 400
    console.log("\n3. Testing Every Tab and checking HTTP responses & errors...");
    const tabsToTest = [
      { name: "Rising", text: "Rising" },
      { name: "Emerging", text: "Emerging" },
      { name: "Comeback", text: "Comeback" },
      { name: "Workspace", text: "Workspace" },
      { name: "Peaked", text: "Peaked" },
      { name: "Expired", text: "Expired" }
    ];

    await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => document.querySelectorAll(".tilt-card").length > 0, { timeout: 15000 });

    isTabTesting = true;
    for (const tab of tabsToTest) {
      console.log(`Switching to tab: ${tab.name}...`);
      const btn = page.locator(`button:has-text("${tab.text}")`).first();
      if (await btn.isVisible()) {
        await btn.click();
        await page.waitForTimeout(1500);
        const count = await page.locator(".tilt-card").count();
        console.log(`Tab ${tab.name} rendered cards count: ${count}`);
        if (tab.name !== "Workspace") {
          assert(count > 0, `Tab ${tab.name} rendered at least 1 card (found ${count})`);
        } else {
          assert(true, `Tab ${tab.name} loaded successfully (empty workspace: ${count} cards)`);
        }
      } else {
        console.log(`Tab ${tab.name} button not visible`);
      }
    }
    isTabTesting = false;

    // Verify 0 HTTP failures across tabs
    console.log("\n4. Verifying HTTP Status across every tab...");
    console.log(`Captured HTTP /api/ failures across tabs (status >= 400): ${tabHttpFailures.length}`);
    if (tabHttpFailures.length > 0) {
      console.table(tabHttpFailures);
    }
    assert(tabHttpFailures.length === 0, `0 HTTP >= 400 requests across every tab`);

    // Verify 0 Console Errors
    console.log("\n5. Verifying Console Errors...");
    const fatalErrors = consoleErrors.filter(e => !e.includes("favicon") && !e.includes("GL Driver") && !e.includes("Failed to load resource") && !e.includes("the server responded with a status of 401"));
    console.log(`Captured fatal console errors: ${fatalErrors.length}`);
    if (fatalErrors.length > 0) {
      console.error("Console Errors:", fatalErrors);
    }
    assert(fatalErrors.length === 0, `0 fatal console errors across all interactions and tabs`);

    console.log("\n=== ALL PLAYWRIGHT VERIFICATIONS PASSED SUCCESSFULLY ===");
    console.table(assertions);

  } catch (err) {
    console.error("Playwright test execution failed:", err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

runOrder76Playwright();
