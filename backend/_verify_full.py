import asyncio, socket, json, sys, time
os.environ["PYTHONIOENCODING"] = "utf-8"
_orig = socket.getaddrinfo
def _ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request

SUPABASE_URL = "https://gxxpvstrvphwhlqbvymv.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd4eHB2c3RydnBod2hscWJ2eW12Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDg4NzczNywiZXhwIjoyMTAwNDYzNzM3fQ.DhoBpfPSmXWBHKnk5oa0H_a6LsaEm--WPjSVSMab-aU"
hdrs = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}", "Content-Type": "application/json"}

async def main():
    from playwright.async_api import async_playwright
    
    # Set to pro
    data = json.dumps({"plan": "pro"}).encode()
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/users?email=eq.chin@free.com",
                                data=data, headers=hdrs, method="PATCH")
    urllib.request.urlopen(req, timeout=15)
    print("Set plan=pro in DB")
    
    # Wait 5 minutes for cache to expire
    print("Waiting 5 minutes for plan cache to expire...")
    time.sleep(310)
    print("Cache should be expired now.\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        # ═══════════════════════════════════════════════════════════════
        # PRO ACCOUNT
        # ═══════════════════════════════════════════════════════════════
        print("=" * 70)
        print("PRO ACCOUNT VERIFICATION")
        print("=" * 70)
        
        page = await browser.new_page()
        await page.goto("https://trendrop-black.vercel.app/login", timeout=15000)
        await page.wait_for_timeout(2000)
        
        await page.locator("input[type='email']").fill("chin@free.com")
        await page.locator("input[type='password']").fill("123456")
        await page.locator("button[type='submit']").click()
        await page.wait_for_timeout(5000)
        
        token = await page.evaluate("() => localStorage.getItem('trendrop_session_token')")
        plan = await page.evaluate("() => localStorage.getItem('trendrop_user_plan')")
        print(f"\nLogin: token={'YES' if token else 'NO'} ({len(token) if token else 0} chars)")
        print(f"  localStorage plan={plan}")
        
        # Verify plan from API
        try:
            r = await page.evaluate("""async () => {
                const r = await fetch('/api/auth/me', {
                    headers: {'Authorization': 'Bearer ' + localStorage.getItem('trendrop_session_token')}
                });
                return await r.json();
            }""")
            print(f"  /api/auth/me plan={r.get('plan', '?')}")
        except: pass
        
        # Pages
        pages = [("/", "Feed"), ("/dashboard", "Dashboard"), ("/generate", "Generate"),
                 ("/ideas", "Ideas"), ("/deals", "Deals"), ("/marketplace", "Marketplace"),
                 ("/pricing", "Pricing"), ("/settings", "Settings")]
        
        print("\n--- Pages ---")
        for path, name in pages:
            try:
                resp = await page.goto(f"https://trendrop-black.vercel.app{path}", wait_until="networkidle", timeout=15000)
                body = await page.inner_text("body")
                has_trend = any(x in body.lower() for x in ["trending", "emerging", "rising"])
                has_blur = "blur" in body.lower() or "locked" in body.lower() or "upgrade" in body.lower()
                print(f"  {name:15} {resp.status} | {len(body):5} chars | trend={has_trend} | locked={has_blur}")
            except Exception as e:
                print(f"  {name:15} ERROR: {e}")
        
        # APIs
        print("\n--- APIs ---")
        apis = ["/api/trends", "/api/trends/emerging", "/api/trends/peaked",
                "/api/trends/expired", "/api/deals"]
        for ep in apis:
            try:
                r = await page.evaluate(f"""async () => {{
                    const r = await fetch('{ep}', {{
                        headers: {{'Authorization': 'Bearer ' + localStorage.getItem('trendrop_session_token')}}
                    }});
                    const t = await r.text();
                    return {{status: r.status, len: t.length, preview: t.substring(0, 150)}};
                }}""")
                print(f"  {ep:30} {r['status']} | {r['len']:6} bytes | {r['preview'][:100]}")
            except Exception as e:
                print(f"  {ep:30} ERROR: {e}")
        
        # Emerging detail
        print("\n--- Emerging Trends Detail ---")
        try:
            r = await page.evaluate("""async () => {
                const r = await fetch('/api/trends/emerging', {
                    headers: {'Authorization': 'Bearer ' + localStorage.getItem('trendrop_session_token')}
                });
                return await r.json();
            }""")
            if isinstance(r, list):
                for t in r[:5]:
                    fmt = t.get('dominant_format', '?')
                    repl = t.get('format_replication_rate', 0)
                    print(f"  {t.get('audio_title','?')[:30]:30} | vel={t.get('velocity_avg',0):.0f} | reels={t.get('reel_count',0)} | window={t.get('window_hours_remaining',0)}h | format={fmt} | replication={repl}")
            else:
                print(f"  Response: {str(r)[:300]}")
        except Exception as e:
            print(f"  ERROR: {e}")
        
        await page.close()
        
        # ═══════════════════════════════════════════════════════════════
        # FREE ACCOUNT
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "=" * 70)
        print("FREE ACCOUNT VERIFICATION")
        print("=" * 70)
        
        # Revert to free
        data = json.dumps({"plan": "free"}).encode()
        req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/users?email=eq.chin@free.com",
                                    data=data, headers=hdrs, method="PATCH")
        urllib.request.urlopen(req, timeout=15)
        print("Set plan=free in DB")
        
        # Wait for cache
        print("Waiting 5 minutes for plan cache to expire...")
        time.sleep(310)
        
        page2 = await browser.new_page()
        await page2.goto("https://trendrop-black.vercel.app/login", timeout=15000)
        await page2.wait_for_timeout(2000)
        
        await page2.locator("input[type='email']").fill("chin@free.com")
        await page2.locator("input[type='password']").fill("123456")
        await page2.locator("button[type='submit']").click()
        await page2.wait_for_timeout(5000)
        
        token2 = await page2.evaluate("() => localStorage.getItem('trendrop_session_token')")
        plan2 = await page2.evaluate("() => localStorage.getItem('trendrop_user_plan')")
        print(f"\nLogin: token={'YES' if token2 else 'NO'} ({len(token2) if token2 else 0} chars)")
        print(f"  localStorage plan={plan2}")
        
        try:
            r = await page2.evaluate("""async () => {
                const r = await fetch('/api/auth/me', {
                    headers: {'Authorization': 'Bearer ' + localStorage.getItem('trendrop_session_token')}
                });
                return await r.json();
            }""")
            print(f"  /api/auth/me plan={r.get('plan', '?')}")
        except: pass
        
        print("\n--- Pages ---")
        for path, name in pages:
            try:
                resp = await page2.goto(f"https://trendrop-black.vercel.app{path}", wait_until="networkidle", timeout=15000)
                body = await page2.inner_text("body")
                has_trend = any(x in body.lower() for x in ["trending", "emerging", "rising"])
                has_blur = "blur" in body.lower() or "locked" in body.lower() or "upgrade" in body.lower()
                print(f"  {name:15} {resp.status} | {len(body):5} chars | trend={has_trend} | locked={has_blur}")
            except Exception as e:
                print(f"  {name:15} ERROR: {e}")
        
        print("\n--- APIs ---")
        for ep in apis:
            try:
                r = await page2.evaluate(f"""async () => {{
                    const r = await fetch('{ep}', {{
                        headers: {{'Authorization': 'Bearer ' + localStorage.getItem('trendrop_session_token')}}
                    }});
                    const t = await r.text();
                    return {{status: r.status, len: t.length, preview: t.substring(0, 150)}};
                }}""")
                print(f"  {ep:30} {r['status']} | {r['len']:6} bytes | {r['preview'][:100]}")
            except Exception as e:
                print(f"  {ep:30} ERROR: {e}")
        
        await page2.close()
        await browser.close()

asyncio.run(main())
