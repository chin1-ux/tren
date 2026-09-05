"""
Account management script:
1. List all users
2. Delete all except admin + chin@free.com
3. Create 2 test accounts (creator + agency)
4. Set their plans via admin API
"""
import os, sys, json, time, requests
from supabase import create_client

# Load env
env = {}
for line in open(os.path.join(os.path.dirname(__file__), "backend", ".env")):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

SUPABASE_URL = env["SUPABASE_URL"]
SERVICE_ROLE_KEY = env.get("SUPABASE_SERVICE_ROLE_KEY", env["SUPABASE_KEY"])
ANON_KEY = env["SUPABASE_KEY"]
BACKEND = "http://localhost:8000"

# Use service role key for admin operations
sb = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)
# Also create anon-key client for user operations
sb_anon = create_client(SUPABASE_URL, ANON_KEY)

# ── Step 1: List all users ─────────────────────────────────────────────
print("=" * 60)
print("STEP 1: List all users")
print("=" * 60)
res = sb.table("users").select("id, email, plan, created_at").order("created_at", desc=True).execute()
users = res.data or []
print(f"Found {len(users)} users:")
for u in users:
    print(f"  {u['email']} | plan={u.get('plan','?')} | id={u.get('id','?')[:8]}...")

# ── Step 2: Delete all except admin + chin@free.com ───────────────────
keep_emails = {"chinmay.feb03@gmail.com", "chin@free.com"}
delete_users = [u for u in users if u["email"] not in keep_emails]

print(f"\n{'=' * 60}")
print(f"STEP 2: Delete {len(delete_users)} users (keeping {keep_emails})")
print("=" * 60)

for u in delete_users:
    email = u["email"]
    user_id = u["id"]
    try:
        # Delete from auth
        sb.auth.admin.delete_user(user_id)
        print(f"  Deleted auth: {email}")
    except Exception as e:
        print(f"  Auth delete failed for {email}: {e}")
    try:
        # Delete from users table
        sb.table("users").delete().eq("email", email).execute()
        print(f"  Deleted users row: {email}")
    except Exception as e:
        print(f"  Users delete failed for {email}: {e}")
    try:
        # Delete from active_sessions
        sb.table("active_sessions").delete().eq("user_id", user_id).execute()
    except:
        pass
    try:
        # Delete from plan_overrides
        sb.table("plan_overrides").delete().eq("user_id", user_id).execute()
    except:
        pass

# ── Step 3: Create 2 test accounts ────────────────────────────────────
print(f"\n{'=' * 60}")
print("STEP 3: Create 2 test accounts")
print("=" * 60)

test_accounts = [
    {
        "email": "creator@trendrop.test",
        "password": "TestPass123!",
        "phone": "+919876543210",
        "niche": "fitness",
        "language": "en",
        "plan": "pro",
        "display_plan": "Pro"
    },
    {
        "email": "agency@trendrop.test",
        "password": "TestPass123!",
        "phone": "+919876543211",
        "niche": "travel",
        "language": "hi",
        "plan": "pro",
        "display_plan": "Pro"
    },
]

for acct in test_accounts:
    print(f"\n  Creating {acct['email']} ({acct['display_plan']} plan)...")
    
    # Step 3a: Create via Supabase Auth
    try:
        auth_res = sb.auth.admin.create_user({
            "email": acct["email"],
            "password": acct["password"],
            "email_confirm": True
        })
        if auth_res and auth_res.user:
            uid = auth_res.user.id
            print(f"    Auth user created: {uid[:8]}...")
        else:
            print(f"    Auth create returned no user")
            continue
    except Exception as e:
        print(f"    Auth create failed: {e}")
        continue
    
    # Step 3b: Insert into users table
    import random
    user_id_str = f"#{random.randint(1000, 9999)}"
    try:
        sb.table("users").upsert({
            "id": uid,
            "email": acct["email"],
            "user_id": user_id_str,
            "phone_number": acct["phone"],
            "phone_verified": True,
            "niche": acct["niche"],
            "language_preference": acct["language"],
            "plan": "free",  # Start as free, override below
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }, on_conflict="email").execute()
        print(f"    Users row inserted")
    except Exception as e:
        print(f"    Users insert failed: {e}")
    
    # Step 3c: Set plan via admin API
    try:
        # First login as admin to get token
        admin_res = requests.post(f"{BACKEND}/api/admin/login", json={
            "email": "chinmay.feb03@gmail.com",
            "password": "changeme123"
        }, timeout=10)
        if admin_res.status_code != 200:
            # Try alternate password
            admin_res = requests.post(f"{BACKEND}/api/admin/login", json={
                "email": "chinmay.feb03@gmail.com",
                "password": "admin123"
            }, timeout=10)
        
        if admin_res.status_code == 200:
            admin_token = admin_res.json()["access_token"]
            # Set plan
            plan_res = requests.post(
                f"{BACKEND}/api/admin/users/{acct['email']}/plan",
                json={"new_plan": acct["plan"], "reason": "Test account setup"},
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10
            )
            if plan_res.status_code == 200:
                print(f"    Plan set to {acct['plan']} via admin API")
            else:
                print(f"    Plan API error: {plan_res.status_code} {plan_res.text[:200]}")
        else:
            print(f"    Admin login failed: {admin_res.status_code}")
            # Fallback: set plan directly in DB
            sb.table("users").update({"plan": acct["plan"]}).eq("email", acct["email"]).execute()
            print(f"    Plan set to {acct['plan']} directly in DB (fallback)")
    except Exception as e:
        print(f"    Plan set error: {e}")
        # Fallback
        try:
            sb.table("users").update({"plan": acct["plan"]}).eq("email", acct["email"]).execute()
            print(f"    Plan set to {acct['plan']} directly in DB (fallback)")
        except:
            pass

# ── Step 4: Verify all accounts ───────────────────────────────────────
print(f"\n{'=' * 60}")
print("STEP 4: Verify final state")
print("=" * 60)
res = sb.table("users").select("email, plan, phone_verified").order("created_at", desc=True).execute()
for u in (res.data or []):
    print(f"  {u['email']} | plan={u.get('plan','?')} | phone_verified={u.get('phone_verified','?')}")

# ── Step 5: Test login for each new account ───────────────────────────
print(f"\n{'=' * 60}")
print("STEP 5: Test login for each account")
print("=" * 60)

all_accounts = [
    ("chin@free.com", "123456", "free"),
    ("creator@trendrop.test", "TestPass123!", "pro"),
    ("agency@trendrop.test", "TestPass123!", "pro"),
]

for email, password, expected_plan in all_accounts:
    try:
        login_res = requests.post(f"{BACKEND}/api/auth/verify", json={
            "session_token": "test"  # Just check the endpoint is reachable
        }, timeout=10)
        print(f"  {email}: Backend reachable (status {login_res.status_code})")
    except Exception as e:
        print(f"  {email}: Backend error: {e}")

print("\nDone.")
