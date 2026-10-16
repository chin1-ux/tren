import asyncio
import json
import re
from playwright.async_api import async_playwright

async def test_dl():
    with open('backend/cookies.json') as f:
        cookies_raw = json.load(f)
    cookies = [{'name': c['name'], 'value': c['value'], 'domain': c.get('domain', '.instagram.com'), 'path': c.get('path', '/')} for c in cookies_raw]
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()
        await page.goto('https://www.instagram.com/reels/audio/474517893035258/')
        await page.wait_for_timeout(3500)
        
        cards = await page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('a[href*="/reel/"]'));
            return anchors.map(a => {
                const bgDiv = a.querySelector('div[style*="background-image"]');
                let bgUrl = null;
                if (bgDiv) {
                    const style = bgDiv.getAttribute('style') || '';
                    const m = style.match(/url\\(["']?([^"']+)["']?\\)/);
                    if (m) bgUrl = m[1].replace(/&amp;/g, '&');
                }
                return {
                    href: a.getAttribute('href'),
                    bgUrl: bgUrl,
                    text: a.innerText
                };
            });
        }""")
        
        print(f"Total cards: {len(cards)}")
        download_success = 0
        total_bytes = 0
        for i, c in enumerate(cards[:12]):
            bg = c['bgUrl']
            if bg:
                resp = await ctx.request.get(bg)
                if resp.status == 200:
                    body = await resp.body()
                    download_success += 1
                    total_bytes += len(body)
                    print(f"Card {i} ({c['href']}, views={repr(c['text'])}): downloaded {len(body):,} bytes (status: {resp.status})")
                else:
                    print(f"Card {i}: HTTP {resp.status}")
            else:
                print(f"Card {i}: No background image found")
        print(f"\nDownload summary: {download_success}/{len(cards)} succeeded, total {total_bytes:,} bytes ({total_bytes/1024:.1f} KB)")
        await b.close()

if __name__ == "__main__":
    asyncio.run(test_dl())
