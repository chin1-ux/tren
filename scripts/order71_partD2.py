import os
import sys
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")
from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

print("=" * 95)
print("PART D2: FRONTEND DEFAULT VIEW & LAST 3 RUNS TREND CREATION AUDIT")
print("=" * 95)

# 1. Check last 3 completed scraper runs in cron_runs
runs_res = sb.table("cron_runs").select("id, created_at, completed_at, status, reels_scraped, new_trends_count, trend_ids").order("created_at", desc=True).limit(5).execute()
runs = runs_res.data or []

print("\nLast 3 Completed Scraper Runs in cron_runs:")
print(f"{'Run ID':<10} | {'Completed At':<22} | {'Status':<12} | {'Reels Scraped':<14} | {'New Trends Count':<18} | {'Trend IDs'}")
print("-" * 115)
for r in runs[:3]:
    rid = str(r.get("id"))
    c_at = str(r.get("completed_at") or r.get("created_at") or "NULL")[:19]
    st = str(r.get("status"))
    rs = str(r.get("reels_scraped") or 0)
    ntc = str(r.get("new_trends_count") or 0)
    tids = str(r.get("trend_ids") or [])
    if len(tids) > 30:
        tids = tids[:27] + "..."
    print(f"{rid:<10} | {c_at:<22} | {st:<12} | {rs:<14} | {ntc:<18} | {tids}")

# 2. Check trends created in the last 72h grouped by status
print("\nTrends Created in the Last 72h by Status:")
from datetime import datetime, timezone, timedelta
now = datetime.now(timezone.utc)
h72_ago = (now - timedelta(hours=72)).isoformat()
trends_res = sb.table("trends").select("id, status, audio_title, language_final, niche_tag, reel_count, first_detected_at").gte("created_at", h72_ago).execute().data or []
by_status = {}
for t in trends_res:
    st = t.get("status") or "unknown"
    by_status.setdefault(st, []).append(t)

for st, t_list in by_status.items():
    print(f"  {st:<15}: {len(t_list)} trends")

# 3. Simulate frontend default query on page load
print("\nFrontend Default Feed Gating on Page Load:")
print("  Default Tab      : 'rising'")
print("  Default Language : 'all' (no language filter)")
print("  Default Niche    : 'all' (no niche filter)")
print("  Guest / Free Cap : limit = 20 items per rail")
print("  Pro Plan Cap     : limit = 50 items per rail")
