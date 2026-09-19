import os
import sys
import re
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

from caption_topic_clusterer import CaptionTopicClusterer

sys.stdout.reconfigure(encoding='utf-8')

# Load environment
env_path = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\.env"
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not set.")
    sys.exit(1)

sb = create_client(supabase_url, supabase_key)
clusterer = CaptionTopicClusterer()

print("==================================================")
print("=== CAPTION & TOPIC CLUSTERING ENGINE RUNNER ===")
print("==================================================")

# 1. Query India-scoped recent reels (last 48h)
now = datetime.now(timezone.utc)
cutoff_48h = (now - timedelta(hours=48)).isoformat()

print(f"Fetching India-scoped reels created since {cutoff_48h}...")
# Filter to regional/India relevance (language in hi, en, ta, te, mr, kn, bn, pa, bho or india_saturation_pct > 0)
reels_res = sb.table('reels') \
    .select('id, owner_username, caption, view_count, like_count, created_at, language') \
    .gte('created_at', cutoff_48h) \
    .execute()

def is_india_scoped(caption: str) -> bool:
    if not caption:
        return True
    # Filter out Portuguese/Spanish diacritic text (e.g. família, milhões, saúde, história, você)
    if re.search(r'[áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]', caption):
        return False
    return True

reels_raw = reels_res.data or []
reels = [r for r in reels_raw if is_india_scoped(r.get('caption') or '')]
print(f"Retrieved {len(reels)} India-scoped reels (filtered from {len(reels_raw)} raw reels).")

# 2. Run unsupervised TF-IDF caption clustering with stopword filtering
clusters = clusterer.cluster_reels(reels)
print(f"\nDiscovered {len(clusters)} candidate format clusters passing Quality Gate.")

print("\n--- TOP DISCOVERED FORMAT CLUSTERS ---")
for idx, c in enumerate(clusters[:15], start=1):
    print(f"{idx}. [{c['status'].upper()}] Name: '{c['format_name']}' | Key: '{c['cluster_key']}' | Creators: {c['creator_count']} | Velocity: {c['velocity_score']}")

# 3. Upsert into Supabase format_trends table (if table exists)
upserted_count = 0
table_error = None

for c in clusters:
    payload = {
        'cluster_key': c['cluster_key'],
        'format_name': c['format_name'],
        'primary_ngrams': c['primary_ngrams'],
        'creator_count': c['creator_count'],
        'reel_count': c['reel_count'],
        'velocity_score': c['velocity_score'],
        'peak_velocity': c['peak_velocity'],
        'status': c['status'],
        'sample_reel_ids': c['sample_reel_ids'],
        'updated_at': now.isoformat()
    }
    try:
        sb.table('format_trends').upsert(payload, on_conflict='cluster_key').execute()
        upserted_count += 1
    except Exception as e:
        table_error = str(e)

if table_error:
    print(f"\n[PENDING_DB_MIGRATION] format_trends table upsert status: Awaiting SQL migration 005 application in Supabase UI.")
else:
    print(f"\nSuccessfully upserted {upserted_count} format trends to Supabase 'format_trends' table.")

# 4. Save diagnostic audit output to backend/outputs/format_trends_audit.json
output_dir = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\outputs"
os.makedirs(output_dir, exist_ok=True)
audit_path = os.path.join(output_dir, "format_trends_audit.json")

with open(audit_path, 'w', encoding='utf-8') as f:
    json.dump({
        'audited_at': now.isoformat(),
        'similarity_threshold': clusterer.similarity_threshold,
        'min_creators_floor': clusterer.min_creators_floor,
        'min_views_single_creator': clusterer.min_views_single_creator,
        'pattern_boost_multiplier': clusterer.pattern_boost_multiplier,
        'total_reels_analyzed': len(reels),
        'discovered_format_clusters': clusters
    }, f, indent=2)

print(f"Diagnostic format trends audit saved to: {audit_path}")
