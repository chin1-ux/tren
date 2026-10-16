import time
import urllib.request
import urllib.error
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

PREVIEW_URL = "https://trendrop-pxg0tk5gn-chinmays-projects-c20ed5a5.vercel.app"

tests = [
    ("Feed Cold (page 1)", f"{PREVIEW_URL}/api/feed"),
    ("Feed Warm/Cached (page 1)", f"{PREVIEW_URL}/api/feed"),
    ("Feed all_active", f"{PREVIEW_URL}/api/feed?status=all_active"),
    ("Feed rising", f"{PREVIEW_URL}/api/feed?status=rising"),
    ("Ask Search ('gym workout')", f"{PREVIEW_URL}/api/search/ask?q=gym+workout"),
    ("Ask Search ('bollywood dance')", f"{PREVIEW_URL}/api/search/ask?q=bollywood+dance"),
    ("Legacy /api/trends", f"{PREVIEW_URL}/api/trends"),
    ("Health Check", f"{PREVIEW_URL}/api/health"),
]

headers = {
    "User-Agent": "Trendrop-Order77-SpeedTest/1.0",
    "Accept": "application/json",
}

print("=" * 100)
print("ORDER 77 ITEM 5: SPEED AUDIT AFTER FIX (LIVE VERCEL PREVIEW)")
print(f"Target Preview URL: {PREVIEW_URL}")
print("=" * 100)
print(f"{'Endpoint':<32} | {'Status':<6} | {'Bytes':<9} | {'TTFB (s)':<9} | {'Total (s)':<10} | {'Vercel Cache':<13} | {'Cache-Control'}")
print("-" * 100)

results = []

for name, url in tests:
    t0 = time.perf_counter()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            # TTFB roughly when headers read
            t_ttfb = time.perf_counter() - t0
            body = resp.read()
            t_total = time.perf_counter() - t0
            status = resp.status
            bytes_len = len(body)
            v_cache = resp.headers.get("x-vercel-cache", "none")
            cc = resp.headers.get("cache-control", "none")
            if len(cc) > 30:
                cc = cc[:27] + "..."
            print(f"{name:<32} | {status:<6} | {bytes_len:<9} | {t_ttfb:<9.3f} | {t_total:<10.3f} | {v_cache:<13} | {cc}")
            results.append({
                "name": name,
                "url": url,
                "status": status,
                "bytes": bytes_len,
                "ttfb": round(t_ttfb, 3),
                "total": round(t_total, 3),
                "v_cache": v_cache,
                "cache_control": resp.headers.get("cache-control", ""),
            })
    except urllib.error.HTTPError as e:
        t_total = time.perf_counter() - t0
        body = e.read()
        print(f"{name:<32} | {e.code:<6} | {len(body):<9} | {'-':<9} | {t_total:<10.3f} | {e.headers.get('x-vercel-cache', 'none'):<13} | HTTPError")
    except Exception as e:
        t_total = time.perf_counter() - t0
        print(f"{name:<32} | {'ERR':<6} | {'-':<9} | {'-':<9} | {t_total:<10.3f} | {'-':<13} | {e}")

# Save to evidence file
out_path = "evidence/order77/item5_speed_after.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(f"ORDER 77 ITEM 5: SPEED AUDIT AFTER FIX (LIVE VERCEL PREVIEW)\n")
    f.write(f"Preview URL: {PREVIEW_URL}\n")
    f.write(f"Deploy ID: 7120560858, Commit: 2438b9c\n\n")
    f.write(f"{'Endpoint':<32} | {'Status':<6} | {'Bytes':<9} | {'TTFB (s)':<9} | {'Total (s)':<10} | {'Vercel Cache':<13} | {'Cache-Control'}\n")
    f.write("-" * 100 + "\n")
    for r in results:
        cc = r["cache_control"]
        if len(cc) > 30:
            cc = cc[:27] + "..."
        f.write(f"{r['name']:<32} | {r['status']:<6} | {r['bytes']:<9} | {r['ttfb']:<9.3f} | {r['total']:<10.3f} | {r['v_cache']:<13} | {cc}\n")

print(f"\nSaved raw evidence to {out_path}")
