import os
import sys
import json

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

endpoints = [
    ("/api/trends?limit=20", "Rising (/api/trends)"),
    ("/api/trends/emerging?limit=20", "Emerging (/api/trends/emerging)"),
    ("/api/trends/peaked?limit=20", "Peaked (/api/trends/peaked)"),
    ("/api/trends/resurging?limit=20", "Resurging (/api/trends/resurging)"),
    ("/api/trends/expired?limit=20", "Expired (/api/trends/expired)"),
    ("/api/trends/freshness", "Freshness (/api/trends/freshness)"),
    ("/api/trends/runs", "Runs (/api/trends/runs)"),
    ("/api/trends/last-detected", "Last Detected (/api/trends/last-detected)"),
]

results = []
print(f"{'Endpoint':<35} | {'Status':<6} | {'Bytes':<10} | {'KB':<8} | {'Items':<6} | {'Cache-Control'}")
print("-" * 110)

for url, label in endpoints:
    try:
        resp = client.get(url)
        content_len = len(resp.content)
        kb = round(content_len / 1024, 2)
        try:
            data = resp.json()
            if isinstance(data, list):
                item_count = len(data)
            elif isinstance(data, dict):
                item_count = len(data.get("runs", [])) or len(data)
            else:
                item_count = 0
        except Exception:
            item_count = 0
        cc = resp.headers.get("cache-control", "None")
        print(f"{label:<35} | {resp.status_code:<6} | {content_len:<10} | {kb:<8} | {item_count:<6} | {cc}")
        results.append({
            "endpoint": url,
            "label": label,
            "status": resp.status_code,
            "bytes": content_len,
            "kb": kb,
            "items": item_count,
            "cache_control": cc
        })
    except Exception as e:
        print(f"{label:<35} | ERR    | {e}")

# Save to evidence
evidence_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "evidence", "order85", "slim_endpoints_measurement.json"))
os.makedirs(os.path.dirname(evidence_path), exist_ok=True)
with open(evidence_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nSaved results to {evidence_path}")
