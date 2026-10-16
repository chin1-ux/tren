import os
from dotenv import load_dotenv
load_dotenv('backend/.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

names = ['Naina', 'Sadeness', 'Yetu Pone', 'Nenjukulle Nee', 'Milegi Milegi']
for n in names:
    res = sb.table('trends').select('id, audio_id, audio_title, audio_artist, audio_use_count').ilike('audio_title', f'%{n}%').limit(1).execute()
    if res.data:
        r = res.data[0]
        print(f"{n} -> id={r['id']}, audio_id={r['audio_id']}, title='{r['audio_title']}', artist='{r['audio_artist']}', count={r['audio_use_count']}")
    else:
        print(f"{n} -> NOT FOUND")
