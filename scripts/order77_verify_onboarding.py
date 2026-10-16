import asyncio
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

PREVIEW_URL = "https://trendrop-pxg0tk5gn-chinmays-projects-c20ed5a5.vercel.app"

async def test_onboarding():
    print("=" * 80)
    print("ORDER 77: VERIFYING 3-TAP ONBOARDING FLOW ON PREVIEW")
    print(f"Target: {PREVIEW_URL}")
    print("=" * 80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = await context.new_page()

        # Set auth but clear onboarding so onboarding modal opens
        await page.goto(f"{PREVIEW_URL}/login")
        await page.wait_for_timeout(1000)
        await page.evaluate("""() => {
            localStorage.setItem('trendrop_session_token', 'demo_guest_token');
            localStorage.setItem('trendrop_user_email', 'demo@trendrop.app');
            localStorage.setItem('trendrop_user_plan', 'pro');
            localStorage.removeItem('trendrop_onboarding_completed');
            localStorage.removeItem('trendrop_user_niche');
            localStorage.removeItem('trendrop_user_language');
        }""")

        await page.goto(f"{PREVIEW_URL}/")
        await page.wait_for_timeout(3000)

        # Step 1: Check Step 1 (Niche)
        niche_heading = await page.inner_text("h2")
        print(f"Step 1 Heading: '{niche_heading}'")
        
        # Tap 1: Select "Fitness & Gym" niche button
        fitness_btn = await page.query_selector("button:has-text('Fitness & Gym')")
        if fitness_btn:
            print("Tap 1: Clicked 'Fitness & Gym'")
            await fitness_btn.click()
            await page.wait_for_timeout(500)
        
        # Click next to step 2
        next1_btn = await page.query_selector("button:has-text('Next: Choose Language')")
        if next1_btn:
            print("Step 1 Action: Clicked 'Next: Choose Language'")
            await next1_btn.click()
            await page.wait_for_timeout(800)

        # Step 2: Check Step 2 (Language)
        lang_heading = await page.inner_text("h2")
        print(f"Step 2 Heading: '{lang_heading}'")
        
        # Tap 2: Select "Global / English"
        lang_btn = await page.query_selector("button:has-text('Global / English')")
        if lang_btn:
            print("Tap 2: Clicked 'Global / English'")
            await lang_btn.click()
            await page.wait_for_timeout(500)

        # Click next to step 3
        next2_btn = await page.query_selector("button:has-text('Review & See 5')")
        if next2_btn:
            print("Step 2 Action: Clicked 'Review & See 5'")
            await next2_btn.click()
            await page.wait_for_timeout(800)

        # Step 3: Check Step 3 (Summary & Final Action)
        summary_heading = await page.inner_text("h2")
        print(f"Step 3 Heading: '{summary_heading}'")

        # Tap 3: Finish -> "See Today's 5 Audios"
        finish_btn = await page.query_selector("button#onboarding-see-5-btn, button:has-text(\"See Today's 5 Audios\")")
        print(f"Tap 3 Button found: {finish_btn is not None}")
        if finish_btn:
            print("Tap 3: Clicked 'See Today's 5 Audios'")
            await finish_btn.click()
            await page.wait_for_timeout(3500)

        # Verify modal is closed and feed is visible
        modal = await page.query_selector("div.fixed.inset-0.z-50")
        print(f"Onboarding modal dismissed: {modal is None}")

        cards = await page.query_selector_all("article.tilt-card")
        print(f"Feed loaded with cards count: {len(cards)}")

        # Screenshot
        shot_path = "evidence/order77/screens/onboarding_3tap_success.png"
        await page.screenshot(path=shot_path, full_page=False)
        print(f"Captured onboarding success screenshot: {shot_path}")

        # Check local storage to confirm persisted
        stored_niche = await page.evaluate("() => localStorage.getItem('trendrop_user_niche')")
        stored_lang = await page.evaluate("() => localStorage.getItem('trendrop_user_language')")
        stored_completed = await page.evaluate("() => localStorage.getItem('trendrop_onboarding_completed')")
        print(f"Persisted state in LocalStorage: niche={stored_niche}, lang={stored_lang}, completed={stored_completed}")

        await browser.close()
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_onboarding())
