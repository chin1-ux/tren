import os
import sys
import time
import json
import statistics
from starlette.requests import Request
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")
sys.path.insert(0, "backend")

from routes.trends import get_trends

print("=" * 95)
print("PART E2: API PAYLOAD SIZE & LATENCY BENCHMARK (10 CALLS, CACHE ON)")
print("=" * 95)

scope = {
    "type": "http",
    "method": "GET",
    "path": "/api/trends",
    "headers": [],
    "query_string": b"",
}
req = Request(scope)

# Warmup call
res = get_trends(req)
raw_bytes = len(res.body)
data = json.loads(res.body.decode("utf-8"))
print(f"Payload Size       : {raw_bytes:,} bytes ({raw_bytes / 1024:.1f} KB) for {len(data)} trends")
print(f"Target Ceiling     : <= 300.0 KB")
if raw_bytes <= 300 * 1024:
    print(f"Size Assertion     : PASS ({raw_bytes / 1024:.1f} KB <= 300 KB)")
else:
    print(f"Size Assertion     : FAIL ({raw_bytes / 1024:.1f} KB > 300 KB)")

latencies = []
for i in range(10):
    t0 = time.perf_counter()
    res = get_trends(req)
    t1 = time.perf_counter()
    dur_ms = (t1 - t0) * 1000.0
    latencies.append(dur_ms)

med_lat = statistics.median(latencies)
p95_lat = sorted(latencies)[int(0.95 * len(latencies))]
min_lat = min(latencies)
max_lat = max(latencies)

print("\n10 Calls Latency Benchmark:")
print(f"  Median Latency   : {med_lat:.1f} ms")
print(f"  P95 Latency      : {p95_lat:.1f} ms")
print(f"  Min / Max Latency: {min_lat:.1f} ms / {max_lat:.1f} ms")
print("=" * 95)
