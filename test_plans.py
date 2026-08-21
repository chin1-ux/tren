"""
Playwright plan-gating test: login as free/creator/agency, verify each tab renders correctly.
"""
import os, time, json
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
OUT = os.path.join(os.path.dirname(__file__), "clickthrough_output")
os.makedirs(OUT, exist_ok=True)

ACCOUNTS = [
    {"email": "chin@free.com", "password": "123456", "plan": "free", "label": "FREE"},
    {"email": "creator@trendrop.test", "password": "Creator123!", "plan": "pro", "label": "PRO (creator)"},
    {"email": "agency@trendrop.test", "password": "Agency1234!", "plan": "pro", "label": "PRO (agency)"},
]

TABS = ["Trends", "Dashboard", "Generate", "Ideas", "Deals", "Settings"]
RESULTS = []

def snap(page, name):
    path = os.path.join(OUT, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    return path

def dismiss_onboarding(page):
    """Set localStorage after navigating to skip onboarding."""
    page.evaluate("localStorage.setItem('trendrop_onboarding_completed', 'true')")

def clear_sessions():
    """Clear all active sessions before each test."""
    from supabase import create_client
    env = {}
    for line in open("backend/.env"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    sb = create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"])
    users = sb.table("users").select("id").execute()
    for u in (users.data or []):
        try:
            sb.table("active_sessions").delete().eq("user_id", u["id"]).execute()
        except:
            pass

def test_account(acct):
    print(f"\n{'='*60}")
    print(f"TESTING: {acct['label']} ({acct['email']})")
    print(f"{'='*60}")

    # Clear all sessions before each test to avoid device cap issues
    clear_sessions()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()

        net_errors = []
        def on_response(response):
            if response.status >= 400:
                net_errors.append(f"{response.status} {response.request.method} {response.url}")
        page.on("response", on_response)

        # Navigate first, then set localStorage to skip onboarding
        page.goto(f"{BASE}/login", wait_until="domcontentloaded")
        dismiss_onboarding(page)
        page.wait_for_selector('input[type="email"]', timeout=15000)
        page.fill('input[type="email"]', acct["email"], timeout=10000)
        page.fill('input[type="password"]', acct["password"], timeout=10000)
        page.click('button[type="submit"]', timeout=5000)
        time.sleep(8)  # Wait for SPA navigation to complete

        current_url = page.url
        body = page.inner_text("body")
        logged_in = "Login successful" in body or "/login" not in current_url
        # Also check: if we see trend data or "ACTIVE TRENDS" we're logged in
        if "ACTIVE TRENDS" in body or "TRENDING" in body:
            logged_in = True
        snap(page, f"plan_{acct['label']}_01_after_login")
        print(f"  Logged in: {logged_in} (URL: {current_url})")

        if not logged_in:
            print(f"  FAILED: Still on login page after submit")
            # Check for error message
            body = page.inner_text("body")
            print(f"  Body: {body[:200]}")
            browser.close()
            RESULTS.append({"plan": acct["label"], "login": False, "tabs": {}})
            return

        # Test each tab
        tab_results = {}
        for i, tab_name in enumerate(TABS):
            print(f"\n  TAB {i+1}: {tab_name}")
            try:
                tab = page.locator(f'nav >> text="{tab_name}"').first
                if tab.count() > 0:
                    tab.click(timeout=5000)
                else:
                    page.goto(f"{BASE}/{tab_name.lower()}", wait_until="domcontentloaded", timeout=10000)
                time.sleep(3)
                # Dismiss any modal
                page.keyboard.press("Escape")
                time.sleep(0.5)

                body = page.inner_text("body")
                url = page.url
                snap(page, f"plan_{acct['label']}_02_tab_{tab_name.lower()}")

                # Check for paywall indicators
                has_paywall = any(x in body.lower() for x in [
                    "requires creator plan", "requires agency plan",
                    "requires pro plan", "upgrade to creator",
                    "upgrade to agency", "upgrade to pro",
                    "unlock this feature", "locked", "coming soon"
                ])
                has_error = any(x in body.lower() for x in ["error", "failed", "something went wrong"])
                body_len = len(body.strip())

                status = "OK"
                if has_paywall:
                    status = "PAYWALLED"
                elif has_error:
                    status = "ERROR"
                elif body_len < 50:
                    status = "EMPTY"

                print(f"    URL: {url}")
                print(f"    Status: {status} | Body: {body_len} chars")
                if has_paywall:
                    # Find the paywall text
                    for line in body.split("\n"):
                        line = line.strip()
                        if any(x in line.lower() for x in ["requires", "upgrade", "unlock", "locked"]):
                            print(f"    Paywall: {line[:100]}")
                            break

                tab_results[tab_name] = {
                    "status": status,
                    "url": url,
                    "body_len": body_len,
                    "has_paywall": has_paywall,
                }
            except Exception as e:
                print(f"    ERROR: {str(e)[:100]}")
                tab_results[tab_name] = {"status": "EXCEPTION", "error": str(e)[:100]}

        # Test /pricing
        print(f"\n  NAVIGATING: /pricing")
        try:
            page.goto(f"{BASE}/pricing", wait_until="domcontentloaded", timeout=10000)
            time.sleep(3)
            body = page.inner_text("body")
            url = page.url
            snap(page, f"plan_{acct['label']}_03_pricing")
            redirected = "/login" in url
            print(f"    URL: {url} | Redirected to login: {redirected}")
            if not redirected:
                # Check what plan is shown as "Current Plan"
                for line in body.split("\n"):
                    if "current plan" in line.lower():
                        print(f"    Current plan shown: {line.strip()[:100]}")
                        break
            tab_results["Pricing"] = {"status": "REDIRECT" if redirected else "OK", "url": url}
        except Exception as e:
            print(f"    ERROR: {e}")

        # Network errors summary
        paywall_403s = [e for e in net_errors if "/api/trends/emerging" in e or "/api/india/" in e]
        auth_errors = [e for e in net_errors if "/api/auth/verify" in e]
        other_errors = [e for e in net_errors if e not in paywall_403s and e not in auth_errors]

        print(f"\n  NETWORK SUMMARY:")
        print(f"    Paywall 403s (expected): {len(paywall_403s)}")
        print(f"    Auth errors: {len(auth_errors)}")
        print(f"    Other errors: {len(other_errors)}")
        for e in other_errors[:5]:
            print(f"      {e}")

        browser.close()

        RESULTS.append({
            "plan": acct["label"],
            "email": acct["email"],
            "login": logged_in,
            "tabs": tab_results,
            "net_errors": {"paywall": len(paywall_403s), "auth": len(auth_errors), "other": len(other_errors)},
        })

def main():
    for acct in ACCOUNTS:
        test_account(acct)

    # Summary table
    print(f"\n{'='*60}")
    print("PLAN-GATING SUMMARY")
    print(f"{'='*60}")
    print(f"{'Plan':<10} {'Login':<8} {'Trends':<12} {'Dashboard':<12} {'Generate':<12} {'Ideas':<12} {'Deals':<12} {'Settings':<12}")
    print("-" * 90)
    for r in RESULTS:
        tabs = r.get("tabs", {})
        login = "OK" if r["login"] else "FAIL"
        vals = [login]
        for t in ["Trends", "Dashboard", "Generate", "Ideas", "Deals", "Settings"]:
            info = tabs.get(t, {})
            vals.append(info.get("status", "?")[:10])
        print(f"{r['plan']:<10} {' '.join(f'{v:<12}' for v in vals)}")

if __name__ == "__main__":
    main()
