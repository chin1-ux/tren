import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

res = sb.table('trends').select('id,audio_title,audio_artist,audio_id,status,audio_use_count').in_('status', ['emerging', 'rising']).execute()
trends = res.data or []
print(f"Found {len(trends)} active trends:")
for t in trends:
    print(f"ID: {t['id']} | Status: {t['status']} | Audio: {t['audio_title']} by {t['audio_artist']} | Audio ID: {t.get('audio_id')} | Count: {t.get('audio_use_count')}")
