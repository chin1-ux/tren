"""
One-shot script to reset the admin password.
Run once, then delete.
"""
import os
import sys
import bcrypt
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set")
    sys.exit(1)

client = create_client(SUPABASE_URL, SUPABASE_KEY)

ADMIN_EMAIL = "chinmay.feb03@gmail.com"
NEW_PASSWORD = "TrendropAdmin@2024!"

# 1. Hash the new password
new_hash = bcrypt.hashpw(NEW_PASSWORD.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
print(f"New hash: {new_hash}")

# 2. Update in DB
res = client.table("admin_users").update({
    "password_hash": new_hash,
    "failed_login_attempts": 0,
    "locked_until": None
}).eq("email", ADMIN_EMAIL).execute()

if res.data:
    print(f"Password reset for {ADMIN_EMAIL}")
    print(f"New password: {NEW_PASSWORD}")
    # Verify immediately
    stored = res.data[0]["password_hash"]
    ok = bcrypt.checkpw(NEW_PASSWORD.encode("utf-8"), stored.encode("utf-8"))
    print(f"Verification: {'PASS' if ok else 'FAIL'}")
else:
    print("Update returned no data")

# 3. Check subscription_tiers columns
print("\nChecking subscription_tiers columns...")
try:
    tiers = client.table("subscription_tiers").select("*").execute()
    print(f"Current tiers: {[t.get('name') for t in tiers.data]}")
    if tiers.data:
        print(f"Columns: {list(tiers.data[0].keys())}")
except Exception as e:
    print(f"Error reading subscription_tiers: {e}")
