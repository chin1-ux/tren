"""
Consolidated test script for all gated endpoints
"""
import requests
import sys

BASE_URL = "http://localhost:8000"

endpoints = [
    "/api/trends/emerging",
    "/api/trends/all-active", 
    "/api/trends/audio-scores",
    "/api/trends/295/timeline",
    "/api/trends/295/reels",
    "/api/trends/295/similar",
    "/api/trends/295/decision",
    "/api/trends/peaking",
    "/api/trends/295/audio-history",
    "/api/trends/295/caption",
    "/api/algorithm/analyze",
    "/api/algorithm/posting-times",
    "/api/algorithm/hashtag-strategy",
    "/api/reels/feed",
    "/api/reels/cross-cultural",
    "/api/ai/generate-caption",
    "/api/ai/content-ideas",
]

results = []

for endpoint in endpoints:
    # Test guest
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        guest_status = response.status_code
    except Exception as e:
        guest_status = f"ERROR: {e}"
    
    # Test pro-demo (account 1)
    try:
        headers = {'Authorization': 'Bearer pro-demo-token'}
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        pro1_status = response.status_code
    except Exception as e:
        pro1_status = f"ERROR: {e}"
    
    # Test pro-demo (account 2)
    try:
        headers = {'Authorization': 'Bearer pro-demo-token-2'}
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        pro2_status = response.status_code
    except Exception as e:
        pro2_status = f"ERROR: {e}"
    
    results.append({
        'endpoint': endpoint,
        'guest': guest_status,
        'pro1': pro1_status,
        'pro2': pro2_status
    })

# Print table
print(f"{'Endpoint':<50} {'Guest':<10} {'Pro1':<10} {'Pro2':<10}")
print("-" * 80)
for r in results:
    print(f"{r['endpoint']:<50} {str(r['guest']):<10} {str(r['pro1']):<10} {str(r['pro2']):<10}")
