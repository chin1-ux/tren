import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
from datetime import datetime, timedelta, timezone

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

print("=== REELS TABLE TOTAL ===")
total = sb.table("reels").select("id", count="exact").execute()
print(f"Total reels: {total.count}")

# --- QUERY 1: cron_job.py:305 ---
# "SELECT audio_title FROM reels WHERE scraped_at >= (now - 30 min)"
print("\n=== cron_job.py:305 (data quality check) ===")
now = datetime.now(timezone.utc)
recent_time = (now - timedelta(minutes=30)).isoformat()

# What the query returns (limited to 1000 by client)
res = sb.table("reels").select("audio_title").gte("scraped_at", recent_time).execute()
print(f"Rows returned by query (client-capped): {len(res.data)}")

# What the actual count is (no cap)
actual = sb.table("reels").select("id", count="exact").gte("scraped_at", recent_time).execute()
print(f"Actual matching rows in DB: {actual.count}")
print(f"Truncated: {'YES - LIVE BUG' if actual.count > len(res.data) else 'NO - safe'}")

# --- QUERY 2: api.py:1130 ---
# "SELECT ... FROM reels WHERE audio_title IN (titles)"
# Need to get the actual titles list from current trends
print("\n=== api.py:1130 (velocity delta pre-fetch) ===")
trends_res = sb.table("trends").select("audio_title").execute()
titles = list(set(t.get("audio_title") for t in (trends_res.data or []) if t.get("audio_title")))
print(f"Distinct audio_title values from trends: {len(titles)}")

if titles:
    # What the query returns (limited to 1000 by client)
    res2 = sb.table("reels").select("reel_id, audio_title, audio_artist, velocity_score").in_("audio_title", titles).execute()
    print(f"Rows returned by query (client-capped): {len(res2.data)}")

    # What the actual count is (no cap)
    actual2 = sb.table("reels").select("id", count="exact").in_("audio_title", titles).execute()
    print(f"Actual matching rows in DB: {actual2.count}")
    print(f"Truncated: {'YES - LIVE BUG' if actual2.count > len(res2.data) else 'NO - safe'}")

    # Per-title breakdown for top offenders
    print("\nPer-title breakdown (top 10 by reel count):")
    title_counts = []
    for t in titles[:50]:  # sample first 50
        cnt = sb.table("reels").select("id", count="exact").eq("audio_title", t).execute()
        if cnt.count > 0:
            title_counts.append((t, cnt.count))
    title_counts.sort(key=lambda x: x[1], reverse=True)
    for title, count in title_counts[:10]:
        print(f"  {title[:50]:50s} {count:5d} reels")
else:
    print("No titles found in trends table")
