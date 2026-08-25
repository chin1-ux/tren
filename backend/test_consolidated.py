import requests

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
    "/api/ai/generate-caption?trend_name=test",
    "/api/ai/content-ideas",
]

print('Endpoint'.ljust(50) + 'Guest'.ljust(10) + 'Agency'.ljust(10) + 'Creator'.ljust(10))
print('-'*80)

for endpoint in endpoints:
    try:
        guest = requests.get(f"{BASE_URL}{endpoint}").status_code
    except:
        guest = "ERROR"
    
    try:
        agency = requests.get(f"{BASE_URL}{endpoint}", headers={"Authorization": "Bearer agency-demo-token"}).status_code
    except:
        agency = "ERROR"
    
    try:
        creator = requests.get(f"{BASE_URL}{endpoint}", headers={"Authorization": "Bearer creator-demo-token"}).status_code
    except:
        creator = "ERROR"
    
    print(f"{endpoint.ljust(50)}{str(guest).ljust(10)}{str(agency).ljust(10)}{str(creator).ljust(10)}")
