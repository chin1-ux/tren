import os
from dotenv import load_dotenv
from supabase import create_client

# Load from backend/.env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', '.env')
load_dotenv(env_path)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

# Query last 20 reels
res = sb.table('reels').select('*').order('created_at', desc=True).limit(20).execute()
print("RAW OUTPUT:")
for row in res.data:
    print(row)
