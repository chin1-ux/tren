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
print("SQL: SELECT DISTINCT scraped_at, COUNT(*) FROM reels")
print("WHERE created_at >= NOW() - INTERVAL '2 days' GROUP BY scraped_at ORDER BY 1 DESC")
print("=" * 80)

two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

# Since Supabase Python client doesn't support raw SQL with GROUP BY easily,
# we'll fetch the data and aggregate in Python
res = sb.table('reels').select('scraped_at').gte('created_at', two_days_ago).execute()

# Aggregate distinct scraped_at values
from collections import Counter
scraped_at_counts = Counter(row['scraped_at'] for row in res.data)

print(f"\nDISTINCT scraped_at VALUES in last 2 days: {len(scraped_at_counts)}")
print("=" * 80)

for scraped_at, count in sorted(scraped_at_counts.items(), key=lambda x: x[0], reverse=True):
    print(f"scraped_at: {scraped_at}")
    print(f"  COUNT: {count}")
    print("-" * 80)

# Also check cron_runs to see how many runs in last 2 days
print("\nCROSS-CHECK: cron_runs in last 2 days")
print("=" * 80)
cron_res = sb.table('cron_runs').select('run_at, reels_scraped, status').gte('run_at', two_days_ago).order('run_at', desc=True).execute()
print(f"Total cron runs in last 2 days: {len(cron_res.data)}")
for row in cron_res.data:
    print(f"  run_at: {row['run_at']}, reels_scraped: {row['reels_scraped']}, status: {row['status']}")
