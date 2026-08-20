import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

print("=" * 80)
print("VERIFICATION: brand_deals table schema")
print("=" * 80)

# Check if brand_deals table exists and its schema
try:
    res = sb.table('brand_deals').select('*').limit(1).execute()
    if res.data:
        print("brand_deals table EXISTS")
        print("\nColumns:")
        for key in res.data[0].keys():
            print(f"  {key}")
    else:
        print("brand_deals table is EMPTY (exists but no data)")
except Exception as e:
    print(f"brand_deals table does NOT exist or error: {e}")

print("\n" + "=" * 80)
print("VERIFICATION: deal_payment_milestones table schema")
print("=" * 80)

try:
    res = sb.table('deal_payment_milestones').select('*').limit(1).execute()
    if res.data:
        print("deal_payment_milestones table EXISTS")
        print("\nColumns:")
        for key in res.data[0].keys():
            print(f"  {key}")
    else:
        print("deal_payment_milestones table is EMPTY (exists but no data)")
except Exception as e:
    print(f"deal_payment_milestones table does NOT exist or error: {e}")

print("\n" + "=" * 80)
print("VERIFICATION: user_notification_prefs table schema")
print("=" * 80)

try:
    res = sb.table('user_notification_prefs').select('*').limit(1).execute()
    if res.data:
        print("user_notification_prefs table EXISTS")
        print("\nColumns:")
        for key in res.data[0].keys():
            print(f"  {key}")
        print("\nSample data:")
        print(res.data[0])
    else:
        print("user_notification_prefs table is EMPTY (exists but no data)")
except Exception as e:
    print(f"user_notification_prefs table does NOT exist or error: {e}")
