#!/usr/bin/env python3
"""
Simple test for admin login using urllib
"""

import urllib.request
import json

url = "http://localhost:8000/api/admin/login"
data = {
    "email": "chinmay.feb03@gmail.com",
    "password": "nagaiah.rathna76"
}

print("Testing admin login...")
print(f"URL: {url}")
print(f"Data: {json.dumps(data, indent=2)}")

try:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    with urllib.request.urlopen(req) as response:
        response_data = response.read()
        print(f"\nStatus Code: {response.status}")
        print(f"Response: {response_data.decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"\nHTTP Error: {e.code}")
    print(f"Response: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"\nError: {e}")
