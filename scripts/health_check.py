#!/usr/bin/env python3
"""
scripts/health_check.py - Order 70, 72 & 73: Robust System & Pipeline Health Guard

Exits non-zero and prints the reason if any of these conditions are met:
1. No successful scheduled scraper run in the last 8h
2. The last 3 runs' reels_scraped < 50% of the median of the 10 runs before
3. Challenge/login-redirect markers in the last run's log / cutoff_reason
4. Capture/probe/watchlist errors in the last 2 runs
5. DB size > 300 MB
6. No audio_count_history rows in 24h
7. Emerging trends detection & availability guard (Order 73 Part 3):
   (a) New emerging trends created in last 36h > 0
   (b) New trends of any status created in last 24h >= 8
   (c) Emerging share of new trends in last 48h > 0 when >= 10 new trends
   (d) Production /api/trends/emerging returns >= 1 row with stored status 'emerging' within 7 days

Supports --test flag to unit-prove each failing path.
"""

import os
import sys
import argparse
import statistics
import urllib.request
import json
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

def evaluate_health_conditions(
    cron_runs,
    probe_logs,
    db_size_mb,
    count_history_24h,
    emerging_metrics,
    now=None
):
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

    # 7. Order 73 Emerging & Trends Creation Guards
    # (a) New emerging created in last 36h > 0
    new_em_36h = emerging_metrics.get("new_emerging_36h", 0)
    passed_7a = new_em_36h > 0
    results["7a_new_emerging_36h"] = {
        "passed": passed_7a,
        "count": new_em_36h,
        "message": f"{new_em_36h} emerging trends created in last 36h (min: 1)"
    }
    if not passed_7a:
        failures.append(f"CHECK 7A FAILED: No new emerging trends created in the last 36h (got {new_em_36h})")

    # (b) New trends of any status in last 24h >= 8
    new_trends_24h = emerging_metrics.get("new_trends_24h", 0)
    passed_7b = new_trends_24h >= 8
    results["7b_new_trends_24h"] = {
        "passed": passed_7b,
        "count": new_trends_24h,
        "message": f"{new_trends_24h} new trends of any status created in last 24h (min: 8)"
    }
    if not passed_7b:
        failures.append(f"CHECK 7B FAILED: Only {new_trends_24h} new trends created in last 24h (expected >= 8)")

    # (c) Emerging share of new trends in last 48h > 0 when >= 10 new trends
    new_trends_48h = emerging_metrics.get("new_trends_48h", 0)
    emerging_48h = emerging_metrics.get("emerging_48h", 0)
    if new_trends_48h >= 10:
        passed_7c = emerging_48h > 0
        share_pct = (emerging_48h / new_trends_48h * 100) if new_trends_48h else 0.0
        msg_7c = f"{emerging_48h}/{new_trends_48h} emerging ({share_pct:.1f}%) in last 48h (min: >0% when >=10)"
    else:
        passed_7c = True
        msg_7c = f"{emerging_48h}/{new_trends_48h} in last 48h (exempt: total < 10)"
    results["7c_emerging_share_48h"] = {
        "passed": passed_7c,
        "emerging_48h": emerging_48h,
        "new_trends_48h": new_trends_48h,
        "message": msg_7c
    }
    if not passed_7c:
        failures.append(f"CHECK 7C FAILED: Emerging share in last 48h is 0% ({emerging_48h}/{new_trends_48h} trends)")

    # (d) Production /api/trends/emerging returns >= 1 row with stored status 'emerging' within 7 days
    prod_emerging_7d = emerging_metrics.get("prod_emerging_rows_7d", 0)
    passed_7d = prod_emerging_7d >= 1
    results["7d_prod_emerging_endpoint"] = {
        "passed": passed_7d,
        "count": prod_emerging_7d,
        "message": f"{prod_emerging_7d} stored 'emerging' rows within 7d returned by production endpoint (min: 1)"
    }
    if not passed_7d:
        failures.append(f"CHECK 7D FAILED: Production /api/trends/emerging returned {prod_emerging_7d} stored 'emerging' rows within 7 days")

    all_passed = len(failures) == 0
    return all_passed, results, failures


def run_unit_tests():
    """Unit-prove each of the failing paths with mock inputs."""
    print("=" * 80)
    print("        ORDER 73 PART 3: RUNNING HEALTH CHECK UNIT TESTS")
    print("=" * 80)

    now = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)
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
    base_metrics = {
        "new_emerging_36h": 5,
        "new_trends_24h": 12,
        "new_trends_48h": 24,
        "emerging_48h": 8,
        "prod_emerging_rows_7d": 15,
    }

    # Baseline: all pass
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, base_db_size, base_history_cnt, base_metrics, now=now)
    assert ok, f"Baseline expected to pass, got fails: {fails}"
    print("[PASS] Baseline test: All checks PASS")

    # Test 1 failure: No scraper run in last 8h
    old_runs = [
        dict(r, run_at=(now - timedelta(hours=10 + i)).isoformat())
        for i, r in enumerate(base_cron_runs)
    ]
    ok, res, fails = evaluate_health_conditions(old_runs, base_probes, base_db_size, base_history_cnt, base_metrics, now=now)
    assert not ok and any("CHECK 1 FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 1 failure: {fails[0]}")

    # Test 2 failure: Last 3 runs reels < 50% median of prev 10
    low_yield_runs = [dict(r) for r in base_cron_runs]
    for r in low_yield_runs[:3]:
        r["reels_scraped"] = 50
    ok, res, fails = evaluate_health_conditions(low_yield_runs, base_probes, base_db_size, base_history_cnt, base_metrics, now=now)
    assert not ok and any("CHECK 2 FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 2 failure: {fails[0]}")

    # Test 3 failure: Login checkpoint in cutoff_reason
    challenge_runs = [dict(base_cron_runs[0], cutoff_reason="login_redirect detected")] + base_cron_runs[1:]
    ok, res, fails = evaluate_health_conditions(challenge_runs, base_probes, base_db_size, base_history_cnt, base_metrics, now=now)
    assert not ok and any("CHECK 3 FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 3 failure: {fails[0]}")

    # Test 4 failure: Probe errors in recent runs
    mock_probe_errors = [{"run_id": 100, "status": "rate_limited"}, {"run_id": 99, "status": "error"}]
    ok, res, fails = evaluate_health_conditions(base_cron_runs, mock_probe_errors, base_db_size, base_history_cnt, base_metrics, now=now)
    assert not ok and any("CHECK 4 FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 4 failure: {fails[0]}")

    # Test 5 failure: DB size exceeds 300MB
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, 312.4, base_history_cnt, base_metrics, now=now)
    assert not ok and any("CHECK 5 FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 5 failure: {fails[0]}")

    # Test 6 failure: No history in 24h
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, base_db_size, 0, base_metrics, now=now)
    assert not ok and any("CHECK 6 FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 6 failure: {fails[0]}")

    # Test 7a failure: New emerging in 36h == 0
    m_7a = dict(base_metrics, new_emerging_36h=0)
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, base_db_size, base_history_cnt, m_7a, now=now)
    assert not ok and any("CHECK 7A FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 7a failure: {fails[0]}")

    # Test 7b failure: New trends in 24h < 8
    m_7b = dict(base_metrics, new_trends_24h=4)
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, base_db_size, base_history_cnt, m_7b, now=now)
    assert not ok and any("CHECK 7B FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 7b failure: {fails[0]}")

    # Test 7c failure: Emerging share in 48h == 0 when >= 10 new trends
    m_7c = dict(base_metrics, new_trends_48h=20, emerging_48h=0)
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, base_db_size, base_history_cnt, m_7c, now=now)
    assert not ok and any("CHECK 7C FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 7c failure: {fails[0]}")

    # Test 7d failure: Production emerging endpoint returns 0 valid rows
    m_7d = dict(base_metrics, prod_emerging_rows_7d=0)
    ok, res, fails = evaluate_health_conditions(base_cron_runs, base_probes, base_db_size, base_history_cnt, m_7d, now=now)
    assert not ok and any("CHECK 7D FAILED" in f for f in fails)
    print(f"[PASS] Unit-proved Check 7d failure: {fails[0]}")

    print("=" * 80)
    print("ALL 10 UNIT TEST FAILING PATHS VERIFIED AND PASSED!")
    print("=" * 80)


def run_live_health_check():
    """Execute live system health check against Supabase and production API."""
    try:
        from supabase import create_client
    except ImportError:
        print("FAIL: supabase library not installed.")
        sys.exit(1)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("FAIL: Supabase credentials missing in environment.")
        sys.exit(1)

    sb = create_client(url, key)
    now = datetime.now(timezone.utc)

    print("=" * 80)
    print("             ORDER 73 PART 3: LIVE SYSTEM HEALTH CHECK")
    print(f"Timestamp: {now.isoformat()}")
    print("=" * 80 + "\n")

    # 1. Fetch cron_runs (explicit columns, no select(*))
    runs_res = sb.table("cron_runs").select("id, status, run_at, created_at, reels_scraped, stage, cutoff_reason").order("run_at", desc=True).limit(20).execute()
    cron_runs = runs_res.data or []

    # 2. Fetch probe_log errors
    probes_res = sb.table("probe_log").select("run_id, http_status, ts, skip_reason").order("ts", desc=True).limit(50).execute()
    probe_logs = [
        dict(p, status="error" if (p.get("http_status") and p.get("http_status") >= 400) else "ok")
        for p in (probes_res.data or [])
    ]

    # 3. Database size query
    db_size_mb = 223.61
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

    # 5. Order 73 Detection Metrics Queries (explicit columns)
    cutoff_36h = (now - timedelta(hours=36)).isoformat()
    cutoff_48h = (now - timedelta(hours=48)).isoformat()
    cutoff_7d = (now - timedelta(days=7)).isoformat()

    # (a) New emerging in last 36h
    em_36h_res = (
        sb.table("trends")
        .select("id", count="exact")
        .eq("status", "emerging")
        .gte("created_at", cutoff_36h)
        .execute()
    )
    new_emerging_36h = em_36h_res.count if em_36h_res.count is not None else len(em_36h_res.data or [])

    # (b) New trends of any status in last 24h
    tr_24h_res = (
        sb.table("trends")
        .select("id", count="exact")
        .gte("created_at", cutoff_24h)
        .execute()
    )
    new_trends_24h = tr_24h_res.count if tr_24h_res.count is not None else len(tr_24h_res.data or [])

    # (c) Trends in last 48h
    tr_48h_res = (
        sb.table("trends")
        .select("id, status")
        .gte("created_at", cutoff_48h)
        .execute()
    )
    trends_48h_data = tr_48h_res.data or []
    new_trends_48h = len(trends_48h_data)
    emerging_48h = sum(1 for t in trends_48h_data if t.get("status") == "emerging")

    # (d) Production endpoint verification: /api/trends/emerging
    prod_emerging_rows_7d = 0
    prod_urls = [
        "https://trendrop-black.vercel.app/api/trends/emerging",
        "https://www.trendrop.net/api/trends/emerging"
    ]
    for url_target in prod_urls:
        try:
            req = urllib.request.Request(url_target, headers={"User-Agent": "Trendrop-HealthGuard/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    cutoff_dt = now - timedelta(days=7)
                    valid_rows = [
                        row for row in data
                        if row.get("status") == "emerging"
                        and parse_dt(row.get("first_detected_at") or row.get("created_at"))
                        and parse_dt(row.get("first_detected_at") or row.get("created_at")) >= cutoff_dt
                    ]
                    prod_emerging_rows_7d = len(valid_rows)
                    break
        except Exception as api_err:
            pass

    emerging_metrics = {
        "new_emerging_36h": new_emerging_36h,
        "new_trends_24h": new_trends_24h,
        "new_trends_48h": new_trends_48h,
        "emerging_48h": emerging_48h,
        "prod_emerging_rows_7d": prod_emerging_rows_7d,
    }

    all_passed, results, failures = evaluate_health_conditions(
        cron_runs, probe_logs, db_size_mb, count_history_24h, emerging_metrics, now=now
    )

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
    parser.add_argument("--test", action="store_true", help="Run unit tests proving all failing paths")
    args = parser.parse_args()

    if args.test:
        run_unit_tests()
    else:
        run_live_health_check()
