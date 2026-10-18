import os
import sys
import json
from dotenv import load_dotenv
import collections

# Add backend directory to sys.path
backend_dir = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from audio_title_normalize import normalize_audio_title

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

from supabase import create_client
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch only the slim columns needed to evaluate C2
# Target <= 129 rows, ~10 KB transfer
cols = "id,audio_title,audio_artist,status,language_final,language,reel_count,audio_use_count"
res = sb.table("trends").select(cols)\
    .in_("status", ["emerging", "rising"])\
    .gt("window_hours_remaining", 0)\
    .eq("is_voiceover", False)\
    .eq("is_seed_data", False)\
    .neq("language_final", "bhojpuri")\
    .execute()

raw_data = res.data or []
print(f"Fetched {len(raw_data)} candidate rows.")

# Canonical Indian languages per spec B1:
# Hindi, Tamil, Telugu, Malayalam, Kannada, Punjabi, English, Instrumental
# (language_final values: hi, ta, te, ml, kn, pa, en, instrumental or title/name)
INDIA_LANGS = {
    'hi', 'hindi', 'ta', 'tamil', 'te', 'telugu', 'ml', 'malayalam',
    'kn', 'kannada', 'pa', 'punjabi', 'en', 'english', 'instrumental'
}

def analyze_rule(rule_name):
    # Step 1: Filter rows
    passing_rows = []
    for r in raw_data:
        reels = r.get("reel_count") or 0
        uses = r.get("audio_use_count") or 0
        if rule_name == 'A':
            if reels < 2:
                continue
        elif rule_name == 'B':
            if not (reels >= 2 or uses >= 50000):
                continue
        elif rule_name == 'C':
            pass
        passing_rows.append(r)
    
    # Step 2: Deduplicate one card per normalized title+artist, keeping highest creator_count
    groups = collections.defaultdict(list)
    for r in passing_rows:
        t_norm = normalize_audio_title(r.get("audio_title") or "").strip().lower()
        a_norm = (r.get("audio_artist") or "").strip().lower()
        key = (t_norm, a_norm)
        groups[key].append(r)
        
    deduped = []
    for key, items in groups.items():
        best = max(items, key=lambda x: (x.get("creator_count") or 0, x.get("reel_count") or 0, x.get("audio_use_count") or 0))
        deduped.append(best)
        
    # Step 3: Count India vs Global
    india_items = []
    global_items = []
    for item in deduped:
        lf = (item.get("language_final") or item.get("language") or "").strip().lower()
        if lf in INDIA_LANGS:
            india_items.append(item)
        # In Global mode: all audios (or global covers international + english/all)
        global_items.append(item)
        
    return {
        "rule": rule_name,
        "db_rows": len(passing_rows),
        "deduped_total": len(deduped),
        "india_count": len(india_items),
        "global_count": len(global_items)
    }

results = {
    "Rule A (reel_count >= 2)": analyze_rule('A'),
    "Rule B (reel_count >= 2 OR audio_use_count >= 50000)": analyze_rule('B'),
    "Rule C (no reel/use filter)": analyze_rule('C')
}

os.makedirs("evidence/order100", exist_ok=True)
with open("evidence/order100/c2_pool_measurement.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(json.dumps(results, indent=2))
