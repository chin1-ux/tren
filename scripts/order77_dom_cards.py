import asyncio
import json
from playwright.async_api import async_playwright

async def inspect():
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
        
        card0_html = await page.evaluate("""() => {
            const a = document.querySelector('a[href*="/reel/"]');
            return a ? a.outerHTML : 'None';
        }""")
        print("Card 0 Outer HTML length:", len(card0_html))
        print("Card 0 Outer HTML:\n", card0_html[:1500])
        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
