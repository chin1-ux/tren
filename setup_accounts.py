"""Delete all users except admin + chin@free.com, create creator + agency test accounts"""
from supabase import create_client
import time, random, requests

env = {}
for line in open("backend/.env"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

sb = create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"])
BACKEND = "http://localhost:8000"

# ── Step 1: Delete all users except chin@free.com ──────────────────────
print("=" * 60)
print("STEP 1: Clean up DB users")
print("=" * 60)
res = sb.table("users").select("email, id, plan").execute()
all_users = res.data or []
keep = "chin@free.com"
to_delete = [u for u in all_users if u["email"] != keep]
print(f"Found {len(all_users)} users. Keeping {keep}. Deleting {len(to_delete)}.")

for u in to_delete:
    email = u["email"]
    uid = u["id"]
    # Delete from Supabase Auth
    try:
        sb.auth.admin.delete_user(str(uid))
    except:
        pass
    # Delete from users table
    try:
        sb.table("users").delete().eq("email", email).execute()
    except:
        pass
    # Delete sessions
    try:
        sb.table("active_sessions").delete().eq("user_id", uid).execute()
    except:
        pass
    # Delete plan overrides
    try:
        sb.table("plan_overrides").delete().eq("user_id", uid).execute()
    except:
        pass
    print(f"  Deleted: {email}")

# ── Step 2: Create 2 test accounts ────────────────────────────────────
print(f"\n{'=' * 60}")
print("STEP 2: Create test accounts")
print("=" * 60)

accounts = [
    {"email": "creator@trendrop.test", "password": "Creator123!", "niche": "fitness", "lang": "en", "phone": "+919876543210", "plan": "pro"},
    {"email": "agency@trendrop.test", "password": "Agency1234!", "niche": "travel", "lang": "hi", "phone": "+919876543211", "plan": "pro"},
]

for acct in accounts:
    print(f"\n  Creating {acct['email']} ({acct['plan']})...")
    
    # Create in Supabase Auth (delete first if exists)
    try:
        # Try to find and delete existing auth user
        auth_list = sb.auth.admin.list_users()
        for au in (auth_list if isinstance(auth_list, list) else []):
            if au.email == acct["email"]:
                sb.auth.admin.delete_user(au.id)
                print(f"    Deleted old auth user: {acct['email']}")
                break
    except:
        pass
    
    try:
        auth_res = sb.auth.admin.create_user({
            "email": acct["email"],
            "password": acct["password"],
            "email_confirm": True
        })
        uid = auth_res.user.id
        print(f"    Auth user: {uid[:12]}...")
    except Exception as e:
        print(f"    Auth create FAILED: {e}")
        continue
    
    # Insert into users table (id is auto-increment, don't pass it)
    user_id_str = f"#{random.randint(1000, 9999)}"
    try:
        sb.table("users").insert({
            "email": acct["email"],
            "user_id": user_id_str,
            "phone_number": acct["phone"],
            "phone_verified": True,
            "niche": acct["niche"],
            "language_preference": acct["lang"],
            "plan": "free",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }).execute()
        print(f"    Users row created")
    except Exception as e:
        print(f"    Users insert FAILED: {e}")
        continue
    
    # Set plan via direct DB update
    try:
        sb.table("users").update({"plan": acct["plan"]}).eq("email", acct["email"]).execute()
        print(f"    Plan set to {acct['plan']}")
    except Exception as e:
        print(f"    Plan update FAILED: {e}")

# ── Step 3: Verify final state ────────────────────────────────────────
print(f"\n{'=' * 60}")
print("STEP 3: Verify")
print("=" * 60)
res = sb.table("users").select("email, plan, phone_verified").execute()
for u in (res.data or []):
    print(f"  {u['email']} | plan={u.get('plan')} | phone_verified={u.get('phone_verified')}")

# ── Step 4: Test Supabase Auth login for each account ─────────────────
print(f"\n{'=' * 60}")
print("STEP 4: Test Supabase Auth login")
print("=" * 60)

test_logins = [
    ("chin@free.com", "123456"),
    ("creator@trendrop.test", "Creator123!"),
    ("agency@trendrop.test", "Agency1234!"),
]

for email, pw in test_logins:
    try:
        from supabase import create_client
        sb_anon = create_client(env["SUPABASE_URL"], env["SUPABASE_KEY"])
        login = sb_anon.auth.sign_in_with_password({"email": email, "password": pw})
        if login.session:
            token = login.session.access_token[:20]
            print(f"  {email}: LOGIN OK (token: {token}...)")
            # Test verify endpoint
            verify = requests.post(f"{BACKEND}/api/auth/verify", json={"session_token": login.session.access_token}, timeout=10)
            vdata = verify.json()
            print(f"    verify: success={vdata.get('success')} valid={vdata.get('valid')} plan={vdata.get('user',{}).get('plan','?')}")
        else:
            print(f"  {email}: LOGIN FAILED (no session)")
    except Exception as e:
        print(f"  {email}: LOGIN ERROR: {e}")

print("\nDone.")
