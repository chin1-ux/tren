import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

COOKIE_FILE = "backend/cookies.json"

async def inspect_dom():
    with open(COOKIE_FILE) as f:
        cookies_raw = json.load(f)

    cookies = [
        {
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/"),
        }
        for c in cookies_raw
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        url = "https://www.instagram.com/reels/audio/474517893035258/"  # Sadeness
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3500)

        # Find first 3 reel links
        links = await page.query_selector_all("a[href*='/reel/']")
        print(f"Found {len(links)} reel link elements")
        
        for i, link in enumerate(links[:3]):
            href = await link.get_attribute("href")
            inner_html = await link.inner_html()
            print(f"\n--- Link {i}: {href} ---")
            print("HTML snippet (first 300 chars):", inner_html[:300].replace('\n', ' '))
            
            # Check for img tag
            img = await link.query_selector("img")
            if img:
                src = await img.get_attribute("src")
                print("Found img src:", src[:100] if src else "None")
                if src:
                    # Try download
                    resp = await context.request.get(src)
                    print(f"Image download status: {resp.status}, bytes: {len(await resp.body())}")
            else:
                print("No direct img child, searching parent or siblings...")
                parent = await link.evaluate_handle("el => el.parentElement.innerHTML")
                parent_str = str(parent)
                print("Parent HTML snippet:", parent_str[:200])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_dom())
