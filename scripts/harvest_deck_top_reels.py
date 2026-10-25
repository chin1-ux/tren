import os
import sys
import time
sys.path.insert(0, os.path.abspath('backend'))
from dotenv import load_dotenv
load_dotenv('backend/.env')
from supabase import create_client
from audio_page_harvester import harvest_audio_reels

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

# Get top 25 active trends in deck
res = sb.table('trends') \
    .select('id, audio_id, audio_title, audio_artist') \
    .eq('is_voiceover', False) \
    .gt('window_hours_remaining', 0) \
    .order('velocity_avg', desc=True) \
    .limit(20) \
    .execute()

trends = res.data or []
print(f"Checking top audio page reel coverage for {len(trends)} deck trends...")

harvested_count = 0
for t in trends:
    aid = t.get('audio_id')
    if not aid:
        continue
        
    # Check current reel count in DB
    r_res = sb.table('reels').select('id', count='exact').eq('audio_id', str(aid)).execute()
    count = r_res.count if hasattr(r_res, 'count') and r_res.count is not None else len(r_res.data or [])
    
    if count < 6:
        print(f"-> Audio {aid} ('{t.get('audio_title')}') only has {count} reels. Harvesting top audio page reels...")
        try:
            results = harvest_audio_reels(audio_id=str(aid), supabase_client=sb, max_reels=15)
            print(f"   Indexed {len(results)} top reels from audio page for {aid}!")
            harvested_count += 1
            time.sleep(2)  # courteous human pacing
        except Exception as err:
            print(f"   Error harvesting {aid}: {err}")
    else:
        print(f"✓ Audio {aid} ('{t.get('audio_title')}') already has {count} reels.")

print(f"\nAll done! Harvested top reels for {harvested_count} trending audios.")
