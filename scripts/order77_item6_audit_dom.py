import asyncio
from playwright.async_api import async_playwright

PROD_URL = "https://trendrop-black.vercel.app"

async def audit():
    lines = []
    def log(msg):
        print(msg)
        lines.append(msg)

    log("=" * 80)
    log("ORDER 77 ITEM 6: UI TRUTH PURGE & COMPLEXITY AUDIT (BEFORE FIX)")
    log(f"Target URL: {PROD_URL}")
    log("=" * 80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = await context.new_page()

        # Auth setup
        await page.goto("https://trendrop-black.vercel.app/login")
        await page.wait_for_timeout(1000)
        await page.evaluate("""() => {
            localStorage.setItem('trendrop_session_token', 'demo_guest_token');
            localStorage.setItem('trendrop_user_email', 'demo@trendrop.app');
            localStorage.setItem('trendrop_user_plan', 'pro');
            localStorage.setItem('trendrop_user_niche', 'all');
            localStorage.setItem('trendrop_user_language', 'all');
            localStorage.setItem('trendrop_theme', 'dark');
            localStorage.setItem('trendrop_onboarding_completed', 'true');
        }""")

        await page.goto("https://trendrop-black.vercel.app/")
        await page.wait_for_timeout(4500)

        # Audit first card
        cards = await page.query_selector_all("div.relative.rounded-2xl, div[class*='border-slate-800']")
        log(f"Total container elements matched: {len(cards)}")

        first_card = await page.query_selector("div.relative.rounded-2xl, div[class*='border-slate-800']")
        if not first_card:
            first_card = (await page.query_selector_all("div[class*='bg-white/5'], div[class*='border']"))[2]

        buttons = await first_card.query_selector_all("button")
        links = await first_card.query_selector_all("a")
        text = await first_card.inner_text()

        log("\nFIRST CARD INTERACTIVE ELEMENTS (BEFORE):")
        log("-" * 80)
        log(f"Buttons count    : {len(buttons)}")
        for i, b in enumerate(buttons):
            b_text = (await b.inner_text()).strip().replace('\n', ' ')
            log(f"  Button {i+1}: '{b_text}'")
            
        log(f"\nLinks count      : {len(links)}")
        for i, l in enumerate(links):
            href = await l.get_attribute("href") or ""
            l_text = (await l.inner_text()).strip().replace('\n', ' ')
            log(f"  Link {i+1}  : '{l_text}' -> {href}")

        log(f"\nTotal interactive elements: {len(buttons) + len(links)} (TARGET: max 6)")

        banned_targets = [
            "Spiking velocity with <28% saturation",
            "currently driving high engagement on short-form feeds",
            "Audience Fit",
            "Market Space",
            "Golden Hour",
            "FILM NOW",
            "Targeted",
        ]

        full_body_text = await page.inner_text("body")
        log("\nBANNED STRINGS & JARGON AUDIT:")
        log("-" * 80)
        for s in banned_targets:
            present = s in text or s in full_body_text
            status_tag = "PRESENT (TO BE PURGED)" if present else "Not found"
            log(f"  '{s}': {status_tag}")

        await browser.close()

    log("=" * 80)
    with open("evidence/order77/item6_before.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Saved evidence to evidence/order77/item6_before.txt successfully")

if __name__ == "__main__":
    asyncio.run(audit())
