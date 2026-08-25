#!/usr/bin/env python3
"""
Check if admin user exists and verify password hash
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_KEY")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=== Check Admin User ===\n")

# Check admin user
try:
    result = supabase.table("admin_users").select("*").eq("email", "chinmay.feb03@gmail.com").execute()
    if result.data:
        user = result.data[0]
        print(f"✅ Admin user found:")
        print(f"   Email: {user.get('email')}")
        print(f"   Role: {user.get('role')}")
        print(f"   Password hash: {user.get('password_hash')[:50]}...")
        print(f"   Failed attempts: {user.get('failed_login_attempts')}")
        print(f"   Locked until: {user.get('locked_until')}")
    else:
        print("❌ Admin user not found")
except Exception as e:
    print(f"❌ Error checking admin user: {e}")

print("\n=== Check Audit Log ===\n")

# Check audit log
try:
    result = supabase.table("admin_audit_log_enhanced").select("*").order("timestamp", desc=True).limit(5).execute()
    if result.data:
        print(f"✅ Recent audit log entries:")
        for entry in result.data:
            print(f"   {entry.get('timestamp')}: {entry.get('admin_email')} - {entry.get('action')} - {entry.get('details')}")
    else:
        print("❌ No audit log entries found")
except Exception as e:
    print(f"❌ Error checking audit log: {e}")
