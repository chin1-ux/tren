#!/usr/bin/env python3
"""
Phase 1 verification - confirm admin schema restoration
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

print("=== Phase 1 Verification ===\n")

# Check tables
tables_to_check = ['admin_users', 'admin_audit_log', 'admin_audit_log_enhanced']
print("Checking table existence:")
for table in tables_to_check:
    try:
        result = supabase.table(table).select('*').limit(1).execute()
        print(f"  ✅ {table}: EXISTS")
    except Exception as e:
        print(f"  ❌ {table}: MISSING - {str(e)[:50]}")

# Check admin user
print("\nChecking admin user:")
try:
    result = supabase.table('admin_users').select('email, role').eq('email', 'chinmay.feb03@gmail.com').execute()
    if result.data:
        user = result.data[0]
        print(f"  ✅ Admin user found:")
        print(f"     Email: {user.get('email')}")
        print(f"     Role: {user.get('role')}")
    else:
        print("  ❌ Admin user not found")
except Exception as e:
    print(f"  ❌ Cannot check admin_users: {str(e)[:100]}")

print("\n=== Phase 1 Verification Complete ===")
