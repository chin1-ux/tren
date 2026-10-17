import { chromium } from 'playwright';

async function test() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  page.on('console', msg => console.log(`[CONSOLE ${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => console.log(`[PAGE ERROR] ${err.message}`));

  await page.goto('http://localhost:8080/', { waitUntil: 'load' });
  await page.waitForTimeout(3000);

  const url = page.url();
  const text = await page.evaluate(() => document.body.innerText.substring(0, 300));
  console.log('FINAL URL:', url);
  console.log('BODY TEXT:\n', text);

  // Take screenshot
  await page.screenshot({ path: 'test_after_fix.png' });
  console.log('Screenshot taken!');

  await browser.close();
}

test().catch(e => console.error(e));
