"""
P-PAY verification: Pro-user Caption Kit happy path + browser bundle proof.
Uses correct localStorage keys matching the app's auth flow.
"""
import asyncio, os, sys, time, requests
from playwright.async_api import async_playwright
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

BASE = 'https://trendrop-black.vercel.app'
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), 'test_screenshots')

ts = 1788426055
pro_email = f'ppay_pro_{ts}@test.com'
free_email = f'ppay_free_{ts}@test.com'

def get_token(email):
    r = requests.post(f'{SUPABASE_URL}/auth/v1/token?grant_type=password',
        headers={'apikey': SERVICE_KEY, 'Content-Type': 'application/json'},
        json={'email': email, 'password': 'TestPass123!'}, timeout=15)
    if r.status_code == 200:
        return r.json().get('access_token', ''), r.json().get('refresh_token', '')
    print(f'Token error: {r.status_code} {r.text[:100]}')
    return '', ''

async def set_auth_keys(page, token, email, plan='free'):
    """Set all auth localStorage keys matching the app's AuthContext."""
    await page.evaluate(f"""() => {{
        localStorage.setItem('trendrop_session_token', '{token}');
        localStorage.setItem('trendrop_user_email', '{email}');
        localStorage.setItem('trendrop_user_niche', 'all');
        localStorage.setItem('trendrop_user_language', 'en');
        localStorage.setItem('trendrop_user_plan', '{plan}');
    }}""")

async def main():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    pro_token, _ = get_token(pro_email)
    free_token, _ = get_token(free_email)
    print(f'Pro token: {pro_token[:30]}...')
    print(f'Free token: {free_token[:30]}...')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ============================================
        # PRO USER TEST — Caption Kit happy path
        # ============================================
        print("\n=== PRO USER: Caption Kit happy path ===")
        ctx = await browser.new_context(viewport={'width': 1280, 'height': 900})
        page = await ctx.new_page()

        js_loads = []
        def on_resp(resp):
            if '/assets/' in resp.url and resp.url.endswith('.js'):
                js_loads.append({'url': resp.url, 'status': resp.status})
        page.on('response', on_resp)

        # Navigate to base to establish origin, then set auth keys
        await page.goto(BASE)
        await page.wait_for_load_state('networkidle')
        await set_auth_keys(page, pro_token, pro_email, 'pro')

        # Navigate to dashboard
        await page.goto(f'{BASE}/dashboard')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)

        url = page.url
        body = await page.inner_text('body')
        print(f'URL: {url}')

        await page.screenshot(path=f'{SCREENSHOT_DIR}/ppay_pro_dashboard.png', full_page=False)
        print('Screenshot: ppay_pro_dashboard.png')

        on_login = 'Login to your Trendrop' in body[:300]
        print(f'On login page: {on_login}')

        if not on_login:
            # Dashboard loaded! Check for Caption Kit
            has_caption = 'Caption Kit' in body
            has_ai = 'AI Content' in body
            has_gate = 'requires a Pro plan' in body
            print(f'Has "Caption Kit": {has_caption}')
            print(f'Has "AI Content": {has_ai}')
            print(f'Has gate text (BAD): {has_gate}')

            # Try to find and click the Caption Kit
            try:
                btn = page.locator('text=/Caption Kit|Generate Caption|AI Content/i').first
                count = await btn.count()
                print(f'Caption Kit button count: {count}')
                if count > 0:
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=f'{SCREENSHOT_DIR}/ppay_pro_caption.png', full_page=False)
                    print('Screenshot: ppay_pro_caption.png')
                    form_text = await page.inner_text('body')
                    print(f'Has "Generate": {"Generate" in form_text}')
                    print(f'Has gate (BAD): {"requires a Pro plan" in form_text}')
            except Exception as e:
                print(f'Error: {e}')
        else:
            # Still on login — print what we see
            lines = [l.strip() for l in body.split('\n') if l.strip()][:20]
            for l in lines:
                print(f'  > {l}')

        await ctx.close()

        # ============================================
        # FREE USER TEST — Gate blocks Caption Kit
        # ============================================
        print("\n=== FREE USER: Gate test ===")
        ctx2 = await browser.new_context(viewport={'width': 1280, 'height': 900})
        page2 = await ctx2.new_page()

        await page2.goto(BASE)
        await page2.wait_for_load_state('networkidle')
        await set_auth_keys(page2, free_token, free_email, 'free')

        await page2.goto(f'{BASE}/dashboard')
        await page2.wait_for_load_state('networkidle')
        await page2.wait_for_timeout(3000)

        await page2.screenshot(path=f'{SCREENSHOT_DIR}/ppay_free_dashboard.png', full_page=False)
        print('Screenshot: ppay_free_dashboard.png')

        free_body = await page2.inner_text('body')
        on_login_free = 'Login to your Trendrop' in free_body[:300]
        has_gate = 'requires a Pro plan' in free_body or 'Upgrade to Pro' in free_body
        print(f'On login: {on_login_free}')
        print(f'Has gate: {has_gate}')

        await ctx2.close()

        # ============================================
        # BUNDLE PROOF
        # ============================================
        print("\n=== BUNDLE PROOF (network tab) ===")
        for load in js_loads:
            fname = load['url'].split('/')[-1]
            if 'index-' in fname:
                print(f'  Loaded: {fname} (HTTP {load["status"]})')

        dqd3 = any('DQD3VWUG' in l['url'] for l in js_loads)
        ecvd = any('EcVD7aSf' in l['url'] for l in js_loads)
        print(f'\n  DQD3VWUG (fixed bundle) loaded in browser: {dqd3}')
        print(f'  EcVD7aSf (entry manifest) loaded in browser: {ecvd}')

        # Verify content
        r = requests.get(f'{BASE}/assets/index-DQD3VWUG.js', timeout=30)
        print(f'\n  DQD3VWUG content:')
        print(f'    has 499: {"499" in r.text}')
        print(f'    has requiredPlan: {"requiredPlan" in r.text}')
        print(f'    has "requires a Pro plan": {"requires a Pro plan" in r.text}')

        await browser.close()

    print("\n=== DONE ===")

asyncio.run(main())
