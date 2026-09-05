import os, json
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError('Supabase env not set')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

res = supabase.table('trends').select('*').execute()
rows = res.data or []
print(f'Total rows: {len(rows)}')
print(json.dumps(rows, indent=2)[:1000])
