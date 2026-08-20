import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

# Get detailed timing breakdown from last 5 cron runs
res = sb.table('cron_runs').select('*').order('run_at', desc=True).limit(5).execute()
print("TIMING BREAKDOWN - Last 5 cron runs:")
for row in res.data:
    print(f"\nRun ID: {row['id']}")
    print(f"  Run at: {row['run_at']}")
    print(f"  Duration: {row['duration_seconds']}s ({row['duration_seconds']/60:.1f} min)")
    print(f"  Stage: {row['stage']}")
    print(f"  Reels scraped: {row['reels_scraped']}")
    print(f"  New reels count: {row['new_reels_count']}")
    print(f"  New trends found: {row['new_trends_found']}")
    print(f"  Status: {row['status']}")
    print(f"  Trend detection skipped: {row['trend_detection_skipped']}")
