import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "backend")
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("backend/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

trend_ids = [111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125]

print("Retrieving the 15 trends created in the last run...")
trends_res = sb.table("trends").select("id", "audio_title", "audio_artist", "first_detected_at").in_("id", trend_ids).execute()
trends = trends_res.data or []

print(f"Retrieved {len(trends)} trends:")
for t in trends:
    title = t.get('audio_title', '')
    artist = t.get('audio_artist', '')
    # Safely print
    print(f"  ID: {t.get('id')} | Title: {repr(title)} | Artist: {repr(artist)} | Detected At: {t.get('first_detected_at')}")

print("\nChecking which of these had new reels scraped versus only old reels...")
# Let's see if the reels associated with these audio titles have scraped_at values during the last run.
# The last run started at 2026-07-09 06:15:58 UTC (which is 11:45 AM IST).
# Let's count reels for each trend title.
for t in trends:
    title = t.get('audio_title')
    artist = t.get('audio_artist')
    if not title:
        continue
    # Query reels with this audio_title
    reels_res = sb.table("reels").select("reel_id", "scraped_at").eq("audio_title", title).execute()
    reels = reels_res.data or []
    # Count total reels and reels scraped recently (say after 2026-07-09T06:00:00Z)
    total_reels = len(reels)
    recent_reels = [r for r in reels if r.get('scraped_at') and r.get('scraped_at') > "2026-07-09T06:00:00"]
    print(f"Title: {repr(title)} | Total Reels in DB: {total_reels} | Recently Scraped Reels (after 06:00 UTC): {len(recent_reels)}")
