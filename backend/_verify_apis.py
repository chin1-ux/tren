import socket, json, sys, time
sys.stdout.reconfigure(encoding='utf-8')
_orig = socket.getaddrinfo
def _ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4
import urllib.request

BASE = "https://trendrop-black.vercel.app"

def api(method, path, token=None, body=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body:
        headers["Content-Type"] = "application/json"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        return 0, {"error": str(e)}

# Login and get fresh token
print("=== LOGGING IN ===")
status, resp = api("POST", "/api/auth/login", body={"email": "chin@free.com", "password": "123456"})
print(f"Login: {status}")
token = resp.get("session_token", "")
plan = resp.get("plan", "?")
print(f"  token={len(token)} chars, plan={plan}")

# Set to pro
SUPABASE_URL = "https://gxxpvstrvphwhlqbvymv.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd4eHB2c3RydnBod2hscWJ2eW12Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDg4NzczNywiZXhwIjoyMTAwNDYzNzM3fQ.DhoBpfPSmXWBHKnk5oa0H_a6LsaEm--WPjSVSMab-aU"
hdrs = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}", "Content-Type": "application/json"}

data = json.dumps({"plan": "pro"}).encode()
req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/users?email=eq.chin@free.com", data=data, headers=hdrs, method="PATCH")
urllib.request.urlopen(req, timeout=15)
print("Set plan=pro in DB")

print("\nWaiting 5 min for cache expiry...")
time.sleep(310)

# Re-login to get fresh token with new plan
print("\n=== RE-LOGIN (after cache expiry) ===")
status, resp = api("POST", "/api/auth/login", body={"email": "chin@free.com", "password": "123456"})
token = resp.get("session_token", "")
plan = resp.get("plan", "?")
print(f"Login: {status} | plan={plan} | token={len(token)} chars")

# Test all APIs as PRO
print("\n=== PRO ACCOUNT APIs ===")
for ep in ["/api/trends", "/api/trends/emerging", "/api/trends/peaked", "/api/trends/expired", "/api/deals"]:
    status, resp = api("GET", ep, token=token)
    if isinstance(resp, list):
        count = len(resp)
        preview = json.dumps(resp[0], default=str)[:120] if resp else "[]"
        print(f"  {ep:30} {status} | {count:4} items | {preview}")
    else:
        print(f"  {ep:30} {status} | {json.dumps(resp, default=str)[:120]}")

# Check emerging trends detail
print("\n=== EMERGING TRENDS (PRO) ===")
status, resp = api("GET", "/api/trends/emerging", token=token)
if isinstance(resp, list):
    for t in resp[:5]:
        fmt = t.get("dominant_format", "?")
        repl = t.get("format_replication_rate", 0)
        print(f"  {t.get('audio_title','?')[:30]:30} | vel={t.get('velocity_avg',0):.0f} | reels={t.get('reel_count',0)} | window={t.get('window_hours_remaining',0)}h | format={fmt} | repl={repl}")
else:
    print(f"  {json.dumps(resp, default=str)[:300]}")

# Revert to free
data = json.dumps({"plan": "free"}).encode()
req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/users?email=eq.chin@free.com", data=data, headers=hdrs, method="PATCH")
urllib.request.urlopen(req, timeout=15)
print("\nSet plan=free in DB")

print("\nWaiting 5 min for cache expiry...")
time.sleep(310)

# Re-login as FREE
print("\n=== RE-LOGIN (FREE) ===")
status, resp = api("POST", "/api/auth/login", body={"email": "chin@free.com", "password": "123456"})
token = resp.get("session_token", "")
plan = resp.get("plan", "?")
print(f"Login: {status} | plan={plan} | token={len(token)} chars")

print("\n=== FREE ACCOUNT APIs ===")
for ep in ["/api/trends", "/api/trends/emerging", "/api/trends/peaked", "/api/trends/expired", "/api/deals"]:
    status, resp = api("GET", ep, token=token)
    if isinstance(resp, list):
        count = len(resp)
        print(f"  {ep:30} {status} | {count:4} items")
    else:
        detail = resp.get("detail", {})
        msg = detail.get("message", "")[:80] if isinstance(detail, dict) else str(resp)[:80]
        print(f"  {ep:30} {status} | {msg}")
