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
print("CRITICAL DISCREPANCY INVESTIGATION")
print("=" * 80)
print("Current time (UTC):", datetime.now(timezone.utc).isoformat())
print("=" * 80)

# The user says they see 0 reels in UI for 2 days
# My query showed 1000 reels with created_at >= 2 days ago
# But only 10 with scraped_at >= 2 days ago
# This suggests UI might be filtering by scraped_at

two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
print(f"\nTwo days ago: {two_days_ago}")

# Check the actual timestamps
print("\nQUERY: Most recent 10 reels by created_at")
res = sb.table('reels').select('id, created_at, scraped_at').order('created_at', desc=True).limit(10).execute()
for row in res.data:
    print(f"  ID: {row['id']}, created_at: {row['created_at']}, scraped_at: {row['scraped_at']}")

print("\nQUERY: Most recent 10 reels by scraped_at")
res = sb.table('reels').select('id, created_at, scraped_at').order('scraped_at', desc=True).limit(10).execute()
for row in res.data:
    print(f"  ID: {row['id']}, created_at: {row['created_at']}, scraped_at: {row['scraped_at']}")

# Check if there's a timezone issue - maybe the UI is using local time filtering
print("\nQUERY: Check if scraped_at is actually recent (last 48 hours)")
res = sb.table('reels').select('id, created_at, scraped_at').gte('scraped_at', two_days_ago).execute()
print(f"  Count: {len(res.data)}")
if res.data:
    print(f"  Most recent scraped_at: {res.data[0]['scraped_at']}")
    print(f"  Age of most recent scrape: {(datetime.now(timezone.utc) - datetime.fromisoformat(res.data[0]['scraped_at'].replace('Z', '+00:00'))).total_seconds() / 3600:.1f} hours")

# Check the actual last cron run
print("\nQUERY: Last cron run from cron_runs table")
res = sb.table('cron_runs').select('*').order('run_at', desc=True).limit(1).execute()
if res.data:
    print(f"  Last run at: {res.data[0]['run_at']}")
    print(f"  Reels scraped: {res.data[0]['reels_scraped']}")
    print(f"  Status: {res.data[0]['status']}")
