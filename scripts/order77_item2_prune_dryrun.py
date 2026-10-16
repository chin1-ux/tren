import json
import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv('backend/.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

print("=" * 80)
print("ORDER 77 ITEM 2: SAFE REELS PRUNING DRY RUN")
print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)

now = datetime.now(timezone.utc)
cutoff_14d = (now - timedelta(days=14)).isoformat()
print(f"14-Day Age Cutoff: {cutoff_14d}")

# 1. Active trend audio_ids (emerging, rising, resurging)
active_res = sb.table('trends').select('audio_id').in_('status', ['emerging', 'rising', 'resurging']).execute()
active_audio_ids = {r['audio_id'] for r in (active_res.data or []) if r.get('audio_id')}
print(f"Active trend audio_ids protected: {len(active_audio_ids):,}")

# 2. Saved watchlist audio_ids
saved_res = sb.table('watchlist').select('audio_id').execute()
saved_audio_ids = {r['audio_id'] for r in (saved_res.data or []) if r.get('audio_id')}
print(f"User saved/watchlist audio_ids protected: {len(saved_audio_ids):,}")

protected_audio_ids = active_audio_ids | saved_audio_ids
print(f"Total distinct protected audio_ids: {len(protected_audio_ids):,}")

# 3. Query total reels count and old reels count
total_reels_res = sb.table('reels').select('id', count='exact').limit(1).execute()
total_reels = total_reels_res.count or 0
print(f"Total current rows in reels table: {total_reels:,}")

old_reels_res = sb.table('reels').select('id', count='exact').lt('created_at', cutoff_14d).execute()
old_reels_count = old_reels_res.count or 0
print(f"Reels older than 14 days: {old_reels_count:,}")

# 4. Paginate old reels in batches of 1000 to identify prune candidates
prune_candidate_ids = []
batch_size = 1000
offset = 0

print("\nScanning reels older than 14 days for prune eligibility...")
while True:
    batch_res = (
        sb.table('reels')
        .select('id, audio_id, created_at')
        .lt('created_at', cutoff_14d)
        .order('id', desc=False)
        .range(offset, offset + batch_size - 1)
        .execute()
    )
    rows = batch_res.data or []
    if not rows:
        break
    
    for r in rows:
        aid = r.get('audio_id')
        # If NULL audio_id or not in protected set -> eligible for pruning
        if not aid or aid not in protected_audio_ids:
            prune_candidate_ids.append(r['id'])
            
    offset += batch_size
    if offset % 10000 == 0:
        print(f"  Scanned {offset:,} rows... Found {len(prune_candidate_ids):,} candidates so far.")

# 5. Calculate bytes to be freed
bytes_per_row = 2910 # From Item 1 actual measurement (152.73 MB / 55,034 rows)
bytes_to_free = len(prune_candidate_ids) * bytes_per_row
mb_to_free = bytes_to_free / (1024 * 1024)

print("\n" + "=" * 80)
print("DRY RUN PRUNE SUMMARY:")
print("-" * 80)
print(f"Total current reels         : {total_reels:,}")
print(f"Reels older than 14 days    : {old_reels_count:,}")
print(f"Protected old reels kept    : {old_reels_count - len(prune_candidate_ids):,}")
print(f"Prune candidates identified : {len(prune_candidate_ids):,} rows")
print(f"Estimated bytes to be freed : {bytes_to_free:,} bytes ({mb_to_free:.2f} MB)")
print(f"Projected post-prune rows   : {total_reels - len(prune_candidate_ids):,}")
print(f"Projected post-prune DB size: {272.88 - mb_to_free:.2f} MB")

# Save candidate IDs backup
backup_path = "evidence/order77/prune_candidates_backup.json"
with open(backup_path, 'w') as f:
    json.dump({
        "timestamp": now.isoformat(),
        "total_candidates": len(prune_candidate_ids),
        "candidate_ids_sample": prune_candidate_ids[:500]
    }, f, indent=2)
print(f"Backup manifest saved to   : {backup_path}")
print("=" * 80)
