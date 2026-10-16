import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv('backend/.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

print("=" * 80)
print("ORDER 77 ITEM 2: SAFE BATCHED REELS PRUNING EXECUTION")
print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)

# Load backup candidates
backup_path = "evidence/order77/prune_candidates_backup.json"
if not os.path.exists(backup_path):
    print(f"FAIL: Backup manifest {backup_path} not found! Run dry run first.")
    sys.exit(1)

with open(backup_path) as f:
    manifest = json.load(f)

# 1. Capture 20 sample active trends before pruning
print("1. Capturing 20 sample active trends BEFORE pruning...")
sample_trends_res = sb.table('trends').select('id, audio_id, audio_title, reel_count, status').in_('status', ['emerging', 'rising', 'resurging']).limit(20).execute()
before_sample = sample_trends_res.data or []
print(f"   Captured {len(before_sample)} sample trends.")

# 2. Before DB sizes
size_res_before = sb.rpc("get_db_size_bytes").execute()
db_size_before_mb = size_res_before.data / (1024 * 1024)
reels_cnt_before = sb.table('reels').select('id', count='exact').limit(1).execute().count
print(f"   Reels rows BEFORE: {reels_cnt_before:,}")
print(f"   Database size BEFORE: {db_size_before_mb:.2f} MB")

# 3. Identify and delete in batches of 500 using safe NOT EXISTS criteria directly in SQL or PostgREST
print("\n2. Executing safe pruning via batched delete...")
# To execute safely in batches:
# We query candidate IDs older than 14d not in protected audio_ids in batches of 500 and delete
cutoff_14d = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
active_res = sb.table('trends').select('audio_id').in_('status', ['emerging', 'rising', 'resurging']).execute()
active_aids = {r['audio_id'] for r in (active_res.data or []) if r.get('audio_id')}
saved_res = sb.table('watchlist').select('audio_id').execute()
saved_aids = {r['audio_id'] for r in (saved_res.data or []) if r.get('audio_id')}
protected_aids = active_aids | saved_aids

deleted_total = 0
batch_size = 500

while True:
    # Fetch next batch of 500 candidate IDs
    batch_res = (
        sb.table('reels')
        .select('id, audio_id')
        .lt('created_at', cutoff_14d)
        .order('id', desc=False)
        .limit(batch_size)
        .execute()
    )
    rows = batch_res.data or []
    if not rows:
        break
        
    ids_to_delete = [
        r['id'] for r in rows
        if not r.get('audio_id') or r.get('audio_id') not in protected_aids
    ]
    
    if not ids_to_delete:
        # If all rows in this window are protected, advance window or break
        break
        
    # Delete batch by ID
    del_res = sb.table('reels').delete().in_('id', ids_to_delete).execute()
    deleted_total += len(ids_to_delete)
    print(f"   Deleted batch: {len(ids_to_delete)} rows (Total deleted: {deleted_total:,})")
    
    # Cap single session execution to max 5,000 rows for high-safety incremental execution
    if deleted_total >= 5000:
        print("   Reached safety batch cap of 5,000 rows for this incremental run.")
        break

# 4. Read after status
print("\n3. Capturing state AFTER pruning...")
reels_cnt_after = sb.table('reels').select('id', count='exact').limit(1).execute().count
size_res_after = sb.rpc("get_db_size_bytes").execute()
db_size_after_mb = size_res_after.data / (1024 * 1024)
print(f"   Reels rows AFTER: {reels_cnt_after:,} (Freed {reels_cnt_before - reels_cnt_after:,} rows)")
print(f"   Database size AFTER: {db_size_after_mb:.2f} MB")

# 5. Diff 20 sample trends
print("\n4. Verifying 20 sample active trends diff...")
after_sample = sb.table('trends').select('id, audio_id, audio_title, reel_count, status').in_('status', ['emerging', 'rising', 'resurging']).limit(20).execute().data or []

diff_count = 0
for b, a in zip(before_sample, after_sample):
    if b['id'] != a['id'] or b.get('reel_count') != a.get('reel_count') or b.get('status') != a.get('status'):
        print(f"   [DIFF DETECTED] Trend {b['id']}: Before={b} vs After={a}")
        diff_count += 1

if diff_count == 0:
    print(f"   [PASS] ZERO diff across all {len(before_sample)} sample trends! reel_count and status are 100% identical.")
else:
    print(f"   [FAIL] {diff_count} discrepancies detected!")

print("=" * 80)
print("SAFE PRUNING EXECUTION COMPLETED")
print("=" * 80)
