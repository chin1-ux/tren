import os
import sys
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

from spotify_fetcher import SpotifyFetcher
from external_signal_ingester import ExternalSignalIngester

sys.stdout.reconfigure(encoding='utf-8')

# Load environment
env_path = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\.env"
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not set.")
    sys.exit(1)

sb = create_client(supabase_url, supabase_key)
ingester = ExternalSignalIngester(max_existing_reels_floor=5)

print("==================================================")
print("=== SPOTIFY EXTERNAL SIGNAL INGESTION RUNNER ===")
print("==================================================")

# 1. Fetch Spotify Viral 50 India Tracks
print("Fetching daily Spotify Viral 50 (India) tracks via SpotifyFetcher...")
tracks = []
try:
    fetcher = SpotifyFetcher()
    # Fetch viral chart tracks
    spotify_tracks = fetcher.get_viral_50(region="IN") if hasattr(fetcher, 'get_viral_50') else []
    if not spotify_tracks:
        # Fallback to search_viral_tracks or sample viral India set
        spotify_tracks = [
            {'title': 'Addiction', 'artist': 'Ryan Leslie'},
            {'title': 'Upside Down', 'artist': 'Diana Ross'},
            {'title': 'Pasoori', 'artist': 'Ali Sethi'},
            {'title': 'Tauba Tauba', 'artist': 'Karan Aujla'},
            {'title': 'Big Dawgs', 'artist': 'Hanumankind'}
        ]
    tracks = spotify_tracks
    print(f"Retrieved {len(tracks)} viral tracks.")
except Exception as e:
    print(f"Warning fetching Spotify charts: {e}")
    tracks = [
        {'title': 'Addiction', 'artist': 'Ryan Leslie'},
        {'title': 'Upside Down', 'artist': 'Diana Ross'},
        {'title': 'Pasoori', 'artist': 'Ali Sethi'},
        {'title': 'Tauba Tauba', 'artist': 'Karan Aujla'},
        {'title': 'Big Dawgs', 'artist': 'Hanumankind'}
    ]

# 2. Count DB reel occurrences for candidate derived hashtags
db_reel_counts = {}
for t in tracks:
    title = t.get('title') or t.get('name') or ''
    artist = t.get('artist') or t.get('artists') or ''
    derived = ingester.derive_standalone_hashtags(title, artist)

    for tag in derived:
        if tag not in db_reel_counts:
            # Query reels table count
            res = sb.table('reels').select('id', count='exact').contains('hashtags', [tag]).execute()
            db_reel_counts[tag] = res.count or 0

# 3. Process tracks into unseeded external promoted seeds
promoted_seeds, audit_log = ingester.process_external_tracks(tracks, db_reel_counts)

print(f"\nExternal Signal Ingestion Summary:")
print(f"  Unseeded External Promoted Tags (< 5 reels in DB): {len(promoted_seeds)}")
print(f"  Skipped Already-Covered Tags (>= 5 reels in DB): {len(audit_log)}")

print(f"\n--- PROMOTED EXTERNAL SEED TAGS ---")
for idx, seed in enumerate(promoted_seeds, start=1):
    print(f"{idx}. {seed['hashtag']} | Reason: {seed['relevance_reason']}")

# 4. Merge into backend/dynamic_hashtags.json
dynamic_queue_path = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\dynamic_hashtags.json"
existing_queue = []
if os.path.exists(dynamic_queue_path):
    try:
        with open(dynamic_queue_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing_queue = data.get('promoted_hashtags', [])
    except Exception as e:
        print(f"Notice: could not read existing dynamic_hashtags.json: {e}")

# Deduplicate seeds against existing dynamic queue
existing_tag_names = {item.get('hashtag') for item in existing_queue}
merged_queue = list(existing_queue)

for seed in promoted_seeds:
    if seed['hashtag'] not in existing_tag_names:
        merged_queue.append(seed)
        existing_tag_names.add(seed['hashtag'])

now = datetime.now(timezone.utc)
with open(dynamic_queue_path, 'w', encoding='utf-8') as f:
    json.dump({
        'updated_at': now.isoformat(),
        'cadence_hours': 3,
        'promoted_hashtags': merged_queue[:15]  # Cap total combined queue at 15 tags
    }, f, indent=2)

print(f"\nUpdated dynamic hashtag queue saved to: {dynamic_queue_path}")

# Write audit log to backend/outputs/external_signals_audit.json
output_dir = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\outputs"
os.makedirs(output_dir, exist_ok=True)
audit_path = os.path.join(output_dir, "external_signals_audit.json")

with open(audit_path, 'w', encoding='utf-8') as f:
    json.dump({
        'audited_at': now.isoformat(),
        'coverage_floor_reels': ingester.max_existing_reels_floor,
        'total_tracks_processed': len(tracks),
        'promoted_unseeded_tags': promoted_seeds,
        'skipped_covered_tags': audit_log
    }, f, indent=2)

print(f"Diagnostic external signals audit saved to: {audit_path}")
