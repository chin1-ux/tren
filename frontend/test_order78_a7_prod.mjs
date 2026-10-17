import { chromium } from "playwright";

async function runA7Prod() {
  console.log("=" .repeat(85));
  console.log("ORDER 78: A7 PLAYWRIGHT COLD LOAD BASELINE (PRODUCTION: trendrop-black.vercel.app)");
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

  const apiCalls = [];
  page.on("response", async (res) => {
    const url = res.url();
    if (url.includes("/api/")) {
      let bodyBytes = 0;
      try {
        const buffer = await res.body();
        bodyBytes = buffer.length;
      } catch (e) {
        // body could be empty or stream closed
      }
      apiCalls.push({
        url: url,
        status: res.status(),
        bytes: bodyBytes
      });
    }
  });

  console.log("Cold Page Load on Production Homepage (https://trendrop-black.vercel.app)...");
  await page.goto("https://trendrop-black.vercel.app/", { waitUntil: "networkidle" });
  await page.waitForTimeout(3000);

  console.log("\n========================================================");
  console.log("COLD LOAD /api/ CALLS WITH STATUS AND BYTES (PRODUCTION):");
  console.log("========================================================");
  console.table(apiCalls);

  const totalBytes = apiCalls.reduce((acc, c) => acc + c.bytes, 0);
  console.log(`Total Production Cold Load /api/ Transfer: ${totalBytes} bytes (${(totalBytes / 1024).toFixed(2)} KB)`);

  await browser.close();
  console.log("\n" + "=" .repeat(85));
  console.log("A7 PRODUCTION BASELINE MEASUREMENT COMPLETED");
  console.log("=" .repeat(85));
}

runA7Prod().catch((err) => {
  console.error("FATAL ERROR IN A7 PROD MEASUREMENT:", err);
  process.exit(1);
});
