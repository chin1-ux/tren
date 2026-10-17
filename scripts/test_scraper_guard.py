import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure scripts directory is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_scraper_guard import evaluate_guard_logic

now = datetime.now(timezone.utc)
results = []
results.append("=" * 80)
results.append("ORDER 79B ITEM 2: SCHEDULER GUARD UNIT TESTS")
results.append(f"Timestamp: {now.isoformat()}")
results.append("=" * 80)

# Case 1: Last run reels_scraped = 0, status = 'success', 100m ago
c1_time = (now - timedelta(minutes=100)).isoformat()
c1_data = [{"id": 1001, "created_at": c1_time, "run_at": c1_time, "status": "success", "reels_scraped": 0}]
skip1, msg1 = evaluate_guard_logic(c1_data, now_dt=now, min_gap_minutes=150)
results.append("\n[TEST CASE 1: reels_scraped = 0, 100 min ago]")
results.append(f"  Input: reels_scraped=0, status=success, elapsed=100m")
results.append(f"  Result skip={skip1} | Message: {msg1}")
assert skip1 is True, "Case 1 failed: should skip because 100m < 150m even with 0 reels scraped"
results.append("  PASS: Correctly recognized 0-reel run and enforced 150m lockout.")

# Case 2: Last run status = 'partial', 100m ago
c2_time = (now - timedelta(minutes=100)).isoformat()
c2_data = [{"id": 1002, "created_at": c2_time, "run_at": c2_time, "status": "partial", "reels_scraped": 50}]
skip2, msg2 = evaluate_guard_logic(c2_data, now_dt=now, min_gap_minutes=150)
results.append("\n[TEST CASE 2: status = 'partial', 100 min ago]")
results.append(f"  Input: reels_scraped=50, status=partial, elapsed=100m")
results.append(f"  Result skip={skip2} | Message: {msg2}")
assert skip2 is True, "Case 2 failed: should skip because partial run at 100m < 150m"
results.append("  PASS: Correctly recognized partial run and enforced lockout.")

# Case 3: Last run 100 min ago (under 150m threshold)
c3_time = (now - timedelta(minutes=100)).isoformat()
c3_data = [{"id": 1003, "created_at": c3_time, "run_at": c3_time, "status": "success", "reels_scraped": 300}]
skip3, msg3 = evaluate_guard_logic(c3_data, now_dt=now, min_gap_minutes=150)
results.append("\n[TEST CASE 3: elapsed = 100 min ago (under 150m threshold)]")
results.append(f"  Input: status=success, elapsed=100m")
results.append(f"  Result skip={skip3} | Message: {msg3}")
assert skip3 is True, "Case 3 failed: should skip when 100m < 150m"
results.append("  PASS: Correctly returned skip=True.")

# Case 4: Last run 200 min ago (>= 150m threshold)
c4_time = (now - timedelta(minutes=200)).isoformat()
c4_data = [{"id": 1004, "created_at": c4_time, "run_at": c4_time, "status": "success", "reels_scraped": 300}]
skip4, msg4 = evaluate_guard_logic(c4_data, now_dt=now, min_gap_minutes=150)
results.append("\n[TEST CASE 4: elapsed = 200 min ago (>= 150m threshold)]")
results.append(f"  Input: status=success, elapsed=200m")
results.append(f"  Result skip={skip4} | Message: {msg4}")
assert skip4 is False, "Case 4 failed: should proceed when 200m >= 150m"
results.append("  PASS: Correctly returned skip=False (PROCEED).")

# Case 5: Active run in progress (e.g. running 15 min ago)
c5_time = (now - timedelta(minutes=15)).isoformat()
c5_data = [
    {"id": 1006, "created_at": c5_time, "run_at": c5_time, "status": "in_progress", "reels_scraped": 0},
    {"id": 1005, "created_at": (now - timedelta(minutes=300)).isoformat(), "status": "success", "reels_scraped": 200}
]
skip5, msg5 = evaluate_guard_logic(c5_data, now_dt=now, min_gap_minutes=150)
results.append("\n[TEST CASE 5: Active run in_progress started 15 min ago]")
results.append(f"  Input: status=in_progress, age=15m")
results.append(f"  Result skip={skip5} | Message: {msg5}")
assert skip5 is True, "Case 5 failed: should skip when run is in progress"
results.append("  PASS: Correctly locked out execution while active run is in progress.")

results.append("\n" + "=" * 80)
results.append("ALL 5 UNIT TEST CASES PASSED SUCCESSFULLY.")
results.append("=" * 80)

output_text = "\n".join(results)
os.makedirs("evidence/order79", exist_ok=True)
with open("evidence/order79/guard_unit_tests.txt", "w", encoding="utf-8") as f:
    f.write(output_text)
print(output_text)
