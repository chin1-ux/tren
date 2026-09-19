import os
import sys
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

from dynamic_hashtag_discoverer import DynamicHashtagDiscoverer

sys.stdout.reconfigure(encoding='utf-8')

# Load environment
env_path = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\.env"
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not set.")
    sys.exit(1)

sb = create_client(supabase_url, supabase_key)
discoverer = DynamicHashtagDiscoverer(max_queue_size=10, default_ttl_hours=72)

print("==================================================")
print("=== DYNAMIC HASHTAG DISCOVERY RUNNER ===")
print("==================================================")

now = datetime.now(timezone.utc)
cutoff_24h = (now - timedelta(hours=24)).isoformat()
cutoff_6h = (now - timedelta(hours=6)).isoformat()

# 1. Fetch recent reels from DB
print(f"Fetching reels created since {cutoff_24h}...")
try:
    reels_res = sb.table('reels').select('*').gte('created_at', cutoff_24h).execute()
    reels = reels_res.data
    print(f"Retrieved {len(reels)} recent reels.")
except Exception as e:
    print(f"Error querying reels table: {e}")
    sys.exit(1)

# Fetch verified audio IDs for confidence boosting
verified_audio_ids = set()
try:
    trends_res = sb.table('trends').select('audio_id').not_.is_('audio_id', 'null').limit(200).execute()
    for t in trends_res.data:
        aid = t.get('audio_id')
        if aid:
            verified_audio_ids.add(str(aid))
    print(f"Loaded {len(verified_audio_ids)} verified trend audio IDs for anchor co-occurrence boosting.")
except Exception as e:
    print(f"Warning: could not load trends table for anchor boosting: {e}")

# 2. Extract and group candidate hashtags
hashtag_reels_map = {}
for r in reels:
    tags = r.get('hashtags')
    extracted = set()
    if isinstance(tags, list):
        for t in tags:
            norm = discoverer.normalize_hashtag(t)
            if norm:
                extracted.add(norm)
    elif isinstance(tags, str):
        for t in tags.split(','):
            norm = discoverer.normalize_hashtag(t)
            if norm:
                extracted.add(norm)

    # Fallback to regex in caption
    cap = r.get('caption')
    if cap:
        import re
        cap_tags = re.findall(r"#([a-zA-Z0-9_]+)", cap)
        for t in cap_tags:
            norm = discoverer.normalize_hashtag(t)
            if norm:
                extracted.add(norm)

    for norm_tag in extracted:
        if norm_tag not in hashtag_reels_map:
            hashtag_reels_map[norm_tag] = []
        hashtag_reels_map[norm_tag].append(r)

print(f"Found {len(hashtag_reels_map)} unique candidate hashtags across recent reels.")

# 3. Evaluate candidates against Quality Gate
evaluated_candidates = []
audit_log = []

for tag, tag_reels in hashtag_reels_map.items():
    recent_reels = [r for r in tag_reels if r.get('created_at') and r.get('created_at') >= cutoff_6h]
    baseline_reels = [r for r in tag_reels if r.get('created_at') and r.get('created_at') < cutoff_6h]

    is_valid, reason, score = discoverer.evaluate_quality_gate(
        hashtag=tag,
        reels=tag_reels,
        recent_count=len(recent_reels),
        baseline_count=len(baseline_reels),
        verified_audio_ids=verified_audio_ids
    )

    candidate_record = {
        'hashtag': f"#{tag}",
        'score': score,
        'recent_count': len(recent_reels),
        'baseline_count': len(baseline_reels),
        'relevance_reason': reason,
        'unique_creators': len(set((r.get('owner_username') or r.get('creator_username') or r.get('owner_id')) for r in tag_reels if (r.get('owner_username') or r.get('creator_username') or r.get('owner_id'))))
    }

    if is_valid:
        evaluated_candidates.append(candidate_record)
    else:
        candidate_record['rejection_reason'] = reason
        audit_log.append(candidate_record)

print(f"\nQuality Gate Evaluation Summary:")
print(f"  Passed Quality Gate: {len(evaluated_candidates)} hashtags")
print(f"  Rejected (Noise/Spam/Low Diversity): {len(audit_log)} hashtags")

# 4. Build dynamic queue & write output files
promoted_queue, cap_audited = discoverer.build_queue(evaluated_candidates)
full_audit_log = audit_log + cap_audited

print(f"\n==================================================")
print(f"=== PROMOTED DYNAMIC HASHTAG QUEUE (Top {len(promoted_queue)}) ===")
print("==================================================")

for idx, item in enumerate(promoted_queue, start=1):
    print(f"{idx}. {item['hashtag']} | Score: {item['score']} | Reason: {item['relevance_reason']} | Creators: {item['unique_creators']}")

# Save promoted tags to backend/dynamic_hashtags.json
output_queue_path = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\dynamic_hashtags.json"
with open(output_queue_path, 'w', encoding='utf-8') as f:
    json.dump({
        'updated_at': now.isoformat(),
        'cadence_hours': 3,
        'promoted_hashtags': promoted_queue
    }, f, indent=2)

print(f"\nSaved promoted dynamic hashtags to: {output_queue_path}")

# Save audit log to backend/outputs/dynamic_discovery_audit.json
output_dir = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\outputs"
os.makedirs(output_dir, exist_ok=True)
output_audit_path = os.path.join(output_dir, "dynamic_discovery_audit.json")
with open(output_audit_path, 'w', encoding='utf-8') as f:
    json.dump({
        'audited_at': now.isoformat(),
        'total_candidates': len(hashtag_reels_map),
        'passed_count': len(evaluated_candidates),
        'rejected_count': len(full_audit_log),
        'rejected_items': full_audit_log[:50]  # Log top 50 rejected items
    }, f, indent=2)

print(f"Saved diagnostic audit log to: {output_audit_path}")
