import os
import sys
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv('backend/.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
if not url or not key:
    print("FAIL: Missing SUPABASE_URL or SUPABASE_KEY")
    sys.exit(1)

sb = create_client(url, key)

print("=" * 80)
print("ORDER 77 ITEM 1: REAL DATABASE BYTES & PER-TABLE SIZES AUDIT")
print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)

# 1. Total DB Size
try:
    size_res = sb.rpc("get_db_size_bytes").execute()
    total_bytes = size_res.data
    total_mb = total_bytes / (1024 * 1024)
    print(f"\nTOTAL DATABASE SIZE (pg_database_size): {total_bytes:,} bytes ({total_mb:.2f} MB)")
except Exception as e:
    print(f"\nFAIL querying get_db_size_bytes: {e}")
    sys.exit(1)

# 2. Per-Table Sizes
try:
    tables_res = sb.rpc("get_table_sizes").execute()
    tables = tables_res.data or []
    print("\nPER-TABLE SIZE BREAKDOWN (Ordered by total_bytes DESC):")
    print("-" * 80)
    print(f"{'Table Name':<28} | {'Total MB':<10} | {'Table MB':<10} | {'Index MB':<10} | {'Est. Rows':<10}")
    print("-" * 80)
    for t in tables:
        t_name = t.get('table_name', 'unknown')
        tot_mb = t.get('total_bytes', 0) / (1024 * 1024)
        tbl_mb = t.get('table_bytes', 0) / (1024 * 1024)
        idx_mb = t.get('index_bytes', 0) / (1024 * 1024)
        rows = t.get('row_estimate', 0)
        rows_str = f"{rows:,}"
        print(f"{t_name:<28} | {tot_mb:<10.2f} | {tbl_mb:<10.2f} | {idx_mb:<10.2f} | {rows_str:<10}")
    print("-" * 80)
except Exception as e:
    print(f"\nFAIL querying get_table_sizes: {e}")
    sys.exit(1)

# 3. Growth rate calculation from reels table created_at distribution
# Query min and max created_at for reels to determine daily rate
try:
    reels_cnt_res = sb.table("reels").select("id", count="exact").limit(1).execute()
    total_reels = reels_cnt_res.count or 0
    
    reels_earliest = sb.table("reels").select("created_at").order("created_at", desc=False).limit(1).execute()
    reels_latest = sb.table("reels").select("created_at").order("created_at", desc=True).limit(1).execute()
    
    t0_str = reels_earliest.data[0]['created_at'] if reels_earliest.data else None
    t1_str = reels_latest.data[0]['created_at'] if reels_latest.data else None
    
    print("\nREELS TABLE LIFESPAN & DAILY INGESTION RATE:")
    print(f"Total rows in reels: {total_reels:,}")
    print(f"Earliest reel created_at: {t0_str}")
    print(f"Latest reel created_at  : {t1_str}")
    
    if t0_str and t1_str:
        # ISO parse
        from datetime import datetime
        # Strip trailing Z or tz offset
        def parse_iso(s):
            return datetime.fromisoformat(s.replace('Z', '+00:00'))
        dt0 = parse_iso(t0_str)
        dt1 = parse_iso(t1_str)
        lifespan_days = max(1.0, (dt1 - dt0).total_seconds() / 86400.0)
        reels_per_day = total_reels / lifespan_days
        
        # Bytes per reel row
        reels_info = next((t for t in tables if t.get('table_name') == 'reels'), None)
        if reels_info:
            reels_total_bytes = reels_info.get('total_bytes', 0)
            bytes_per_row = reels_total_bytes / max(1, total_reels)
            mb_per_day = (reels_per_day * bytes_per_row) / (1024 * 1024)
            print(f"Active lifespan: {lifespan_days:.2f} days")
            print(f"Ingestion rate: {reels_per_day:.1f} reels/day")
            print(f"Average footprint: {bytes_per_row:,.0f} bytes/row (table + indexes)")
            print(f"Growth rate: {mb_per_day:.2f} MB/day")
            
            remaining_mb = max(0.0, 450.0 - total_mb)
            days_to_450mb = remaining_mb / mb_per_day if mb_per_day > 0 else 999.0
            print(f"Remaining headroom to 450 MB: {remaining_mb:.2f} MB")
            print(f"Days to 450 MB ceiling: {days_to_450mb:.1f} days")
except Exception as e:
    print(f"Error computing reels growth rate: {e}")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
