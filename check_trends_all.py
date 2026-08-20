import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

# Search for trends with audio_title containing PITTAL
res = sb.table('trends').select('*').ilike('audio_title', '%PITTAL%').execute()
print("TRENDS with audio_title containing PITTAL:")
for row in res.data:
    print(f"ID: {row['id']}, audio_title: {row.get('audio_title')}, created_at: {row.get('created_at')}")

# Search for trends with audio_title containing EX-FILES
res = sb.table('trends').select('*').ilike('audio_title', '%EX-FILES%').execute()
print("\nTRENDS with audio_title containing EX-FILES:")
for row in res.data:
    print(f"ID: {row['id']}, audio_title: {row.get('audio_title')}, created_at: {row.get('created_at')}")

# Search for trends with audio_title containing EX FILES (without hyphen)
res = sb.table('trends').select('*').ilike('audio_title', '%EX FILES%').execute()
print("\nTRENDS with audio_title containing EX FILES:")
for row in res.data:
    print(f"ID: {row['id']}, audio_title: {row.get('audio_title')}, created_at: {row.get('created_at')}")

# Get recent trends from last 2 days
from datetime import datetime, timedelta, timezone
two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
res = sb.table('trends').select('*').gte('created_at', two_days_ago).order('created_at', desc=True).limit(20).execute()
print(f"\nRECENT TRENDS from last 2 days (total: {len(res.data)}):")
for row in res.data:
    print(f"ID: {row['id']}, audio_title: {row.get('audio_title')}, created_at: {row.get('created_at')}")
