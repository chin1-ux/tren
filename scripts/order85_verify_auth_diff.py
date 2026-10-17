import os
import sys
import json

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

# 1. Anonymous request
resp_anon = client.get("/api/trends?limit=20")
cc_anon = resp_anon.headers.get("cache-control")

# 2. Authenticated request with custom headers
resp_auth = client.get("/api/trends?limit=20", headers={"Authorization": "Bearer demo-token"})
cc_auth = resp_auth.headers.get("cache-control")

print(f"Anonymous Cache-Control: {cc_anon}")
print(f"Auth Cache-Control: {cc_auth}")
print(f"Data matches: {len(resp_anon.json()) == len(resp_auth.json())}")

evidence = {
    "anonymous_cache_control": cc_anon,
    "auth_cache_control": cc_auth,
    "item_count_anon": len(resp_anon.json()),
    "item_count_auth": len(resp_auth.json())
}

out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "evidence", "order85", "auth_diff_evidence.json"))
with open(out_path, "w") as f:
    json.dump(evidence, f, indent=2)
print(f"Saved auth diff evidence to {out_path}")
