#!/usr/bin/env python3
"""
Test frontend with Playwright
Tests: Auth/Login behavior, Trends display
"""

import asyncio
import os
from playwright.async_api import async_playwright
from datetime import datetime

async def test_auth_behavior():
    """Test auth/login behavior with fresh browser context"""
    print("=" * 60)
    print("TESTING AUTH/LOGIN BEHAVIOR")
    print("=" * 60)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Get the frontend URL from environment or use localhost
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
        print(f"\nTesting with URL: {frontend_url}")

        try:
            # Navigate to the site with fresh context (simulating new user)
            print("\n1. Navigating to site with fresh browser context...")
            await page.goto(frontend_url, timeout=60000)
            await page.wait_for_load_state('networkidle', timeout=30000)

            # Take screenshot
            screenshot_path = f"test_screenshots/auth_fresh_visit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            os.makedirs('test_screenshots', exist_ok=True)
            await page.screenshot(path=screenshot_path)
            print(f"   Screenshot saved: {screenshot_path}")

            # Check if onboarding is shown
            print("\n2. Checking if onboarding flow is shown...")
            onboarding_visible = await page.locator('text=/Welcome|Onboarding|Get started/i').count() > 0
            print(f"   Onboarding visible: {onboarding_visible}")

            if onboarding_visible:
                print("   [PASS] Onboarding flow is shown to new users")
            else:
                print("   [FAIL] Onboarding flow is NOT shown (users can access app directly)")

            # Check if app is accessible without auth
            print("\n3. Checking if app is accessible without authentication...")
            app_elements = await page.locator('text=/Trend|Trendrop|trends/i').count()
            print(f"   App elements found: {app_elements}")

            if app_elements > 0:
                print("   [FAIL] APP IS ACCESSIBLE WITHOUT AUTHENTICATION")
            else:
                print("   [PASS] App is protected (requires auth)")

            # Check localStorage
            print("\n4. Checking localStorage contents...")
            visited = await page.evaluate('() => localStorage.getItem("trendrop_visited")')
            email = await page.evaluate('() => localStorage.getItem("trendrop_email")')
            token = await page.evaluate('() => localStorage.getItem("trendrop_token")')

            print(f"   trendrop_visited: {visited}")
            print(f"   trendrop_email: {email}")
            print(f"   trendrop_token: {token}")

            if visited:
                print("   [FAIL] User marked as visited without real auth")
            else:
                print("   [PASS] Fresh visit detected")

        except Exception as e:
            print(f"   Error during test: {e}")

        finally:
            await context.close()
            await browser.close()

async def test_trends_display():
    """Test trends display in the frontend"""
    print("\n" + "=" * 60)
    print("TESTING TRENDS DISPLAY")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
        print(f"\nTesting with URL: {frontend_url}")

        try:
            # Navigate to site
            print("\n1. Navigating to site...")
            await page.goto(frontend_url, timeout=60000)
            await page.wait_for_load_state('networkidle', timeout=30000)

            # Dismiss onboarding if shown
            print("\n2. Dismissing onboarding if shown...")
            try:
                onboarding_close = page.locator('button:has-text("Skip"), button:has-text("X"), [aria-label="Close"]').first
                if await onboarding_close.count() > 0:
                    await onboarding_close.click(timeout=5000)
                    await page.wait_for_timeout(1000)
            except:
                print("   (No onboarding to dismiss or already dismissed)")

            # Wait for trends to load
            print("\n3. Waiting for trends to load...")
            await page.wait_for_timeout(3000)

            # Take screenshot
            screenshot_path = f"test_screenshots/trends_display_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            os.makedirs('test_screenshots', exist_ok=True)
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   Screenshot saved: {screenshot_path}")

            # Check for trend cards
            print("\n4. Checking for trend cards...")
            trend_cards = await page.locator('[class*="trend"], [class*="card"]').count()
            print(f"   Trend cards found: {trend_cards}")

            if trend_cards > 0:
                print("   [PASS] Trends are displayed")
            else:
                print("   [FAIL] No trends displayed")

            # Check for loading state
            print("\n5. Checking for loading state...")
            loading = await page.locator('text=/Loading|loading/i').count()
            print(f"   Loading indicators: {loading}")

            # Check for error state
            print("\n6. Checking for error state...")
            error = await page.locator('text=/Error|error|Failed/i').count()
            print(f"   Error indicators: {error}")

            if error > 0:
                print("   [FAIL] Errors detected on page")
            else:
                print("   [PASS] No errors detected")

            # Check specific trend elements
            print("\n7. Checking for specific trend elements...")
            audio_titles = await page.locator('text=/Audio|Song|Track/i').count()
            print(f"   Audio/Song/Track mentions: {audio_titles}")

            # Check if trends are recent (last 2 days)
            print("\n8. Checking trend freshness...")
            date_elements = await page.locator('text=/hours|days|ago/i').count()
            print(f"   Date elements found: {date_elements}")

        except Exception as e:
            print(f"   Error during test: {e}")

        finally:
            await context.close()
            await browser.close()

async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("FRONTEND TESTING WITH PLAYWRIGHT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    await test_auth_behavior()
    await test_trends_display()

    print("\n" + "=" * 60)
    print("TESTING COMPLETED")
    print("=" * 60)
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nScreenshots saved in: test_screenshots/")

if __name__ == "__main__":
    asyncio.run(main())
