import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

print("=" * 80)
print("INVESTIGATING: content_type field in trends table")
print("=" * 80)

# Get recent trends and their content_type values
res = sb.table('trends').select('audio_title, content_type, audio_artist, niche_tag').order('created_at', desc=True).limit(20).execute()

print(f"\nSample trends with content_type:")
print("=" * 80)

# Collect unique content_type values
content_types = set()
for row in res.data:
    content_types.add(row['content_type'])
    print(f"audio_title: {row['audio_title']}")
    print(f"  content_type: {row['content_type']}")
    print(f"  audio_artist: {row['audio_artist']}")
    print(f"  niche_tag: {row['niche_tag']}")
    print("-" * 80)

print(f"\nUNIQUE content_type VALUES: {sorted(content_types)}")
print("=" * 80)

# Check if content_type correlates with audio_artist being a known music label
print("\nCORRELATION CHECK: content_type vs audio_artist")
print("=" * 80)
for ct in sorted(content_types):
    res = sb.table('trends').select('audio_title, audio_artist').eq('content_type', ct).limit(5).execute()
    print(f"\ncontent_type = '{ct}':")
    for row in res.data:
        print(f"  {row['audio_title']} by {row['audio_artist']}")
