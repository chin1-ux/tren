import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

# Data contract query for trends
print("=== DATA CONTRACT: TRENDS TABLE ===")
res = sb.table('trends').select('id, audio_title, audio_artist, niche_tag, velocity_avg, first_detected_at, status, sample_captions').in_('audio_title', ['PITTAL', 'EX-FILES', 'Musicaltunnel']).execute()
print("Trends for PITTAL, EX-FILES, Musicaltunnel:")
for row in res.data:
    print(f"  ID: {row['id']}, audio_title: {row['audio_title']}, audio_artist: {row['audio_artist']}, niche_tag: {row['niche_tag']}, velocity_avg: {row['velocity_avg']}, first_detected_at: {row['first_detected_at']}, status: {row['status']}")
    print(f"  sample_captions: {row.get('sample_captions')}")

# Check if audio_type column exists
print("\n=== CHECKING FOR audio_type COLUMN ===")
try:
    res = sb.table('trends').select('audio_type').limit(1).execute()
    print("audio_type column EXISTS in trends table")
except Exception as e:
    print(f"audio_type column DOES NOT EXIST in trends table: {e}")

# Check sample reels for these trends
print("\n=== SAMPLE REELS FOR THESE TRENDS ===")
trend_ids = [row['id'] for row in res.data if 'id' in row]
if trend_ids:
    # Get audio_ids from trends
    audio_ids = [row.get('audio_id') for row in res.data if row.get('audio_id')]
    print(f"Audio IDs: {audio_ids}")
    
    if audio_ids:
        for audio_id in audio_ids[:3]:  # Check first 3
            res = sb.table('reels').select('reel_id, caption, owner_username, view_count, niche_tag').eq('audio_id', str(audio_id)).order('view_count', desc=True).limit(5).execute()
            print(f"\nReels for audio_id {audio_id}:")
            for row in res.data:
                print(f"  reel_id: {row['reel_id']}, caption: {row['caption'][:50] if row['caption'] else None}..., owner: {row['owner_username']}, views: {row['view_count']}, niche: {row['niche_tag']}")
else:
    print("No trend IDs found")

# Check user profile niche
print("\n=== USER PROFILE NICHE CHECK ===")
try:
    res = sb.table('users').select('*').limit(1).execute()
    if res.data:
        print("Users table columns:")
        for key in res.data[0].keys():
            print(f"  {key}")
    else:
        print("No users found")
except Exception as e:
    print(f"Users table may not exist or error: {e}")
