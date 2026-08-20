import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone, timedelta

# RAW SQL QUERY EQUIVALENT
# SELECT id, created_at, scraped_at, audio_title, reel_id, owner_username, view_count
# FROM reels
# WHERE created_at >= NOW() - INTERVAL '2 days'
# ORDER BY created_at DESC
# LIMIT 50

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

print("=" * 80)
print("RAW SQL QUERY EQUIVALENT:")
print("SELECT id, created_at, scraped_at, audio_title, reel_id, owner_username, view_count")
print("FROM reels")
print("WHERE created_at >= NOW() - INTERVAL '2 days'")
print("ORDER BY created_at DESC")
print("LIMIT 50")
print("=" * 80)
print(f"Supabase Project ID: gxxpvstrvphwhlqbvymv")
print("=" * 80)

two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
res = sb.table('reels').select('id, created_at, scraped_at, audio_title, reel_id, owner_username, view_count').gte('created_at', two_days_ago).order('created_at', desc=True).limit(50).execute()

print(f"\nTOTAL ROWS RETURNED: {len(res.data)}")
print("=" * 80)
print("RAW OUTPUT (FULL RESULT SET):")
print("=" * 80)
for row in res.data:
    print(f"ID: {row['id']}")
    print(f"  created_at: {row['created_at']}")
    print(f"  scraped_at: {row['scraped_at']}")
    print(f"  audio_title: {row['audio_title']}")
    print(f"  reel_id: {row['reel_id']}")
    print(f"  owner_username: {row['owner_username']}")
    print(f"  view_count: {row['view_count']}")
    print("-" * 80)
