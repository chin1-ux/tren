import { chromium } from 'playwright';

async function debugDom() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log(`[BROWSER CONSOLE ${msg.type()}]:`, msg.text()));
  page.on('pageerror', err => console.log('[PAGE ERROR]:', err));

  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' });
  
  const title = await page.title();
  console.log('Page Title:', title);

  const bodyText = await page.evaluate(() => document.body.innerText.slice(0, 500));
  console.log('Body Text Preview:\n', bodyText);

  const html = await page.content();
  console.log('HTML Length:', html.length);

  await browser.close();
}

debugDom().catch(console.error);
