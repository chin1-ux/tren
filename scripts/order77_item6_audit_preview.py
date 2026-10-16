import asyncio
from playwright.async_api import async_playwright

PREVIEW_URL = "https://trendrop-pxg0tk5gn-chinmays-projects-c20ed5a5.vercel.app"

async def audit():
    lines = []
    def log(msg):
        print(msg)
        lines.append(msg)

    log("=" * 80)
    log("ORDER 77 ITEM 6: UI TRUTH PURGE & COMPLEXITY AUDIT (AFTER FIX - PREVIEW)")
    log(f"Target URL: {PREVIEW_URL}")
    log("=" * 80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = await context.new_page()

        # Auth setup
        await page.goto(f"{PREVIEW_URL}/login")
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

        await page.goto(f"{PREVIEW_URL}/")
        await page.wait_for_timeout(5000)

        # Total DOM element count
        dom_count = await page.evaluate("() => document.querySelectorAll('*').length")
        log(f"Total DOM elements on page: {dom_count}")

        # Capture screenshot of preview feed
        shot_path = "evidence/order77/screens/item6_after_preview.png"
        await page.screenshot(path=shot_path, full_page=False)
        log(f"Captured screenshot to: {shot_path}")

        # Cards count
        cards = await page.query_selector_all("article.tilt-card")
        log(f"Total trend card elements (article.tilt-card) found: {len(cards)}")

        if cards:
            first_card = cards[0]
            buttons = await first_card.query_selector_all("button")
            links = await first_card.query_selector_all("a")
            text = await first_card.inner_text()

            log("\nFIRST CARD INTERACTIVE ELEMENTS (AFTER):")
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

            interactive_total = len(buttons) + len(links)
            log(f"\nTotal interactive elements on card: {interactive_total} (TARGET: <= 6)")
        else:
            log("No article.tilt-card found on page!")

        # Banned copy audit
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
        violations = 0
        for s in banned_targets:
            present = s in full_body_text
            status_tag = "VIOLATION (STILL PRESENT)" if present else "PASSED (Clean / Not found)"
            if present:
                violations += 1
            log(f"  '{s}': {status_tag}")

        log(f"\nTotal Banned String Violations: {violations}")

        # Check Today's 5 default landing chip
        todays_5_btn = await page.query_selector("button:has-text(\"Today's 5\")")
        log(f"\nToday's 5 Action Button Present: {todays_5_btn is not None}")

        await browser.close()

    log("=" * 80)
    with open("evidence/order77/item6_after.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Saved evidence to evidence/order77/item6_after.txt successfully")

if __name__ == "__main__":
    asyncio.run(audit())
