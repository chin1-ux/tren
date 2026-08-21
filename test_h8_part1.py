import os
import requests
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('backend/.env')
SUPA_URL = os.environ.get('SUPABASE_URL')
SUPA_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(SUPA_URL, SUPA_KEY)

EMAIL = "test_agency_h8_5@mailinator.com"
PASSWORD = "TestPassword123!"

# temporarily set agency limit to 2
supabase.table("subscription_tiers").update({"max_active_sessions": 2}).eq("name", "pro").execute()

try:
    auth_user_id = next((u.id for u in supabase.auth.admin.list_users() if u.email == EMAIL), None)
    if auth_user_id:
        supabase.auth.admin.delete_user(auth_user_id)
    supabase.table("users").delete().eq("email", EMAIL).execute()
except Exception:
    pass

# We will just use the frontend signup endpoint to let the backend do the heavy lifting of user creation!
# Ah wait, I can't use signup because of the IP rate limit.
# I will use admin create_user and then manually insert, but WITHOUT specifying id, just let Postgres generate it!
try:
    auth_res = supabase.auth.admin.create_user({"email": EMAIL, "password": PASSWORD, "email_confirm": True})
except Exception:
    pass

import random
supabase.table("users").upsert({
    "email": EMAIL,
    "user_id": f"#{random.randint(1000, 9999)}",
    "status": "active",
    "tier_id": supabase.table("subscription_tiers").select("id").eq("name", "pro").execute().data[0]["id"]
}, on_conflict="email").execute()

# NOW get the auto-generated INT ID
user_int_id = supabase.table("users").select("id").eq("email", EMAIL).execute().data[0]["id"]

# 3. Log in from Device 1
print("\n--- Login Device 1 ---")
login1 = requests.post("http://127.0.0.1:8000/api/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()
token1 = login1["session_token"]
verify1 = requests.post("http://127.0.0.1:8000/api/auth/verify", json={"session_token": token1})
print(f"Verify 1: {verify1.status_code}")

# 4. Log in from Device 2
print("\n--- Login Device 2 ---")
login2 = requests.post("http://127.0.0.1:8000/api/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()
token2 = login2["session_token"]
verify2 = requests.post("http://127.0.0.1:8000/api/auth/verify", json={"session_token": token2})
print(f"Verify 2: {verify2.status_code}")

# Save tokens for part 2
with open("tokens.json", "w") as f:
    json.dump({"token1": token1, "token2": token2}, f)

# 5. Check active sessions (should be 2)
print("\n--- Active Sessions (Expected 2) ---")
sessions = supabase.table("active_sessions").select("*").eq("user_id", user_int_id).execute().data
for s in sessions:
    print(f"ID: {s['id']}, Fingerprint: {s['device_fingerprint']}, Label: {s['device_label']}")

# 6. Log in from Device 3
print("\n--- Login Device 3 (Expected Reject) ---")
login3 = requests.post("http://127.0.0.1:8000/api/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()
token3 = login3["session_token"]
verify3 = requests.post("http://127.0.0.1:8000/api/auth/verify", json={"session_token": token3})
print(f"Verify 3 Status: {verify3.status_code}")
print(f"Verify 3 Body: {verify3.text}")

# 7. Check active sessions (should still be 2, identical to before)
print("\n--- Active Sessions Post-Reject (Expected 2 intact) ---")
sessions_post = supabase.table("active_sessions").select("*").eq("user_id", user_int_id).execute().data
for s in sessions_post:
    print(f"ID: {s['id']}, Fingerprint: {s['device_fingerprint']}, Label: {s['device_label']}")

# 8. Check session_cap_exceeded_count
count = supabase.table("users").select("session_cap_exceeded_count").eq("id", user_int_id).execute().data[0]
print(f"\nsession_cap_exceeded_count: {count['session_cap_exceeded_count']}")

with open("test_h8_tokens.json", "w") as f:
    json.dump({"token1": token1, "user_int_id": user_int_id, "email": EMAIL, "password": PASSWORD}, f)
