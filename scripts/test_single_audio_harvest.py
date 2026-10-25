import os
import sys
sys.path.insert(0, os.path.abspath('backend'))
from dotenv import load_dotenv
load_dotenv('backend/.env')
from supabase import create_client
from audio_page_harvester import harvest_audio_reels

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

# Test on audio_id 1907900819862543 (Waqt by Paradox) which currently only has 1 reel
test_audio_id = "1907900819862543"
print(f"Starting top audio page harvest for audio_id: {test_audio_id}...")
results = harvest_audio_reels(audio_id=test_audio_id, supabase_client=sb, max_reels=15)
print(f"Harvest finished! Retrieved {len(results)} top reels from audio page:")
for r in results[:6]:
    print(f"  - Reel {r.get('reel_id')}: {r.get('view_count')} views by @{r.get('owner_username')}")
