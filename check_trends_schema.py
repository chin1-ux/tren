import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

# Get trends table schema
res = sb.table('trends').select('*').limit(1).execute()
if res.data:
    print("TRENDS TABLE COLUMNS:")
    for key in res.data[0].keys():
        print(f"  {key}")
else:
    print("No trends found")

# Query for trends with audio_title containing PITTAL, EX-FILES, or Musicaltunnel
res = sb.table('trends').select('*').ilike('audio_title', '%PITTAL%').execute()
print("\nTRENDS with audio_title containing PITTAL:")
for row in res.data:
    print(row)

res = sb.table('trends').select('*').ilike('audio_title', '%EX-FILES%').execute()
print("\nTRENDS with audio_title containing EX-FILES:")
for row in res.data:
    print(row)

res = sb.table('trends').select('*').ilike('audio_title', '%Musicaltunnel%').execute()
print("\nTRENDS with audio_title containing Musicaltunnel:")
for row in res.data:
    print(row)
