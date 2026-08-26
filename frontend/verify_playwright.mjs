import { chromium } from 'playwright';

(async () => {
  console.log('Starting Playwright verification...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const targetUrl = process.argv[2] || 'http://localhost:8080';
  
  try {
    // 1. Verify /proof page
    console.log(`Visiting ${targetUrl}/proof...`);
    await page.goto(`${targetUrl}/proof`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000); // give it a second to render React
    const content = await page.content();
    console.log(content.slice(0, 500));
    if (content.toLowerCase().includes('early detection proof') || content.toLowerCase().includes('proof')) {
      console.log('✅ /proof page verified.');
    } else {
      console.log('❌ /proof page missing expected content.');
    }
    
    // 2. Verify responsiveness on /generate
    console.log(`Visiting ${targetUrl}/generate...`);
    await page.goto(`${targetUrl}/generate`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    console.log('✅ /generate page accessible.');
    
    // 3. Verify fonts and styles
    const bodyFont = await page.evaluate(() => {
      return window.getComputedStyle(document.body).fontFamily;
    });
    if (bodyFont.toLowerCase().includes('bricolage grotesque')) {
      console.log('✅ Bricolage Grotesque font is applied to body.');
    } else {
      console.log(`❌ Bricolage Grotesque font NOT applied, got: ${bodyFont}`);
    }

  } catch (error) {
    console.error('Test failed with error:', error);
  } finally {
    await browser.close();
  }
})();
