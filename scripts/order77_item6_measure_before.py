import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(viewport={'width': 390, 'height': 844})
        page = await ctx.new_page()
        
        # 1. Visit origin to initialize localStorage on domain
        await page.goto('https://trendrop-black.vercel.app/login')
        await page.wait_for_timeout(1000)
        
        # 2. Set localStorage directly on the origin domain
        await page.evaluate("""() => {
            localStorage.setItem('trendrop_session_token', 'demo_guest_token');
            localStorage.setItem('trendrop_user_email', 'demo@trendrop.app');
            localStorage.setItem('trendrop_user_plan', 'pro');
            localStorage.setItem('trendrop_user_niche', 'all');
            localStorage.setItem('trendrop_user_language', 'all');
            localStorage.setItem('trendrop_theme', 'dark');
            localStorage.setItem('trendrop_onboarding_completed', 'true');
        }""")
        
        # 3. Navigate to root
        await page.goto('https://trendrop-black.vercel.app/')
        await page.wait_for_timeout(5000)
        
        print("URL after navigation:", page.url)
        cards = await page.query_selector_all("div[class*='group/card']")
        print("Cards rendered:", len(cards))
        
        # Take screenshot of feed
        await page.screenshot(path="evidence/order77/screens/item6_before_prod.png")
        print("Screenshot saved to evidence/order77/screens/item6_before_prod.png")
        
        if cards:
            first_card = cards[0]
            buttons = await first_card.query_selector_all("button")
            links = await first_card.query_selector_all("a")
            text = await first_card.inner_text()
            print("\nFirst card elements:")
            print("  Buttons count:", len(buttons))
            print("  Links count  :", len(links))
            print("  Text snippet :", text[:200].replace('\n', ' '))
            
            banned = [
                "Spiking velocity with <28% saturation",
                "currently driving high engagement on short-form feeds",
                "85%",
                "61%",
                "Audience Fit",
                "Market Space",
            ]
            print("\nBanned strings in first card:")
            for b_str in banned:
                print(f"  '{b_str}': {b_str in text}")
                
        await b.close()

if __name__ == "__main__":
    asyncio.run(run())
