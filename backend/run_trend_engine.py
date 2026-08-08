#!/usr/bin/env python3
"""
Manually trigger just TrendEngine + TrendRefresher to classify fresh reels as rising/emerging.
Skip the Instagram scraping step since we already have fresh reels.
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

print("=" * 60)
print("MANUAL TREND ENGINE + REFRESHER RUN")
print("=" * 60)

# Step 1: TrendEngine
print("\n[STEP 1] Running TrendEngine.detect_trends()...")
try:
    from trend_engine import TrendEngine
    engine = TrendEngine()
    trend_ids = engine.detect_trends()
    stats = getattr(engine, 'last_run_stats', {})
    print(f"  [OK] TrendEngine complete. New trend IDs: {trend_ids}")
    print(f"  Stats: {stats}")
except Exception as e:
    print(f"  [ERROR] TrendEngine failed: {e}")
    import traceback
    traceback.print_exc()

# Step 2: TrendRefresher
print("\n[STEP 2] Running TrendRefresher.refresh_all()...")
try:
    from trend_refresher import TrendRefresher
    refresher = TrendRefresher()
    summary = refresher.refresh_all()
    print(f"  [OK] TrendRefresher complete. Summary: {summary}")
except Exception as e:
    print(f"  [ERROR] TrendRefresher failed: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Check DB status after
print("\n[STEP 3] Checking DB status after run...")
try:
    from supabase import create_client
    from collections import Counter
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    result = sb.table('trends').select('status').execute()
    counts = Counter(r['status'] for r in result.data)
    print(f"  Total trends: {len(result.data)}")
    print(f"  Status breakdown: {dict(counts)}")
except Exception as e:
    print(f"  [ERROR] DB check failed: {e}")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
