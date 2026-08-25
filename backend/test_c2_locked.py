"""
C2 verification test — locked user enforcement.

Mocks the Supabase client so that:
- auth_token lookup returns a user with status='locked'
- Supabase JWT lookup resolves an email whose DB row has status='locked'
- login endpoint returns the locked row at status check time
- verify endpoint sees status='locked' and returns valid:false

We also test an unlocked user passes through each path correctly.
"""
import os, sys
os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_dummy"
os.environ["RAZORPAY_KEY_ID"]     = "rzp_test_dummy"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "dummy_wh_secret"
# Disable Supabase so auth.py sets supabase=None (we override manually below)
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
os.environ.pop("SUPABASE_KEY", None)

sys.path.insert(0, os.path.abspath("backend"))
os.chdir("backend")

import auth
from fastapi.testclient import TestClient
import api

# ── Build a mock supabase client ────────────────────────────────────────────
class MockExecute:
    def __init__(self, data): self.data = data

class MockQuery:
    def __init__(self, data): self._data = data
    def select(self, *a, **kw): return self
    def eq(self, *a, **kw): return self
    def limit(self, *a, **kw): return self
    def execute(self): return MockExecute(self._data)

class MockTable:
    def __init__(self, rows): self._rows = rows
    def select(self, *a, **kw): return MockQuery(self._rows)

class MockAuth:
    def get_user(self, jwt=None):
        class U: email = None
        class R: user = U()
        return R()
    def sign_in_with_password(self, creds):
        class Session:
            access_token = "fake_jwt_token"
            expires_at   = None
        class Res:
            session = Session()
        return Res()
    def sign_out(self): pass

class MockSupabase:
    auth = MockAuth()
    def table(self, name):
        return MockTable(self._rows_for(name))
    def _rows_for(self, name):
        return self._table_data.get(name, [])

def make_supabase(user_status):
    sb = MockSupabase()
    sb._table_data = {
        "users": [{"email": "locked@example.com", "status": user_status,
                   "id": "uid1", "niche": "all", "language_preference": "en",
                   "tier_id": None, "plan": "free"}],
        "subscription_tiers": [],
        "active_sessions": [],
    }
    return sb

# Inject mock into both auth and api modules
def set_locked(locked: bool):
    status_val = "locked" if locked else "active"
    sb = make_supabase(status_val)
    auth.supabase = sb
    api.supabase  = sb

client = TestClient(api.app)

# ─────────────────────────────────────────────────────────────────────────────
# Helper: craft a fake auth_token Bearer that the mock resolves
AUTH_TOKEN = "fake_auth_token_in_db"

# We need the mock to find the user by auth_token — update _rows_for to key on auth_token
class MockTableWithAuthToken:
    def __init__(self, rows, match_col=None, match_val=None):
        self._rows = rows; self._match_col = match_col; self._match_val = match_val
    def select(self, *a, **kw):
        return self
    def eq(self, col, val):
        if col == "auth_token":
            matched = [r for r in self._rows if r.get("auth_token") == val]
            return MockTableWithAuthToken(matched)
        if col == "email":
            matched = [r for r in self._rows if r.get("email") == val]
            return MockTableWithAuthToken(matched)
        if col == "status":
            matched = [r for r in self._rows if r.get("status") == val]
            return MockTableWithAuthToken(matched)
        return self
    def limit(self, n): return self
    def order(self, *a, **kw): return self
    def execute(self): return MockExecute(self._rows)

class SmartMockSupabase:
    auth = MockAuth()
    def __init__(self, user_rows): self._user_rows = user_rows
    def table(self, name):
        if name == "users":
            return MockTableWithAuthToken(self._user_rows)
        return MockTableWithAuthToken([])

def set_smart_mock(user_rows):
    sb = SmartMockSupabase(user_rows)
    auth.supabase = sb
    api.supabase  = sb

# ── LOCKED user rows (auth_token path) ──────────────────────────────────────
LOCKED_USER  = {"email": "locked@test.com", "auth_token": AUTH_TOKEN,
                "status": "locked", "id": "u1", "niche": "all",
                "language_preference": "en", "tier_id": None, "plan": "free"}
ACTIVE_USER  = {"email": "active@test.com", "auth_token": AUTH_TOKEN,
                "status": "active", "id": "u2", "niche": "all",
                "language_preference": "en", "tier_id": None, "plan": "free"}

print("=" * 60)
print("C2 TEST: Locked user enforcement")
print("=" * 60)

# ── Test 1: Locked user — request with pre-existing token ───────────────────
set_smart_mock([LOCKED_USER])
r = client.get("/api/creator/diagnostics?email=locked@test.com",
               headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
print(f"\n[1] Locked user — GET /api/creator/diagnostics with valid token")
print(f"    Status : {r.status_code}  (expected 403)")
print(f"    Body   : {r.text}")
assert r.status_code == 403, f"FAIL: expected 403, got {r.status_code}: {r.text}"

# ── Test 2: Active user — same endpoint passes through ──────────────────────
set_smart_mock([ACTIVE_USER])
r = client.get("/api/creator/diagnostics?email=active@test.com",
               headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
print(f"\n[2] Active user — GET /api/creator/diagnostics with valid token")
print(f"    Status : {r.status_code}  (expected 200 or 500, NOT 403)")
print(f"    Body   : {r.text}")
assert r.status_code != 403, f"FAIL: active user should NOT be blocked but got 403"

# ── Test 3: Locked user — /api/auth/verify returns valid:false ───────────────
set_smart_mock([LOCKED_USER])
r = client.post("/api/auth/verify", json={"session_token": AUTH_TOKEN})
print(f"\n[3] Locked user — POST /api/auth/verify")
print(f"    Status : {r.status_code}  (expected 200 with valid:false)")
print(f"    Body   : {r.text}")
body = r.json()
assert body.get("valid") == False, f"FAIL: expected valid:false, got {body}"
assert "locked" in body.get("error", "").lower(), f"FAIL: expected 'locked' in error: {body}"

# ── Test 4: Active user — /api/auth/verify returns valid:true ────────────────
set_smart_mock([ACTIVE_USER])
r = client.post("/api/auth/verify", json={"session_token": AUTH_TOKEN})
print(f"\n[4] Active user — POST /api/auth/verify")
print(f"    Status : {r.status_code}")
print(f"    Body   : {r.text}")
body = r.json()
assert body.get("valid") == True, f"FAIL: expected valid:true, got {body}"

# ── Test 5: Locked user — /api/auth/login returns 403 ───────────────────────
# For login, mock auth.sign_in_with_password to succeed, then status check locks
set_smart_mock([LOCKED_USER])
r = client.post("/api/auth/login", json={"email": "locked@test.com", "password": "anypass"})
print(f"\n[5] Locked user — POST /api/auth/login")
print(f"    Status : {r.status_code}  (expected 403)")
print(f"    Body   : {r.text}")
assert r.status_code == 403, f"FAIL: expected 403, got {r.status_code}: {r.text}"
assert "locked" in r.text.lower(), f"FAIL: expected 'locked' in response: {r.text}"

print("\n✓ ALL C2 LOCKED-USER TESTS PASSED")
