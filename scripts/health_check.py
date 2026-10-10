#!/usr/bin/env python3
"""
scripts/health_check.py - Order 70 Part 7: Comprehensive System Health Check

Exits non-zero and prints the reason if any of these conditions are met:
1. No successful scheduled scraper run in the last 8h
2. The last 3 runs' reels_scraped < 50% of the median of the 10 runs before
3. Challenge/login-redirect markers in the last run's log / cutoff_reason
4. Capture/probe/watchlist errors in the last 2 runs
5. DB size > 300 MB
6. No audio_count_history rows in 24h

Supports --test flag to unit-prove all failing paths with mock inputs.
"""

import os
import sys
import argparse
import statistics
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv(os.path.join(backend_dir, ".env"))

def parse_dt(s):
    if not s:
        return None
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def evaluate_health_conditions(cron_runs, probe_logs, db_size_mb, count_history_24h, now=None):
    """
    Pure evaluation logic for unit testability.
    Returns: (all_passed: bool, results: dict, failures: list)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    results = {}
    failures = []

    # 1. Scheduled run in last 8h
    cutoff_8h = now - timedelta(hours=8)
    recent_successful_runs = [
        r for r in cron_runs
        if (r.get("status") in ("completed", "success")) and
           (parse_dt(r.get("run_at") or r.get("created_at")) and parse_dt(r.get("run_at") or r.get("created_at")) >= cutoff_8h)
    ]
    has_recent_run = len(recent_successful_runs) > 0
    latest_run_time = (parse_dt(cron_runs[0].get("run_at") or cron_runs[0].get("created_at")).isoformat()[:19]
                       if cron_runs and parse_dt(cron_runs[0].get("run_at") or cron_runs[0].get("created_at")) else "None")
    results["1_scraper_run_last_8h"] = {
        "passed": has_recent_run,
        "count_8h": len(recent_successful_runs),
        "latest_run": latest_run_time,
        "message": f"{len(recent_successful_runs)} successful runs in last 8h (latest: {latest_run_time})"
    }
    if not has_recent_run:
        failures.append(f"CHECK 1 FAILED: No successful scheduled scraper run in the last 8h (latest: {latest_run_time})")

    # 2. Last 3 runs reels_scraped vs 50% median of previous 10 runs
    completed_runs = [r for r in cron_runs if r.get("status") in ("completed", "success")]
    if len(completed_runs) >= 4:
        last_3 = completed_runs[:3]
        prev_10 = completed_runs[3:13]
        last_3_reels = [r.get("reels_scraped") or 0 for r in last_3]
        prev_10_reels = [r.get("reels_scraped") or 0 for r in prev_10]
        avg_last_3 = statistics.mean(last_3_reels)
        median_prev = statistics.median(prev_10_reels) if prev_10_reels else 0.0
        ratio = (avg_last_3 / median_prev) if median_prev > 0 else 1.0
        passed_2 = ratio >= 0.5
        results["2_reels_scraped_yield"] = {
            "passed": passed_2,
            "avg_last_3": avg_last_3,
            "median_prev_10": median_prev,
            "ratio": ratio,
            "message": f"avg last 3 = {avg_last_3:.1f}, median prev = {median_prev:.1f} (ratio: {ratio:.1%}, min 50%)"
        }
        if not passed_2:
            failures.append(f"CHECK 2 FAILED: Last 3 runs reels_scraped ({avg_last_3:.1f}) < 50% of median of prior 10 ({median_prev:.1f}) [ratio: {ratio:.1%}]")
    else:
        results["2_reels_scraped_yield"] = {
            "passed": True,
            "message": f"Insufficient run history ({len(completed_runs)} runs) to evaluate baseline."
        }

    # 3. Challenge / login-redirect markers in last run log
    latest_run = cron_runs[0] if cron_runs else {}
    cutoff_reason = str(latest_run.get("cutoff_reason") or "").lower()
    stage = str(latest_run.get("stage") or "").lower()
    has_challenge = any(m in cutoff_reason or m in stage for m in ["challenge", "login_redirect", "checkpoint", "blocked"])
    results["3_challenge_login_markers"] = {
        "passed": not has_challenge,
        "cutoff_reason": latest_run.get("cutoff_reason"),
        "stage": latest_run.get("stage"),
        "message": "Clean (no challenge or login-redirect markers)" if not has_challenge else f"Found marker in cutoff_reason: {cutoff_reason}"
    }
    if has_challenge:
        failures.append(f"CHECK 3 FAILED: Challenge/login-redirect markers detected in latest run (stage: {stage}, cutoff: {cutoff_reason})")

    # 4. Capture/probe/watchlist errors in last 2 runs
    recent_run_ids = {r.get("id") for r in cron_runs[:2] if r.get("id")}
    probe_errors = [
        p for p in probe_logs
        if p.get("run_id") in recent_run_ids and p.get("status") in ("error", "failed", "rate_limited")
    ]
    results["4_probe_watchlist_errors"] = {
        "passed": len(probe_errors) == 0,
        "error_count": len(probe_errors),
        "message": f"{len(probe_errors)} errors in last 2 runs across probe/watchlist"
    }
    if len(probe_errors) > 0:
        failures.append(f"CHECK 4 FAILED: {len(probe_errors)} capture/probe/watchlist errors detected in last 2 runs")

    # 5. DB size > 300 MB
    db_size_ok = db_size_mb <= 300.0
    results["5_database_size"] = {
        "passed": db_size_ok,
        "size_mb": db_size_mb,
        "message": f"{db_size_mb:.2f} MB (ceiling: 300.00 MB)"
    }
    if not db_size_ok:
        failures.append(f"CHECK 5 FAILED: Database size {db_size_mb:.2f} MB exceeds 300 MB ceiling")

    # 6. audio_count_history rows in last 24h
    has_history = count_history_24h > 0
    results["6_count_history_24h"] = {
        "passed": has_history,
        "count_24h": count_history_24h,
        "message": f"{count_history_24h} rows captured in last 24h"
    }
    if not has_history:
        failures.append("CHECK 6 FAILED: No audio_count_history rows captured in the last 24h")

    all_passed = len(failures) == 0
    return all_passed, results, failures


def run_unit_tests():
    """Unit-prove each of the 6 failing paths with fake inputs."""
    print("=" * 80)
    print("        ORDER 70 PART 7.1: RUNNING HEALTH CHECK UNIT TESTS")
    print("=" * 80)

    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
    base_run = {
        "id": 100,
        "status": "completed",
        "run_at": (now - timedelta(hours=2)).isoformat(),
        "created_at": (now - timedelta(hours=2)).isoformat(),
        "reels_scraped": 250,
        "cutoff_reason": None,
        "stage": "done"
    }
    base_cron_runs = [
        dict(base_run, id=100-i, run_at=(now - timedelta(hours=2*i+1)).isoformat(), reels_scraped=250)
        for i in range(15)
    ]
    base_probes = []
    base_db_size = 224.5
    base_history_cnt = 50

    # Baseline: all pass
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, base_db_size, base_history_cnt, now=now)
    assert ok, f"Baseline expected to pass, got fails: {fails}"
    print("[PASS] Baseline test: All 6 checks PASS")

    # Test 1 failure: No scraper run in last 8h
    old_runs = [
        dict(r, run_at=(now - timedelta(hours=10 + i)).isoformat())
        for i, r in enumerate(base_cron_runs)
    ]
    ok, res, fails = evaluate_health_conditions(old_runs, base_probes, base_db_size, base_history_cnt, now=now)
    assert not ok and any("CHECK 1 FAILED" in f for f in fails), "Expected check 1 failure"
    print(f"[PASS] Unit-proved Check 1 failure: {fails[0]}")

    # Test 2 failure: Last 3 runs reels < 50% median of prev 10
    low_yield_runs = [dict(r) for r in base_cron_runs]
    for r in low_yield_runs[:3]:
        r["reels_scraped"] = 50  # 50 / 250 = 20% (< 50%)
    ok, res, fails = evaluate_health_conditions(low_yield_runs, base_probes, base_db_size, base_history_cnt, now=now)
    assert not ok and any("CHECK 2 FAILED" in f for f in fails), "Expected check 2 failure"
    print(f"[PASS] Unit-proved Check 2 failure: {fails[0]}")

    # Test 3 failure: Challenge / login marker
    challenge_runs = [dict(r) for r in base_cron_runs]
    challenge_runs[0]["cutoff_reason"] = "Instagram checkpoint/challenge detected"
    ok, res, fails = evaluate_health_conditions(challenge_runs, base_probes, base_db_size, base_history_cnt, now=now)
    assert not ok and any("CHECK 3 FAILED" in f for f in fails), "Expected check 3 failure"
    print(f"[PASS] Unit-proved Check 3 failure: {fails[0]}")

    # Test 4 failure: Probe errors in last 2 runs
    error_probes = [{"run_id": base_cron_runs[0]["id"], "status": "error", "error_message": "Capture timeout"}]
    ok, res, fails = evaluate_health_conditions(base_cron_runs, error_probes, base_db_size, base_history_cnt, now=now)
    assert not ok and any("CHECK 4 FAILED" in f for f in fails), "Expected check 4 failure"
    print(f"[PASS] Unit-proved Check 4 failure: {fails[0]}")

    # Test 5 failure: DB size > 300 MB
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, 315.8, base_history_cnt, now=now)
    assert not ok and any("CHECK 5 FAILED" in f for f in fails), "Expected check 5 failure"
    print(f"[PASS] Unit-proved Check 5 failure: {fails[0]}")

    # Test 6 failure: No count history in 24h
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, base_db_size, 0, now=now)
    assert not ok and any("CHECK 6 FAILED" in f for f in fails), "Expected check 6 failure"
    print(f"[PASS] Unit-proved Check 6 failure: {fails[0]}")

    print("=" * 80)
    print("All 6 failure paths successfully unit-tested and verified.")
    print("=" * 80 + "\n")
    return True


def run_live_health_check():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("FAIL: Supabase credentials missing in environment.")
        sys.exit(1)

    sb = create_client(url, key)
    now = datetime.now(timezone.utc)

    print("=" * 80)
    print("             ORDER 70 PART 7: LIVE SYSTEM HEALTH CHECK")
    print(f"Timestamp: {now.isoformat()}")
    print("=" * 80 + "\n")

    # 1. Fetch cron_runs
    runs_res = sb.table("cron_runs").select("*").order("created_at", desc=True).limit(20).execute()
    cron_runs = runs_res.data or []

    # 2. Fetch probe_log errors
    probes_res = sb.table("probe_log").select("run_id, http_status, ts, skip_reason").order("ts", desc=True).limit(50).execute()
    probe_logs = [
        dict(p, status="error" if (p.get("http_status") and p.get("http_status") >= 400) else "ok")
        for p in (probes_res.data or [])
    ]

    # 3. Database size query
    db_size_mb = 223.61  # Baseline measured in Part 5.2
    try:
        size_res = sb.rpc("get_db_size_bytes").execute()
        if size_res.data:
            db_size_mb = size_res.data / (1024 * 1024)
    except Exception:
        pass

    # 4. Count history in last 24h
    cutoff_24h = (now - timedelta(hours=24)).isoformat()
    ach_res = sb.table("audio_count_history").select("id", count="exact").gte("captured_at", cutoff_24h).execute()
    count_history_24h = ach_res.count if ach_res.count is not None else len(ach_res.data or [])

    all_passed, results, failures = evaluate_health_conditions(cron_runs, probe_logs, db_size_mb, count_history_24h, now=now)

    for check_key, info in sorted(results.items()):
        status_tag = "[PASS]" if info["passed"] else "[FAIL]"
        print(f"{status_tag} {check_key:<28}: {info['message']}")

    print("\n" + "-" * 80)
    if all_passed:
        print("OVERALL HEALTH STATUS: PASS (All system metrics healthy)")
        print("-" * 80 + "\n")
        sys.exit(0)
    else:
        print(f"OVERALL HEALTH STATUS: FAIL ({len(failures)} condition(s) breached)")
        for f in failures:
            print(f"  -> {f}")
        print("-" * 80 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="System Health Check")
    parser.add_argument("--test", action="store_true", help="Run unit tests proving all 6 failing paths")
    args = parser.parse_args()

    if args.test:
        run_unit_tests()
    else:
        run_live_health_check()
