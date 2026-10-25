import os
import sys
sys.path.insert(0, os.path.abspath('backend'))
from dotenv import load_dotenv
load_dotenv('backend/.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

res = sb.table('trends').select('id, audio_id, audio_title, audio_artist, status').eq('is_voiceover', False).gt('window_hours_remaining', 0).order('velocity_avg', desc=True).limit(10).execute()
print(f"Found active trends: {len(res.data)}")
for t in res.data:
    aid = t.get('audio_id')
    reels = []
    if aid:
        r_res = sb.table('reels').select('id, reel_id, view_count, owner_username').eq('audio_id', str(aid)).order('view_count', desc=True).execute()
        reels = r_res.data or []
    top_view = reels[0]['view_count'] if reels else 0
    try:
        title = t.get('audio_title', '').encode('ascii', 'replace').decode('ascii')
        artist = t.get('audio_artist', '').encode('ascii', 'replace').decode('ascii')
        print(f"ID {t['id']}: '{title}' by '{artist}' (audio_id: {aid}) -> {len(reels)} reels (Top view: {top_view})")
    except Exception:
        print(f"ID {t['id']} -> {len(reels)} reels (Top view: {top_view})")
