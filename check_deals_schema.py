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
print("CHECKING: brand_deals table schema for required columns")
print("=" * 80)

# Required columns from create_creator_deal()
required_columns = [
    "creator_id",
    "brand_name",
    "deliverables",
    "rate_amount",
    "currency",
    "usage_rights",
    "exclusivity_clause",
    "timeline_start",
    "timeline_end",
    "cover_note_type",
    "status",
    "contract_pdf"
]

# Get actual schema
try:
    res = sb.table('brand_deals').select('*').limit(1).execute()
    if res.data:
        actual_columns = list(res.data[0].keys())
        print(f"Actual columns in brand_deals: {actual_columns}")
        print()
        
        missing = []
        for col in required_columns:
            if col not in actual_columns:
                missing.append(col)
                print(f"❌ MISSING: {col}")
            else:
                print(f"✓ EXISTS: {col}")
        
        if missing:
            print(f"\n❌ MISSING COLUMNS: {missing}")
        else:
            print("\n✓ All required columns exist")
    else:
        print("brand_deals table is empty, cannot check schema")
except Exception as e:
    print(f"Error checking brand_deals schema: {e}")

print("\n" + "=" * 80)
print("CHECKING: deal_payment_milestones table schema")
print("=" * 80)

required_milestone_columns = [
    "deal_id",
    "milestone_name",
    "amount",
    "due_date",
    "paid_status"
]

try:
    res = sb.table('deal_payment_milestones').select('*').limit(1).execute()
    if res.data:
        actual_columns = list(res.data[0].keys())
        print(f"Actual columns in deal_payment_milestones: {actual_columns}")
        print()
        
        missing = []
        for col in required_milestone_columns:
            if col not in actual_columns:
                missing.append(col)
                print(f"❌ MISSING: {col}")
            else:
                print(f"✓ EXISTS: {col}")
        
        if missing:
            print(f"\n❌ MISSING COLUMNS: {missing}")
        else:
            print("\n✓ All required columns exist")
    else:
        print("deal_payment_milestones table is empty, cannot check schema")
except Exception as e:
    print(f"Error checking deal_payment_milestones schema: {e}")
