import { chromium } from 'playwright';

async function auditSpeed() {
  console.log('====================================================');
  console.log('   TRENDROP REAL PERFORMANCE & SMOOTHNESS AUDIT     ');
  console.log('====================================================\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });

  // Pre-seed authenticated demo session for seamless entry
  await context.addInitScript(() => {
    localStorage.setItem('trendrop_session_token', 'demo_guest_token');
    localStorage.setItem('trendrop_user_email', 'demo@trendrop.app');
    localStorage.setItem('trendrop_user_plan', 'pro');
    localStorage.setItem('trendrop_user_niche', 'all');
    localStorage.setItem('trendrop_user_language', 'all');
    localStorage.setItem('trendrop_theme', 'dark');
  });

  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  // 1. Initial Page Load (Cold load from Vite)
  console.log('[TEST 1] Opening App (Initial Page Load)...');
  const t0 = performance.now();
  await page.goto('http://localhost:8080/', { waitUntil: 'domcontentloaded' });
  const dclTime = performance.now() - t0;
  console.log(`  -> DOMContentLoaded: ${dclTime.toFixed(0)}ms`);

  await page.waitForSelector('.tilt-card', { timeout: 35000 });
  const firstCardTime = performance.now() - t0;
  const initialCardCount = await page.locator('.tilt-card').count();
  console.log(`  -> First Cards Visible: ${firstCardTime.toFixed(0)}ms`);
  console.log(`  -> Initial Visible Cards: ${initialCardCount}`);

  // 2. Warm Reload (Real user refreshing or returning)
  console.log('\n[TEST 2] Page Reload (Warm Cache Load)...');
  const tWarm = performance.now();
  await page.reload({ waitUntil: 'domcontentloaded' });
  const warmDcl = performance.now() - tWarm;
  console.log(`  -> Warm DOMContentLoaded: ${warmDcl.toFixed(0)}ms`);

  await page.waitForSelector('.tilt-card', { timeout: 20000 });
  const warmCardsTime = performance.now() - tWarm;
  const warmCount = await page.locator('.tilt-card').count();
  console.log(`  -> Warm Cards Visible: ${warmCardsTime.toFixed(0)}ms`);
  console.log(`  -> Warm Visible Cards: ${warmCount}`);

  // 3. Quick Lifecycle Pill Switching (Instant client-side / cache switch)
  console.log('\n[TEST 3] Interactive Lifecycle Filter Switching...');
  
  // Switch to Emerging
  let tSwitch = performance.now();
  const emergingPill = page.locator('#lifecycle-pill-emerging');
  if (await emergingPill.isVisible()) {
    await emergingPill.click();
    await page.waitForTimeout(100);
    const emergingCards = await page.locator('.tilt-card').count();
    console.log(`  -> Switch to Emerging: ${(performance.now() - tSwitch).toFixed(0)}ms (Rendered ${emergingCards} cards)`);
  }

  // Switch to Rising
  tSwitch = performance.now();
  const risingPill = page.locator('#lifecycle-pill-rising');
  if (await risingPill.isVisible()) {
    await risingPill.click();
    await page.waitForTimeout(100);
    const risingCards = await page.locator('.tilt-card').count();
    console.log(`  -> Switch to Rising: ${(performance.now() - tSwitch).toFixed(0)}ms (Rendered ${risingCards} cards)`);
  }

  // Switch to Targeted quick chip
  tSwitch = performance.now();
  const targetedChip = page.locator('#targeted-quick-filter');
  if (await targetedChip.isVisible()) {
    await targetedChip.click();
    await page.waitForTimeout(100);
    const targetedActive = await targetedChip.evaluate(el => el.classList.contains('bg-emerald-500'));
    console.log(`  -> Toggle Targeted Workspace: ${(performance.now() - tSwitch).toFixed(0)}ms (Active: ${targetedActive})`);
    // Toggle back
    await targetedChip.click();
    await page.waitForTimeout(100);
  }

  // 4. Modal Filter Switching (Testing Language Filter: Global)
  console.log('\n[TEST 4] Advanced Filter Modal & Global Filter Switch...');
  const openFiltersBtn = page.locator('#open-filters-modal-btn');
  if (await openFiltersBtn.isVisible()) {
    await openFiltersBtn.click();
    await page.waitForSelector('text=Language & Regional Cluster', { timeout: 5000 });
    
    // Select Global chip inside modal
    const globalChip = page.locator('button:has-text("🌐 Global")').first();
    if (await globalChip.isVisible()) {
      await globalChip.click();
      console.log('  -> Selected "🌐 Global" filter in modal');
    }

    // Click Apply button
    const applyBtn = page.locator('button:has-text("Apply Filters")');
    if (await applyBtn.isVisible()) {
      tSwitch = performance.now();
      await applyBtn.click();
      await page.waitForSelector('.tilt-card', { timeout: 10000 });
      const globalCards = await page.locator('.tilt-card').count();
      console.log(`  -> Applied Global Filter: ${(performance.now() - tSwitch).toFixed(0)}ms (Rendered ${globalCards} cards)`);
    }
  }

  // Check for any ApiErrorBanner
  const errorBanner = page.locator('text=Service temporarily unavailable');
  const hasError = await errorBanner.isVisible().catch(() => false);
  console.log(`\n[ERROR AUDIT] ApiErrorBanner visible: ${hasError ? 'YES (REGRESSION!)' : 'NO (PASSED)'}`);
  console.log(`[ERROR AUDIT] Console errors detected: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    console.log('Console error sample:', consoleErrors.slice(0, 3));
  }

  // Take screenshot for evidence
  await page.screenshot({ path: 'speed_audit_result.png', fullPage: false });
  console.log('\nScreenshot saved to speed_audit_result.png');

  await browser.close();
  console.log('\n=== AUDIT COMPLETE ===');
  process.exit(0);
}

auditSpeed().catch((err) => {
  console.error(err);
  process.exit(1);
});
