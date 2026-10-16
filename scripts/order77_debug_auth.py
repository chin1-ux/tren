import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(viewport={'width': 390, 'height': 844})
        await ctx.add_init_script("""() => {
            localStorage.setItem('trendrop_session_token', 'demo_guest_token');
            localStorage.setItem('trendrop_user_email', 'demo@trendrop.app');
            localStorage.setItem('trendrop_user_plan', 'pro');
            localStorage.setItem('trendrop_user_niche', 'all');
            localStorage.setItem('trendrop_user_language', 'all');
            localStorage.setItem('trendrop_theme', 'dark');
            window.addEventListener('trendrop:unauthorized', e => console.log('EVENT: trendrop:unauthorized DISPATCHED!'));
        }""")
        page = await ctx.new_page()
        page.on('console', lambda msg: print(f"CONSOLE: {msg.text}"))
        page.on('response', lambda res: print(f"API {res.status}: {res.url}") if '/api/' in res.url else None)
        
        await page.goto('https://trendrop-black.vercel.app/')
        await page.wait_for_timeout(3000)
        print('URL at 3s:', page.url)
        await b.close()

if __name__ == "__main__":
    asyncio.run(run())
