import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Check reels table
try:
    r = sb.table('reels').select('reel_id,audio_title,scraped_at').order('scraped_at', desc=True).limit(5).execute()
    total = sb.table('reels').select('reel_id', count='exact').execute()
    print(f'Total reels: {total.count}')
    print('Most recent:')
    for row in r.data:
        print(f"  {row['audio_title']} @ {row['scraped_at']}")
except Exception as e:
    print(f'reels table error: {e}')
