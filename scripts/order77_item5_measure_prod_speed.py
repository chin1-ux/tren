import json
import time
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://trendrop-black.vercel.app"

ENDPOINTS = [
    ("/api/trends", "Main Rising Feed"),
    ("/api/trends/emerging", "Emerging Trends"),
    ("/api/trends/peaked", "Peaked Trends"),
    ("/api/trends/expired", "Expired Trends"),
    ("/api/trends/resurging", "Resurging Trends"),
    ("/api/trends/targeted", "Targeted Trends"),
    ("/api/trends/last-detected", "Last Detected Times"),
    ("/api/trends/runs?limit=6", "Recent Scraper Runs"),
]

def measure_url(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            elapsed = time.time() - t0
            status = resp.status
            size_kb = len(content) / 1024.0
            try:
                data = json.loads(content.decode("utf-8"))
                if isinstance(data, list):
                    rows = len(data)
                elif isinstance(data, dict):
                    rows = len(data.get("trends", data.get("runs", data.keys())))
                else:
                    rows = 1
            except Exception:
                rows = 0
            return status, elapsed, size_kb, rows
    except Exception as e:
        elapsed = time.time() - t0
        return str(e), elapsed, 0, 0

print("=" * 95)
print("ORDER 77 ITEM 5: PRODUCTION SPEED AUDIT (BEFORE FIX)")
print(f"Target Base URL: {BASE_URL}")
print(f"Timestamp      : {datetime.now(timezone.utc).isoformat()}")
print("=" * 95)
print(f"{'Endpoint':<28} | {'Status':<8} | {'Cold (s)':<10} | {'Warm (s)':<10} | {'Size (KB)':<10} | {'Rows':<6}")
print("-" * 95)

total_cold = 0
total_warm = 0
total_kb = 0
total_rows = 0

for ep, label in ENDPOINTS:
    url = f"{BASE_URL}{ep}"
    # Cold request
    status_c, time_c, size_c, rows_c = measure_url(url)
    time.sleep(0.5)
    # Warm request
    status_w, time_w, size_w, rows_w = measure_url(url)
    
    total_cold += time_c
    total_warm += time_w
    total_kb += size_c
    total_rows += rows_c
    
    print(f"{ep:<28} | {str(status_c):<8} | {time_c:<10.3f} | {time_w:<10.3f} | {size_c:<10.1f} | {rows_c:<6}")

print("-" * 95)
print(f"{'TOTALS (8 REQUESTS)':<28} | {'-':<8} | {total_cold:<10.3f} | {total_warm:<10.3f} | {total_kb:<10.1f} | {total_rows:<6}")
print("=" * 95)
