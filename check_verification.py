import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Avoid encoding issues on Windows terminals
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv('backend/.env')
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

print('--- RECENT COMPLETED TRENDS ---')
res = sb.table('trends').select('id,audio_title,audio_artist,language,niche_tag,llm_classification_status,why_this_works,ideal_content_description,audio_cue_second,text_overlay_template,hook_brief,first_detected_at,sample_captions').eq('llm_classification_status', 'completed').order('first_detected_at', desc=True).limit(5).execute()
trends = res.data or []
for t in trends:
    print(f"ID: {t['id']} | Title: {t['audio_title']} | Artist: {t['audio_artist']} | Lang: {t['language']} | Niche: {t['niche_tag']} | Status: {t['llm_classification_status']}")
    print(f"  Sample Captions: {repr((t.get('sample_captions') or '')[:120])}")
    print(f"  Why works: {repr(t.get('why_this_works'))}")
    print(f"  Ideal desc: {repr(t.get('ideal_content_description'))}")
    print(f"  Overlay: {repr(t.get('text_overlay_template'))}")
    print(f"  Hook: {repr(t.get('hook_brief'))}")
    print('-'*40)

print('\n--- TRENDS STATUS COUNTS ---')
res_all = sb.table('trends').select('llm_classification_status').execute()
statuses = [row['llm_classification_status'] for row in (res_all.data or [])]
from collections import Counter
print(Counter(statuses))
