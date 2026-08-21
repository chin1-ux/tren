import os
from dotenv import load_dotenv
from supabase import create_client
import random

load_dotenv("backend/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Create test user in Supabase Auth
test_email = "test-agency@trendrop.internal"
test_password = "TestAgency2026!"

try:
    # Create auth user
    auth_res = supabase.auth.admin.create_user({
        "email": test_email,
        "password": test_password,
        "email_confirm": True
    })
    print(f"[OK] Created auth user: {test_email}")
except Exception as e:
    print(f"[WARN] Auth user might already exist: {e}")

# Create user in users table with agency plan
user_id = f"#{random.randint(1000, 9999)}"
user_data = {
    "email": test_email,
    "user_id": user_id,
    "phone_number": "+15550000000",
    "phone_verified": True,  # Skip phone verification for testing
    "niche": "all",
    "language_preference": "en",
    "plan": "pro",
    "credits_remaining": 1000,
    "status": "active",
    "subscription_status": "active",
    "created_at": "2026-08-14T00:00:00Z"
}

try:
    result = supabase.table("users").upsert(user_data, on_conflict="email").execute()
    print(f"[OK] Created/updated user in users table")
    print(f"  User ID: {user_id}")
    print(f"  Plan: agency")
    print(f"  Tier ID: 3")
except Exception as e:
    print(f"[ERROR] Failed to create user: {e}")

print(f"\nTest credentials:")
print(f"Email: {test_email}")
print(f"Password: {test_password}")
