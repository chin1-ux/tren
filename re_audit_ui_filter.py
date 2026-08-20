import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone, timedelta

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

print("=" * 80)
print("DISCREPANCY INVESTIGATION: UI vs Database")
print("=" * 80)

# Check if UI might be filtering by scraped_at instead of created_at
two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

print("\nQUERY 1: Filter by created_at (what I ran before)")
res1 = sb.table('reels').select('id, created_at, scraped_at').gte('created_at', two_days_ago).execute()
print(f"  Count: {len(res1.data)}")
if res1.data:
    print(f"  Most recent created_at: {res1.data[0]['created_at']}")
    print(f"  Most recent scraped_at: {res1.data[0]['scraped_at']}")

print("\nQUERY 2: Filter by scraped_at (what UI might be using)")
res2 = sb.table('reels').select('id, created_at, scraped_at').gte('scraped_at', two_days_ago).execute()
print(f"  Count: {len(res2.data)}")
if res2.data:
    print(f"  Most recent created_at: {res2.data[0]['created_at']}")
    print(f"  Most recent scraped_at: {res2.data[0]['scraped_at']}")

print("\nQUERY 3: Check for any reels with scraped_at in last 2 days")
res3 = sb.table('reels').select('id, created_at, scraped_at').gte('scraped_at', two_days_ago).order('scraped_at', desc=True).limit(10).execute()
print(f"  Count: {len(res3.data)}")
for row in res3.data:
    print(f"  ID: {row['id']}, created_at: {row['created_at']}, scraped_at: {row['scraped_at']}")

print("\nQUERY 4: Check total count in reels table")
res4 = sb.table('reels').select('id', count='exact').execute()
print(f"  Total reels in database: {res4.count}")

print("\nQUERY 5: Check most recent 5 reels regardless of date")
res5 = sb.table('reels').select('id, created_at, scraped_at').order('created_at', desc=True).limit(5).execute()
print(f"  Most recent 5 reels:")
for row in res5.data:
    print(f"  ID: {row['id']}, created_at: {row['created_at']}, scraped_at: {row['scraped_at']}")
