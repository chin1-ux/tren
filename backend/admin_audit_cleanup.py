#!/usr/bin/env python3
"""
Admin audit and cleanup script
1. Check chinbinchin03@gmail.co current plan
2. Change to premium plan
3. Delete all other accounts except chinbinchin03@gmail.co
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=== ADMIN AUDIT AND CLEANUP ===\n")

# Step 1: Check chinbinchin03@gmail.co current status
print("Step 1: Checking chinbinchin03@gmail.co current status...")
res = supabase.table("users").select("*").eq("email", "chinbinchin03@gmail.co").execute()
if res.data:
    user = res.data[0]
    print(f"Current plan: {user.get('plan', 'N/A')}")
    print(f"Current status: {user.get('status', 'N/A')}")
else:
    print("User not found!")

# Step 2: Change to premium plan
print("\nStep 2: Changing chinbinchin03@gmail.co to pro (premium) plan...")
res = supabase.table("users").update({
    "plan": "pro",
    "tier_id": 3
}).eq("email", "chinbinchin03@gmail.co").execute()
print(f"Updated: {res.data}")

# Step 3: Get all users except chinbinchin03@gmail.co
print("\nStep 3: Getting all users except chinbinchin03@gmail.co...")
res = supabase.table("users").select("email, plan, created_at").execute()
users_to_delete = [u for u in res.data if u['email'] != 'chinbinchin03@gmail.co']
print(f"Found {len(users_to_delete)} users to delete:")
for user in users_to_delete:
    print(f"  - {user['email']} (plan: {user.get('plan', 'N/A')})")

# Step 4: Delete all other users
print("\nStep 4: Deleting all other users...")
for user in users_to_delete:
    res = supabase.table("users").delete().eq("email", user['email']).execute()
    print(f"Deleted: {user['email']}")

print("\n=== CLEANUP COMPLETE ===")
