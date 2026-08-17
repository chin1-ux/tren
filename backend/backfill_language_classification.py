import os
import sys
import argparse
import json
from dotenv import load_dotenv
from supabase import create_client

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from instagram_scraper_browser import _detect_audio_language

STATE_FILE = os.path.join(os.path.dirname(__file__), '..', 'scratch', 'backfill_lang_state.txt')

def get_last_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            content = f.read().strip()
            if content.isdigit():
                return int(content)
    return 0

def save_last_id(last_id: int):
    with open(STATE_FILE, 'w') as f:
        f.write(str(last_id))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Run in live mode (writes to DB).')
    parser.add_argument('--limit', type=int, default=1000, help='Batch size')
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
    
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY'))

    # TODO: N rows for artists like pawan singh/khesari/manoj tiger/bhojpurisong 
    # were labeled 'hi' in an earlier pass but should be 'bho'. 
    # This script only touches 'en' rows. Needs a dedicated cleanup pass.
    
    last_id = get_last_id()
    print(f"Starting language backfill... Live mode: {args.live}")
    if last_id > 0:
        print(f"Resuming from ID > {last_id}")

    res = sb.table('trends').select('id, audio_title, audio_artist, sample_captions, language') \
            .eq('language', 'en') \
            .gt('id', last_id) \
            .order('id') \
            .limit(args.limit) \
            .execute()
            
    rows = res.data
    print(f"Found {len(rows)} rows to process.")
    
    updates = 0
    unresolved_examples = []
    
    for row in rows:
        row_id = row['id']
        title = row.get('audio_title') or ""
        artist = row.get('audio_artist') or ""
        audio_text = f"{title} {artist}".strip()
        
        # Read-only fetch from reels table
        caption_text = ""
        reels_res = sb.table('reels').select('caption').eq('audio_id', row_id).limit(5).execute()
        if reels_res.data:
            caption_text = " | ".join([r.get('caption') or "" for r in reels_res.data])
            
        hashtags = []
        
        new_lang = _detect_audio_language(audio_text, caption_text, hashtags)
        
        if new_lang != 'en':
            print(json.dumps({
                "id": row_id,
                "before_lang": "en",
                "after_lang": new_lang,
                "title": title,
                "artist": artist
            }))
            if args.live:
                sb.table('trends').update({"language": new_lang}).eq('id', row_id).execute()
            updates += 1
        else:
            unresolved_examples.append({
                "id": row_id,
                "title": title,
                "artist": artist,
                "caption_snippet": caption_text[:100]
            })
            
        if args.live:
            save_last_id(row_id)

    print(f"\nProcessed {len(rows)} rows. Updates: {updates}")
    
    if len(rows) > 0:
        print(f"Last processed ID: {rows[-1]['id']}")
        
    if not args.live:
        with open(os.path.join(os.path.dirname(__file__), '..', 'scratch', 'unresolved_remainder.json'), 'w', encoding='utf-8') as f:
            json.dump(unresolved_examples, f, indent=2)
        print(f"Exported {len(unresolved_examples)} unresolved tracks to scratch/unresolved_remainder.json")

if __name__ == '__main__':
    main()
