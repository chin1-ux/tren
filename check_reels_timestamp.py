import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta, timezone

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

# Check reels from last 2 days
two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
res = sb.table('reels').select('id, created_at, scraped_at, audio_title').gte('created_at', two_days_ago).order('created_at', desc=True).limit(50).execute()

print(f"RAW OUTPUT - Reels from last 2 days (since {two_days_ago}):")
print(f"Total count: {len(res.data)}")
for row in res.data:
    print(row)
