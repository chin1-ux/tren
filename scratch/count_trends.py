import os, sys
sys.path.insert(0, "backend")
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("backend/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

print("Fetching all trends...")
trends_res = sb.table("trends").select("id, audio_title, audio_artist, reel_count, status").execute()
trends = trends_res.data or []
print(f"Total trends: {len(trends)}")

# Count trends with reel_count == 1
one_reel_trends = [t for t in trends if t.get("reel_count") == 1]
print(f"Trends with reel_count == 1: {len(one_reel_trends)}")

# Let's verify by checking reels in DB for each trend
print("\nVerifying creator and reel counts per trend via reels table:")
single_creator_trends_count = 0
single_reel_trends_count = 0
total_checked = 0

for t in trends:
    title = t.get("audio_title")
    artist = t.get("audio_artist")
    if not title:
        continue
    
    # Query reels with matching title and artist
    reels_res = sb.table("reels").select("owner_username, reel_id").eq("audio_title", title).eq("audio_artist", artist).execute()
    reels = reels_res.data or []
    
    unique_creators = set(r.get("owner_username") for r in reels if r.get("owner_username"))
    
    if len(reels) == 1:
        single_reel_trends_count += 1
    if len(unique_creators) <= 1:
        single_creator_trends_count += 1
        
    total_checked += 1

print(f"Total trends checked: {total_checked}")
print(f"Trends with exactly 1 associated reel in reels table: {single_reel_trends_count}")
print(f"Trends with exactly 1 unique creator in reels table: {single_creator_trends_count}")

# Print a few samples of single-creator trends
if single_creator_trends_count > 0:
    print("\nSample single-creator trends:")
    sample_count = 0
    for t in trends:
        title = t.get("audio_title")
        artist = t.get("audio_artist")
        if not title:
            continue
        reels_res = sb.table("reels").select("owner_username").eq("audio_title", title).eq("audio_artist", artist).execute()
        reels = reels_res.data or []
        unique_creators = set(r.get("owner_username") for r in reels if r.get("owner_username"))
        if len(unique_creators) <= 1:
            print(f"  ID: {t.get('id')} | Title: '{title}' | Artist: '{artist}' | Creators: {list(unique_creators)} | Status: {t.get('status')}")
            sample_count += 1
            if sample_count >= 5:
                break
