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

print("=== Database Schema Check ===\n")

# Check for admin-related tables
tables_to_check = [
    'admin_users',
    'admin_audit_log', 
    'admin_audit_log_enhanced',
    'subscription_tiers',
    'plan_features'
]

print("Checking table existence:")
for table in tables_to_check:
    try:
        result = supabase.table(table).select('*').limit(1).execute()
        print(f"  ✅ {table}: EXISTS")
    except Exception as e:
        print(f"  ❌ {table}: MISSING - {str(e)[:50]}")

print("\n=== Admin Users Check ===")
try:
    result = supabase.table('admin_users').select('email, role').execute()
    if result.data:
        print(f"Found {len(result.data)} admin users:")
        for user in result.data:
            print(f"  - {user.get('email')}: {user.get('role')}")
    else:
        print("No admin users found")
except Exception as e:
    print(f"Cannot check admin_users: {str(e)[:100]}")

print("\n=== Subscription Tiers Columns Check ===")
try:
    # Try to check if subscription_tiers has the new columns
    result = supabase.table('subscription_tiers').select('*').limit(1).execute()
    if result.data and len(result.data) > 0:
        row = result.data[0]
        columns_to_check = ['api_limit_per_day', 'trend_views_per_day', 'features']
        print("Columns in subscription_tiers:")
        for col in columns_to_check:
            if col in row:
                print(f"  ✅ {col}: EXISTS")
            else:
                print(f"  ❌ {col}: MISSING")
        print(f"Available columns: {list(row.keys())}")
    else:
        print("No data in subscription_tiers to check columns")
except Exception as e:
    print(f"Cannot check subscription_tiers: {str(e)[:100]}")

print("\n=== Plan Features Table Check ===")
try:
    result = supabase.table('plan_features').select('*').limit(1).execute()
    if result.data:
        print(f"✅ plan_features table EXISTS with {len(result.data)} rows")
        if result.data:
            print(f"Sample columns: {list(result.data[0].keys())}")
    else:
        print("❌ plan_features table is empty or missing")
except Exception as e:
    print(f"❌ plan_features: MISSING - {str(e)[:50]}")
