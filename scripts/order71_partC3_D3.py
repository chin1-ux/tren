import os
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")
sys.path.insert(0, "backend")
from supabase import create_client
from song_key import compute_song_key

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

print("=" * 95)
print("PART D3: INVESTIGATING ALFAAZ & WATCHLIST DEDUPLICATION")
print("=" * 95)

# 1. Inspect trends 4606 and 7229
t_res = sb.table("trends").select("id, status, audio_title, audio_artist, audio_id, first_detected_at").in_("id", [4606, 7229]).execute().data or []
print("Trends #4606 and #7229 details:")
for t in t_res:
    print(f"  Trend #{t['id']}: Status='{t.get('status')}' | Title='{t.get('audio_title')}' | Artist='{t.get('audio_artist')}' | Audio ID={t.get('audio_id')} | First Detected={t.get('first_detected_at')}")

# 2. Check why Alfaaz was in watchlist
alfaaz_wl = sb.table("watchlist").select("*").ilike("song_key", "%Alfaaz%").execute().data or []
print("\nWatchlist entries matching 'Alfaaz':")
for w in alfaaz_wl:
    print(f"  Audio ID={w.get('audio_id')} | Song Key='{w.get('song_key')}' | Score={w.get('score')} | Status='{w.get('status')}' | Reasons={w.get('reasons')}")

# 3. Load all trends that are not 'unqualified' (paginated to cover all 7,600+ rows)
all_trends = []
offset = 0
while True:
    t_chunk = sb.table("trends").select("audio_id, audio_title, audio_artist, status").neq("status", "unqualified").order("id", desc=False).range(offset, offset + 999).execute().data or []
    all_trends.extend(t_chunk)
    if len(t_chunk) < 1000:
        break
    offset += 1000

excluded_trend_aids = {str(t["audio_id"]) for t in all_trends if t.get("audio_id")}
excluded_trend_keys = {
    compute_song_key(t.get("audio_title"), t.get("audio_artist"))
    for t in all_trends
    if compute_song_key(t.get("audio_title"), t.get("audio_artist"))
}
print(f"\nTotal non-unqualified trend audio_ids to exclude: {len(excluded_trend_aids)}, song_keys: {len(excluded_trend_keys)} (Total trends scanned: {len(all_trends)})")
print(f"Is audio 1090536066806769 in excluded aids? {'1090536066806769' in excluded_trend_aids}")
print(f"Is 'alfaaz|hamzamalik' in excluded keys? {'alfaaz|hamzamalik' in excluded_trend_keys}")

# 4. Fetch active watchlist entries
wl_active = sb.table("watchlist").select("*").eq("status", "active").execute().data or []
print(f"Total active watchlist rows before filtering: {len(wl_active)}")

# 5. Fetch count history readings for established song check
now = datetime.now(timezone.utc)
cutoff_30d = (now - timedelta(days=30)).isoformat()
ach_res = sb.table("audio_count_history").select("audio_id, use_count, captured_at").gte("captured_at", cutoff_30d).not_.is_("use_count", "null").order("captured_at", desc=True).execute().data or []
ach_by_aid = {}
for r in ach_res:
    aid = str(r["audio_id"])
    ach_by_aid.setdefault(aid, []).append(r)

P95_30D = 2400000

# 6. Process watchlist candidates
candidates = []
unknown_artists_cnt = 0

for w in wl_active:
    aid = str(w.get("audio_id") or "").strip()
    sk = w.get("song_key") or ""
    reasons = w.get("reasons") or {}
    
    # Exclusion check: any audio_id or song_key matching a non-unqualified trend
    if aid in excluded_trend_aids or sk in excluded_trend_keys:
        continue
    if not aid or aid.lower() in ("0", "unknown", "none", "null"):
        continue
        
    title = reasons.get("title") or (sk.split("|")[0] if "|" in sk else None) or "Unknown Title"
    artist = reasons.get("artist") or (sk.split("|")[1] if "|" in sk else None)
    
    # If artist is missing or Unknown, fill from most common audio_artist in reels
    if not artist or artist.lower() in ("unknown", "null", "none"):
        reels_res = sb.table("reels").select("audio_artist").eq("audio_id", aid).limit(50).execute().data or []
        artists = [r["audio_artist"].strip() for r in reels_res if r.get("audio_artist") and r["audio_artist"].strip().lower() not in ("unknown", "null", "none")]
        if artists:
            artist = Counter(artists).most_common(1)[0][0]
        else:
            artist = "Unknown"
            
    if artist == "Unknown":
        unknown_artists_cnt += 1
        
    score = float(w.get("score") or reasons.get("score") or 0.0)
    creators = reasons.get("distinct_creators") or w.get("first_creators") or 0
    reels_cnt = reasons.get("total_reels") or w.get("first_reels") or 0
    
    # Check established song flag
    is_established = False
    latest_reading = ach_by_aid.get(aid, [{}])[0].get("use_count")
    if latest_reading and latest_reading >= P95_30D:
        is_established = True
        
    candidates.append({
        "audio_id": aid,
        "song_key": sk,
        "title": title,
        "artist": artist,
        "score": score,
        "creators": creators,
        "reels": reels_cnt,
        "latest_reading": latest_reading,
        "is_established": is_established
    })

# Sort by score desc
candidates.sort(key=lambda x: x["score"], reverse=True)

print(f"\nRemaining valid watchlist candidates after trend exclusion: {len(candidates)}")
print(f"Candidates with 'Unknown' artist: {unknown_artists_cnt} / {len(candidates)}")

established_songs = [c for c in candidates if c["is_established"]]
print(f"\nCandidates flagged as 'Established song' (ig_use_count >= 2.4M): {len(established_songs)}")
for es in established_songs:
    print(f"  - '{es['title']}' by '{es['artist']}' (Audio {es['audio_id']}): {es['latest_reading']:,} reels")

print("\n" + "=" * 95)
print("REFINED TOP 10 WATCHLIST ROWS (AFTER TREND DEDUPLICATION & ARTIST ENRICHMENT):")
print("=" * 95)
print(f"{'Rank':<4} | {'Title':<26} | {'Artist':<22} | {'Score':<8} | {'Creators':<8} | {'Reels':<6} | {'Est. Song'}")
print("-" * 95)
for idx, c in enumerate(candidates[:10], start=1):
    est_label = "YES" if c["is_established"] else "No"
    print(f"{idx:<4} | {c['title'][:24]:<26} | {c['artist'][:20]:<22} | {c['score']:<8.1f} | {c['creators']:<8} | {c['reels']:<6} | {est_label}")
print("=" * 95 + "\n")
